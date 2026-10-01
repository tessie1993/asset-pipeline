"""Tests for plugins/blendkit/login.py, the BlendKit add-on's OAuth login for a headless Blender
(offline: the server and the installed add-on are stand-ins).

Run: python3 -m unittest discover -s tests/tools/assetgen -p "*_test.py"
"""
import base64
import hashlib
import json
import stat
import sys
import tempfile
import time
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "plugins" / "blendkit"))
import login  # noqa: E402

CLIENT_ID = "test-client-id"
REDIRECT = "http://localhost:62485/consumer/exchange/"
PROFILE = {"user": {"id": 7, "username": "", "fullName": "(anonymous)", "currentPlanName": "Free"}}


class LoginTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        addon = tmp / "blenderkit"
        addon.mkdir()
        (addon / "bkit_oauth.py").write_text(f'CLIENT_ID = "{CLIENT_ID}"\n')
        (addon / "global_vars.py").write_text('CLIENT_PORTS = ["62485", "65425"]\n')
        data = tmp / ".data"
        for name, value in (
            ("DATA_DIR", data),
            ("PREFERENCES", data / "config" / "preferences.json"),
            ("PENDING", data / "login-pending.json"),
        ):
            patcher = mock.patch.object(login, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(login, "_addon_dir", return_value=addon)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.requests = []
        self.answers = {}
        patcher = mock.patch.object(login, "_request", side_effect=self._request)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _request(self, path, form=None, token=""):
        self.requests.append((path, form, token))
        answer = self.answers.get(path, (200, {}))
        return answer(form) if callable(answer) else answer

    def tokens(self, access="access-1", refresh="refresh-1", expires_in=36000):
        return 200, {"access_token": access, "refresh_token": refresh, "expires_in": expires_in}

    def private(self, path: Path) -> bool:
        return stat.S_IMODE(path.stat().st_mode) == 0o600 and stat.S_IMODE(login.DATA_DIR.stat().st_mode) == 0o700

    def logged_in(self) -> None:
        link = login.start()
        state = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)["state"][0]
        self.answers["/o/token/"] = self.tokens()
        self.answers["/api/v1/me/"] = (200, PROFILE)
        login.finish(f"{REDIRECT}?code=the-code&state={state}")
        self.requests.clear()

    def test_start_gives_the_add_ons_login_link_and_keeps_the_verifier_private(self):
        link = login.start()
        query = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
        pending = json.loads(login.PENDING.read_text())
        challenge = base64.urlsafe_b64encode(hashlib.sha256(pending["code_verifier"].encode()).digest()).decode().rstrip("=")
        self.assertEqual(query["client_id"], [CLIENT_ID])
        self.assertEqual(query["redirect_uri"], [REDIRECT])
        self.assertEqual(query["code_challenge"], [challenge])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["state"], [pending["state"]])
        self.assertNotIn(pending["code_verifier"], link)
        self.assertTrue(self.private(login.PENDING))

    def test_finish_exchanges_the_code_and_stores_the_tokens_as_the_add_on_does(self):
        self.logged_in()
        stored = json.loads(login.PREFERENCES.read_text())
        self.assertEqual(stored["api_key"], "access-1")
        self.assertEqual(stored["api_key_refresh"], "refresh-1")
        self.assertAlmostEqual(stored["api_key_timeout"], time.time() + 36000, delta=60)
        self.assertTrue(self.private(login.PREFERENCES))
        self.assertFalse(login.PENDING.exists())

    def test_finish_sends_the_verifier_with_the_code(self):
        login.start()
        pending = json.loads(login.PENDING.read_text())
        self.answers["/o/token/"] = self.tokens()
        login.finish(f"{REDIRECT}?code=the-code&state={pending['state']}")
        path, form, _ = self.requests[0]
        self.assertEqual(path, "/o/token/")
        self.assertEqual(form["grant_type"], "authorization_code")
        self.assertEqual(form["code"], "the-code")
        self.assertEqual(form["code_verifier"], pending["code_verifier"])
        self.assertEqual(form["client_id"], CLIENT_ID)
        self.assertEqual(form["redirect_uri"], REDIRECT)

    def test_finish_refuses_another_login_s_address_or_one_without_a_code(self):
        login.start()
        with self.assertRaises(SystemExit):
            login.finish(f"{REDIRECT}?code=the-code&state=someone-elses")
        with self.assertRaises(SystemExit):
            login.finish("http://localhost:62485/consumer/exchange/")
        self.assertEqual(self.requests, [])
        self.assertFalse(login.PREFERENCES.exists())

    def test_finish_without_a_login_in_progress_refuses(self):
        with self.assertRaises(SystemExit):
            login.finish(f"{REDIRECT}?code=the-code&state=any")

    def test_a_failed_token_request_stores_nothing(self):
        login.start()
        state = json.loads(login.PENDING.read_text())["state"]
        self.answers["/o/token/"] = (400, {"error": "invalid_grant"})
        with self.assertRaises(SystemExit):
            login.finish(f"{REDIRECT}?code=expired&state={state}")
        self.assertFalse(login.PREFERENCES.exists())
        self.assertTrue(login.PENDING.exists())  # the same link can be opened again

    def test_api_key_refreshes_only_near_expiry(self):
        self.logged_in()
        self.assertEqual(login.api_key(), "access-1")
        self.assertEqual(self.requests, [])
        stored = json.loads(login.PREFERENCES.read_text())
        stored["api_key_timeout"] = int(time.time()) + 60
        login.PREFERENCES.write_text(json.dumps(stored))
        self.answers["/o/token/"] = self.tokens("access-2", "refresh-2")
        self.assertEqual(login.api_key(), "access-2")
        _, form, _ = self.requests[0]
        self.assertEqual(form["grant_type"], "refresh_token")
        self.assertEqual(form["refresh_token"], "refresh-1")
        self.assertEqual(json.loads(login.PREFERENCES.read_text())["api_key_refresh"], "refresh-2")

    def test_api_key_without_a_login_says_how_to_log_in(self):
        with self.assertRaisesRegex(RuntimeError, "login.py start"):
            login.api_key()

    def test_status_names_the_account_by_id_when_it_has_no_username(self):
        self.logged_in()
        self.answers["/api/v1/me/"] = (200, PROFILE)
        self.assertIn("account 7, plan Free", login.status_line())

    def test_logout_revokes_both_tokens_and_deletes_them(self):
        self.logged_in()
        login.logout()
        revoked = [form["token"] for path, form, _ in self.requests if path == "/o/revoke_token/"]
        self.assertEqual(revoked, ["access-1", "refresh-1"])
        self.assertNotIn("api_key", json.loads(login.PREFERENCES.read_text()))


if __name__ == "__main__":
    unittest.main()
