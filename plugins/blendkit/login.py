#!/usr/bin/env python3
"""plugins/blendkit/login.py — log the headless Blender's BlendKit add-on in to your BlendKit account.

The add-on's own login, done by hand because this Blender has no window and no browser: the
same OAuth 2 authorization-code flow with PKCE, client id, redirect and token request as the
add-on and its BlendKit-Client (bkit_oauth.py, bk_client/client/login.go). You log in on
blendkit.com in your own browser; no password ever reaches this machine.

    python3 plugins/blendkit/login.py start          prints the login link
    python3 plugins/blendkit/login.py finish <url>   takes the address your browser ended on
    python3 plugins/blendkit/login.py status         who is logged in, until when
    python3 plugins/blendkit/login.py logout         revokes the tokens on the server, deletes them

After logging in on the link's page, blendkit.com sends the browser to
http://localhost:62485/consumer/exchange/?code=...&state=..., which does not load on your computer
(the BlendKit-Client it is meant for runs here). Copy that address from the address bar and give
it to ``finish`` within a minute: the code in it expires quickly and is useless without the
verifier ``start`` kept here.

The tokens go where the add-on keeps them, ``.data/config/preferences.json`` (``api_key``,
``api_key_refresh``, ``api_key_timeout``), git-ignored and readable only by this user. Headless
scripts get a current access token from :func:`api_key`, which refreshes it when it is about to
expire, as the add-on does.
"""

from __future__ import annotations

import base64
import glob
import hashlib
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / ".data"
PREFERENCES = DATA_DIR / "config" / "preferences.json"
PENDING = DATA_DIR / "login-pending.json"
SERVER = os.environ.get("BLENDERKIT_SERVER", "https://www.blendkit.com")
# blendkit.com's Cloudflare refuses Python's default User-Agent (error 1010).
USER_AGENT = "asset-pipeline BlendKit login"
REFRESH_RESERVE = 3600  # seconds before expiry the token is refreshed (as the add-on's REFRESH_RESERVE)
PENDING_MAX_AGE = 3600


def _addon_dir() -> Path:
    """The installed add-on (plugins/blendkit/install.sh puts it in Blender's user_default repository)."""
    config = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    found = sorted(glob.glob(f"{config}/blender/*/extensions/user_default/blenderkit/bkit_oauth.py"))
    if not found:
        sys.exit("BlendKit is not installed: run bash plugins/blendkit/install.sh")
    return Path(found[-1]).parent


def _addon_value(file_name: str, pattern: str) -> str:
    match = re.search(pattern, (_addon_dir() / file_name).read_text(encoding="utf-8"))
    if not match:
        sys.exit(f"Cannot read {pattern!r} from the add-on's {file_name}: the add-on changed")
    return match.group(1)


def _client_id() -> str:
    return _addon_value("bkit_oauth.py", r'CLIENT_ID\s*=\s*"([^"]+)"')


def _redirect_uri() -> str:
    port = _addon_value("global_vars.py", r'CLIENT_PORTS\s*=\s*\[\s*"(\d+)"')
    return f"http://localhost:{port}/consumer/exchange/"


