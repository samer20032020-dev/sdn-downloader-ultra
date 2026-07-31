import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import downloader


class FakeYoutubeDL:
    instances = []
    info = {}

    def __init__(self, options):
        self.options = options
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def extract_info(self, url, download=False):
        if not download:
            return self.__class__.info

        template = self.options["outtmpl"]
        title = "Sample"
        media_id = "abc123"
        extension = "mp4"
        postprocessors = self.options.get("postprocessors") or []
        if postprocessors and postprocessors[0].get("key") == "FFmpegExtractAudio":
            extension = postprocessors[0].get("preferredcodec", "mp3")
        output = (
            template
            .replace("%(title).180B", title)
            .replace("%(title).160B", title)
            .replace("%(playlist_title|Playlist).120B", "Playlist")
            .replace("%(playlist_index)03d", "001")
            .replace("%(id)s", media_id)
            .replace("%(ext)s", extension)
        )
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_bytes(b"media")

        info = {
            "id": media_id,
            "title": title,
            "filepath": output,
            "_filename": output,
            "playlist_index": 1,
            "n_entries": 1,
        }
        for hook in self.options.get("progress_hooks") or []:
            hook(
                {
                    "status": "downloading",
                    "downloaded_bytes": 50,
                    "total_bytes": 100,
                    "speed": 10,
                    "eta": 5,
                    "info_dict": info,
                }
            )
            hook({"status": "finished", "filename": output, "info_dict": info})
        for hook in self.options.get("postprocessor_hooks") or []:
            hook({"status": "finished", "info_dict": info})
        return info


class DownloaderTests(unittest.TestCase):
    def setUp(self):
        FakeYoutubeDL.instances = []

    def test_clean_url_preserves_playlist_parameters(self):
        cleaned = downloader.clean_url("https://youtu.be/abc123?list=PL42&t=5")
        self.assertIn("v=abc123", cleaned)
        self.assertIn("list=PL42", cleaned)
        self.assertIn("t=5", cleaned)

    def test_options_have_distinct_quality_tags(self):
        video, audio = downloader.build_download_options()
        tags = [item["quality_tag"] for item in video + audio]
        self.assertEqual(len(tags), len(set(tags)))
        self.assertTrue(any(item["ext"] == "m4a" for item in audio))
        self.assertTrue(any(item["ext"] == "flac" for item in audio))

    @patch("downloader.yt_dlp.YoutubeDL", FakeYoutubeDL)
    def test_fetch_playlist_exposes_selectable_entries(self):
        FakeYoutubeDL.info = {
            "_type": "playlist",
            "title": "My list",
            "entries": [
                {"id": "one", "title": "First", "playlist_index": 1},
                {"id": "two", "title": "Second", "playlist_index": 2},
            ],
        }
        result = downloader.MediaDownloader().fetch_info("https://example.com/list")
        self.assertTrue(result["is_playlist"])
        self.assertEqual(result["entry_count"], 2)
        self.assertEqual([item["index"] for item in result["items"]], [1, 2])

    @patch("downloader.yt_dlp.YoutubeDL", FakeYoutubeDL)
    def test_repeated_downloads_get_unique_paths(self):
        FakeYoutubeDL.info = {"id": "abc123", "title": "Sample"}
        engine = downloader.MediaDownloader()
        option = {
            "type": "video",
            "ext": "mp4",
            "quality_tag": "720p",
            "format_id": "best",
        }
        with tempfile.TemporaryDirectory() as directory:
            first = engine.download("https://example.com/video", option, directory)
            second = engine.download("https://example.com/video", option, directory)
            self.assertNotEqual(first["filepath"], second["filepath"])
            self.assertTrue(os.path.isfile(first["filepath"]))
            self.assertTrue(os.path.isfile(second["filepath"]))

    @patch("downloader.yt_dlp.YoutubeDL", FakeYoutubeDL)
    def test_playlist_selection_and_audio_codec_reach_ytdlp(self):
        engine = downloader.MediaDownloader()
        option = {
            "type": "audio",
            "ext": "m4a",
            "quality_tag": "M4A",
            "format_id": "bestaudio",
            "is_playlist": True,
            "playlist_items": [3, 1, 3, "bad"],
            "playlist_count": 2,
        }
        with tempfile.TemporaryDirectory() as directory:
            result = engine.download("https://example.com/list", option, directory)
        settings = FakeYoutubeDL.instances[-1].options
        self.assertEqual(settings["playlist_items"], "1,3")
        self.assertFalse(settings["noplaylist"])
        self.assertEqual(settings["postprocessors"][0]["preferredcodec"], "m4a")
        self.assertEqual(result["media_type"], "audio")
        self.assertTrue(result["files"][0]["playable_url"].startswith("file:"))

    def test_error_messages_are_user_friendly(self):
        self.assertIn("خاص", downloader.clean_error_message("ERROR: Private video"))
        self.assertIn("الشبكة", downloader.clean_error_message("connection timed out"))


if __name__ == "__main__":
    unittest.main()
