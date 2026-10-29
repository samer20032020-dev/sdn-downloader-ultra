import urllib.parse
import unittest
from unittest.mock import MagicMock


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


if __name__ == "__main__":
    unittest.main()

