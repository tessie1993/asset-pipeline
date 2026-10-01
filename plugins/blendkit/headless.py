"""plugins/blendkit/headless.py — the BlendKit add-on in a headless Blender, logged in.

In background mode the add-on registers but starts neither its timers nor its BlendKit-Client,
and it does not read the login it keeps on disk. This module does those steps for a
``blender -b`` script, then downloads and appends assets with the add-on's own functions:

    import sys; sys.path.insert(0, "<repo>/plugins/blendkit"); import headless
    headless.enable()                                   # the add-on, with your login (login.py)
    asset = headless.search("asset_type:material oak")[0]
    asset = headless.asset("https://www.blendkit.com/asset-gallery-detail/<id>/")  # or one from its link
    material = headless.append(asset)                   # download as your account, then append

Assets, the client binary and its log go in this folder's ``.data`` (git-ignored); the client
stops by itself a few minutes after the last Blender using it. Search with
the server's query syntax (``asset_type:model``, ``is_free:true``, ``license:cc_zero``, ...).
The asset's licence is in ``asset["license"]``: check it allows what you will do with the asset.
"""

from __future__ import annotations

import importlib
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import login

ADDON = "bl_ext.user_default.blenderkit"
LIBRARY = login.DATA_DIR / "assets"
CLIENT_START_TIMEOUT = 30.0


def _addon(module: str = ""):
    return importlib.import_module(f"{ADDON}.{module}" if module else ADDON)


def _api_key() -> str:
    import bpy

    return bpy.context.preferences.addons[ADDON].preferences.api_key


def _client_up() -> bool:
    client_lib = _addon("client_lib")
    try:
        client_lib.get_reports(0)
        return True
    except Exception:  # not listening yet
        return False


def enable() -> None:
    """Enable the add-on in this session with the login and data folder applied, and start its
    BlendKit-Client (which it starts itself only with a window)."""
    import addon_utils
    import bpy

    if addon_utils.enable(ADDON, default_set=True) is None:
        raise RuntimeError("BlendKit is not installed: bash plugins/blendkit/install.sh")
    stored = login._read(login.PREFERENCES)
    preferences = bpy.context.preferences.addons[ADDON].preferences
    preferences.global_dir = str(login.DATA_DIR)
    preferences.api_key_refresh = stored.get("api_key_refresh", "")
    preferences.api_key_timeout = int(stored.get("api_key_timeout", 0))
    _addon("global_vars").PREFS = _addon("utils").get_preferences_as_dict()
    if not _client_up():
        _addon("client_lib").start_blenderkit_client()
        deadline = time.time() + CLIENT_START_TIMEOUT
        while not _client_up():
            if time.time() > deadline:
                raise RuntimeError(f"BlendKit-Client did not start: see {_addon('client_lib').get_client_log_path()}")
            time.sleep(0.5)
    # Set last: the add-on then fetches the profile through the running client.
    preferences.api_key = login.api_key()  # refreshed when near expiry
    _addon("global_vars").PREFS = _addon("utils").get_preferences_as_dict()


def search(query: str, page_size: int = 20) -> list[dict]:
    """Search records matching ``query`` (the server's syntax), as your account sees them."""
    params = urllib.parse.urlencode({"query": query, "page_size": page_size, "dict_parameters": 1})
    request = urllib.request.Request(
        f"{login.SERVER}/api/v1/search/?{params}",
        headers={"User-Agent": login.USER_AGENT, "Authorization": f"Bearer {_api_key()}"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response).get("results", [])


def asset(link_or_id: str) -> dict:
    """The search record of one asset, from its blendkit.com gallery link or its asset base id."""
    match = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", link_or_id)
    if not match:
        raise ValueError(f"No asset id in {link_or_id!r}")
    found = search(f"asset_base_id:{match.group(0)}", page_size=1)
    if not found:
        raise LookupError(f"BlendKit has no asset {match.group(0)} this account can see")
    return found[0]


def download(asset: dict) -> Path:
    """Download ``asset``'s .blend through the add-on's BlendKit-Client, once; returns its path."""
    client_lib = _addon("client_lib")
    can_download, url, filename = client_lib.get_download_url(asset, _addon("utils").get_scene_id(), _api_key())
    if not can_download:
        raise RuntimeError(f"BlendKit will not let this account download {asset['name']} ({asset.get('canDownloadError')})")
    target = LIBRARY / asset["assetType"] / asset["assetBaseId"] / filename
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        response = client_lib.blocking_file_download(url, str(target), _api_key())
        if not response.ok or not target.exists():
            raise RuntimeError(f"BlendKit download of {asset['name']} failed: {response.status_code} {response.text[:200]}")
    return target


def append(asset: dict):
    """Download ``asset`` and append it with the add-on's own functions: a material returns the
    ``bpy.types.Material``, a model the list of its objects (linked to the scene)."""
    path = download(asset)
    append_link = _addon("append_link")
    if asset["assetType"] == "material":
        return append_link.append_material(str(path), matname=asset["name"])
    if asset["assetType"] == "model":
        _, objects = append_link.append_objects(str(path), name=asset["name"], location=(0, 0, 0))
        return objects
    raise ValueError(f"append handles materials and models; load {asset['assetType']} assets from {path} yourself")
