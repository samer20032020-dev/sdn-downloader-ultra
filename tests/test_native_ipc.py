import re
import urllib.parse
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN_SRC = ROOT / "main.py"


class TestNativeIPC(unittest.TestCase):
    def test_sdn_internal_url_parsing(self):
        url = "https://sdn.internal/action?cmd=download&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dtest123&quality=mp3&mode=playlist_all&force=0&title=%D9%85%D9%8A%D9%83%D8%B3%20%D8%A7%D8%BA%D8%A7%D9%86%D9%8A"
        parsed = urllib.parse.urlsplit(url)
        self.assertEqual(parsed.netloc, "sdn.internal")
        self.assertEqual(parsed.path, "/action")
        q = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(q.get("cmd", [""])[0], "download")
        self.assertEqual(q.get("url", [""])[0], "https://www.youtube.com/watch?v=test123")
        self.assertEqual(q.get("quality", [""])[0], "mp3")
        self.assertEqual(q.get("mode", [""])[0], "playlist_all")
        self.assertEqual(q.get("title", [""])[0], "ميكس اغاني")

    def test_sdn_internal_cancel_parsing(self):
        url = "https://sdn.internal/action?cmd=cancel"
        parsed = urllib.parse.urlsplit(url)
        q = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(q.get("cmd", [""])[0], "cancel")


class TestNativeIPCAuthToken(unittest.TestCase):
    """Regression tests for the sdn.internal auth-token contract.

    The WebResourceRequested handler rejects every request without the
    per-process token, so the injected sdnCall bridge must send it on every
    command (download / cancel / send_to_main / open_folder / locate_file).
    """

    @classmethod
    def setUpClass(cls):
        cls.src = MAIN_SRC.read_text(encoding="utf-8")

    def test_sdn_call_sends_token_placeholder(self):
        self.assertIn("params.token = '__SDN_IPC_TOKEN__'", self.src)

    def test_token_placeholder_is_replaced_with_secret(self):
        self.assertIn("_NATIVE_IPC_SECRET", self.src)
        self.assertIn(
            "YOUTUBE_IDM_ADBLOCK_SCRIPT.replace('__SDN_IPC_TOKEN__', _NATIVE_IPC_SECRET)",
            self.src,
        )

    def test_every_injection_point_uses_token_filled_helper(self):
        # No injection site may use the raw (token-less) script constant.
        self.assertNotIn(
            "AddScriptToExecuteOnDocumentCreatedAsync(YOUTUBE_IDM_ADBLOCK_SCRIPT)",
            self.src,
        )
        self.assertNotIn("evaluate_js(YOUTUBE_IDM_ADBLOCK_SCRIPT)", self.src)
        # The three real injection points:
        #   1) AddScriptToExecuteOnDocumentCreatedAsync
        #   2) browser_win.evaluate_js (loaded event)
        #   3) inject_loop concatenation
        self.assertIn("AddScriptToExecuteOnDocumentCreatedAsync(_adblock_script())", self.src)
        self.assertIn("evaluate_js(_adblock_script())", self.src)
        self.assertIn('_adblock_script() + " } else {', self.src)

    def test_dead_postmessage_path_removed(self):
        # This fallback reported a fake success without any Python handler,
        # which prevented the tokenized sdn.internal path from ever running.
        self.assertNotIn("via: 'post_message'", self.src)

    def test_token_roundtrip_through_url(self):
        token = "sdn-token_ABC-123"
        query = urllib.parse.urlencode({"cmd": "download", "token": token})
        parsed = urllib.parse.urlsplit("https://sdn.internal/action?" + query)
        q = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(q["token"][0], token)

    def test_python_handler_still_requires_token(self):
        self.assertIn("secrets.compare_digest(token, _NATIVE_IPC_SECRET)", self.src)


if __name__ == "__main__":
    unittest.main()

