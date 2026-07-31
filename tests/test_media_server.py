import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import main


class MediaServerTests(unittest.TestCase):
    def setUp(self):
        self.api = object.__new__(main.DownloaderBridgeAPI)
        self.api._media_server = None
        self.api._media_port = None
        self.api._media_lock = threading.Lock()
        self.api._media_tokens = {}
        self.api._media_path_tokens = {}
        main.MediaHTTPHandler.bridge_api = self.api
        self.api._start_local_media_server()
        self.assertIsNotNone(self.api._media_port)

    def tearDown(self):
        if self.api._media_server:
            self.api._media_server.shutdown()
            self.api._media_server.server_close()

    def test_tokenized_media_url_supports_head_and_byte_ranges(self):
        with tempfile.TemporaryDirectory() as directory:
            media_path = Path(directory) / "sample.mp3"
            payload = bytes(range(256)) * 4
            media_path.write_bytes(payload)

            scanned = self.api.scan_music_folder(directory)
            self.assertEqual(len(scanned["tracks"]), 1)
            media_url = scanned["tracks"][0]["playable_url"]
            self.assertTrue(media_url.startswith("http://127.0.0.1:"))
            self.assertNotIn(media_path.name, media_url)

            head_request = urllib.request.Request(media_url, method="HEAD")
            with urllib.request.urlopen(head_request, timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(int(response.headers["Content-Length"]), len(payload))
                self.assertEqual(response.headers["Accept-Ranges"], "bytes")

            range_request = urllib.request.Request(
                media_url,
                headers={"Range": "bytes=10-29"},
            )
            with urllib.request.urlopen(range_request, timeout=5) as response:
                self.assertEqual(response.status, 206)
                self.assertEqual(response.headers["Content-Range"], f"bytes 10-29/{len(payload)}")
                self.assertEqual(response.read(), payload[10:30])

    def test_unknown_media_token_returns_not_found(self):
        bad_url = f"http://127.0.0.1:{self.api._media_port}/media/{'x' * 32}"
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(bad_url, timeout=5)
        self.assertEqual(error.exception.code, 404)
        error.exception.close()
