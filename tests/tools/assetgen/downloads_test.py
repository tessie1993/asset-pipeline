"""Tests for tools/assetgen/downloads.py's Blendkit material library: anonymous (free CC0 only)
or through the BlendKit login (free CC0 and royalty-free) (offline: the server is a stand-in).

Run: python3 -m unittest discover -s tests/tools/assetgen -p "*_test.py"
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools" / "assetgen"))
import downloads  # noqa: E402


def material(base_id: str, licence: str, can_download: bool = True, free: bool = True) -> dict:
    return {"assetBaseId": base_id, "name": base_id, "license": licence, "isFree": free,
            "canDownload": can_download,
            "files": [{"fileType": "blend", "downloadUrl": f"https://api/downloads/{base_id}/", "fileUploadSize": 3}]}


SEARCH = [
    material("cc0", "cc_zero"),
    material("rf", "royalty_free"),
    material("plan_only", "royalty_free", can_download=False),
    material("other", "editorial"),
]


class BlendkitTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.calls = []
        self.answer = {"results": SEARCH}
        patcher = mock.patch.object(downloads, "get_json", side_effect=self._get_json)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _get_json(self, url, token=""):
        self.calls.append((url, token))
        return self.answer

    def logged_in(self, token: str):
        return mock.patch.object(downloads, "blendkit_token", return_value=token)

    def test_anonymous_search_asks_for_cc0_only_and_keeps_only_cc0(self):
        with self.logged_in(""):
            found = downloads.blendkit_search(["pink", "crystal"], 6)
        url, token = self.calls[0]
        self.assertIn("license:cc_zero", url)
        self.assertIn("is_free:true", url)
        self.assertEqual(token, "")
        self.assertEqual([asset["assetBaseId"] for asset in found], ["cc0"])

    def test_logged_in_search_sends_the_token_and_keeps_free_cc0_and_royalty_free(self):
        with self.logged_in("tok"):
            found = downloads.blendkit_search(["pink", "crystal"], 6)
        url, token = self.calls[0]
        self.assertNotIn("license:", url)
        self.assertIn("is_free:true", url)
        self.assertEqual(token, "tok")
        self.assertEqual([asset["assetBaseId"] for asset in found], ["cc0", "rf"])

    def test_a_royalty_free_material_needs_the_login(self):
        self.answer = {"results": [material("rf", "royalty_free")]}
        with self.logged_in(""), self.assertRaisesRegex(downloads.FetchError, "login.py start"):
            downloads.blendkit_asset("rf")
        with self.logged_in("tok"):
            self.assertEqual(downloads.blendkit_asset("rf")["assetBaseId"], "rf")

    def test_a_material_that_is_not_free_is_refused_even_logged_in(self):
        self.answer = {"results": [material("paid", "royalty_free", free=False)]}
        with self.logged_in("tok"), self.assertRaises(downloads.FetchError):
            downloads.blendkit_asset("paid")

    def test_the_download_asks_for_its_signed_url_with_the_token(self):
        self.answer = {"filePath": "https://files/signed.blend"}
        with tempfile.TemporaryDirectory() as cache, self.logged_in("tok"), \
                mock.patch.object(downloads, "download", side_effect=lambda url, target, size: target) as fetch:
            path = downloads.blendkit_download(material("rf", "royalty_free"), Path(cache))
        url, token = self.calls[0]
        self.assertTrue(url.startswith("https://api/downloads/rf/?scene_uuid="))
        self.assertEqual(token, "tok")
        self.assertEqual(fetch.call_args.args[0], "https://files/signed.blend")
        self.assertEqual(path.name, "blend.blend")


class BlendkitTokenTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.login = Path(self._tmp.name) / "login.py"
        shutil.copy(downloads.BLENDKIT_LOGIN, self.login)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_no_login_means_anonymous(self):
        self.assertEqual(downloads.blendkit_token(self.login), "")
        self.assertEqual(downloads.blendkit_token(Path(self._tmp.name) / "missing.py"), "")

    def test_a_stored_login_gives_its_token(self):
        preferences = self.login.parent / ".data" / "config" / "preferences.json"
        preferences.parent.mkdir(parents=True)
        preferences.write_text(json.dumps({"api_key": "tok", "api_key_refresh": "", "api_key_timeout": 0}))
        self.assertEqual(downloads.blendkit_token(self.login), "tok")


if __name__ == "__main__":
    unittest.main()