def _write_private(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(DATA_DIR, 0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=4)


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _request(path: str, form: dict | None = None, token: str = "") -> tuple[int, dict]:
    """POST ``form`` (or GET when None) to the BlendKit server; returns the status and JSON body."""
    data = urllib.parse.urlencode(form).encode() if form is not None else None
    request = urllib.request.Request(f"{SERVER}{path}", data=data, headers={"User-Agent": USER_AGENT})
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        body, status = error.read(), error.code
    try:
        return status, json.loads(body or b"{}")
    except ValueError:
        return status, {"error": body[:300].decode("utf-8", "replace")}


def _save_tokens(tokens: dict) -> None:
    preferences = _read(PREFERENCES)
    preferences["api_key"] = tokens["access_token"]
    preferences["api_key_refresh"] = tokens.get("refresh_token", "")
    preferences["api_key_timeout"] = int(time.time() + int(tokens.get("expires_in", 0)))
    _write_private(PREFERENCES, preferences)


def start() -> str:
    """Create the PKCE pair and state, keep them here and return the login link."""
    verifier = secrets.token_urlsafe(96)[:128]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe()
    _write_private(PENDING, {"code_verifier": verifier, "state": state, "created": int(time.time())})
    query = urllib.parse.urlencode(
        {
            "client_id": _client_id(),
            "response_type": "code",
            "state": state,
            "redirect_uri": _redirect_uri(),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{SERVER}/o/authorize?{query}"


def finish(redirected_to: str) -> str:
    """Exchange the code in the address the browser ended on for tokens and store them."""
    pending = _read(PENDING)
    if not pending or time.time() - pending.get("created", 0) > PENDING_MAX_AGE:
        sys.exit("No login in progress (or it is over an hour old): run login.py start again")
    query = urllib.parse.parse_qs(urllib.parse.urlparse(redirected_to.strip()).query)
    code, state = query.get("code", [""])[0], query.get("state", [""])[0]
    if query.get("error"):
        sys.exit(f"blendkit.com refused the login: {query['error'][0]}")
    if not code or not state:
        sys.exit("That address has no code and state: copy the whole address the browser ended on")
    if not secrets.compare_digest(state, pending["state"]):
        sys.exit("That address belongs to another login attempt: open the newest link")
    status, tokens = _request(
        "/o/token/",
        {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": pending["code_verifier"],
            "client_id": _client_id(),
            "scopes": "read write",
            "redirect_uri": _redirect_uri(),
        },
    )
    if status != 200 or "access_token" not in tokens:
        sys.exit(
            f"Token request failed ({status}: {tokens.get('error', tokens)}). The code lasts about a "
            "minute: open the same link again, log in and send the new address straight away"
        )
    _save_tokens(tokens)
    PENDING.unlink(missing_ok=True)
    return status_line()


def refresh(force: bool = False) -> None:
    """Refresh the access token with the refresh token when it is about to expire (or ``force``)."""
    preferences = _read(PREFERENCES)
    if not preferences.get("api_key_refresh"):
        return
    if not force and time.time() + REFRESH_RESERVE < preferences.get("api_key_timeout", 0):
        return
    status, tokens = _request(
        "/o/token/",
        {
            "grant_type": "refresh_token",
            "refresh_token": preferences["api_key_refresh"],
            "client_id": _client_id(),
            "scopes": "read write",
            "redirect_uri": _redirect_uri(),
        },
    )
    if status != 200 or "access_token" not in tokens:
        raise RuntimeError(
            f"BlendKit token refresh failed ({status}): log in again with python3 plugins/blendkit/login.py start"
        )
    _save_tokens(tokens)


def api_key() -> str:
    """A current access token for the add-on's ``api_key`` preference; refreshed when needed."""
    if not _read(PREFERENCES).get("api_key"):
        raise RuntimeError("BlendKit is not logged in: python3 plugins/blendkit/login.py start")
    refresh()
    return _read(PREFERENCES)["api_key"]


def status_line() -> str:
    preferences = _read(PREFERENCES)
    if not preferences.get("api_key"):
        return "Not logged in"
    refresh()
    preferences = _read(PREFERENCES)
    code, me = _request("/api/v1/me/", token=preferences["api_key"])
    if code != 200:
        return f"Logged in, but the server answered {code}: log in again"
    user = me.get("user", me)
    name = user.get("username") or f"account {user.get('id', '?')}"  # fullName is "(anonymous)" when unset
    plan = user.get("currentPlanName") or ("Free" if user.get("hasFreePlan") else "unknown")
    until = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(preferences["api_key_timeout"]))
    return f"Logged in to BlendKit as {name}, plan {plan} (token valid until {until}, refreshed automatically)"


def logout() -> str:
    preferences = _read(PREFERENCES)
    for token, hint in ((preferences.get("api_key"), ""), (preferences.get("api_key_refresh"), "refresh_token")):
        if token:
            form = {"client_id": _client_id(), "token": token}
            if hint:
                form["token_type_hint"] = hint
            _request("/o/revoke_token/", form)
    for key in ("api_key", "api_key_refresh", "api_key_timeout"):
        preferences.pop(key, None)
    if PREFERENCES.exists():
        _write_private(PREFERENCES, preferences)
    PENDING.unlink(missing_ok=True)
    return "Logged out: the tokens are revoked and deleted"


def main(argv: list[str]) -> None:
    command = argv[1] if len(argv) > 1 else ""
    if command == "start":
        print(start())
    elif command == "finish" and len(argv) == 3:
        print(finish(argv[2]))
    elif command == "status":
        print(status_line())
    elif command == "logout":
        print(logout())
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
