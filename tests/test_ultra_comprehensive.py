# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  SDN Downloader Ultra - COMPREHENSIVE Backend Test Suite                ║
║  Tests every single feature, edge case, and security boundary          ║
║  Coverage: 20 test categories, 100+ individual test cases              ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import downloader
import main
from app_logger import setup_logger, get_diagnostic_info, cleanup_old_logs, log_exception
from version import APP_VERSION, GITHUB_REPO, RELEASE_TAG


class Test01_URLCleaning(unittest.TestCase):
    """FEATURE 1: URL Cleaning & Normalization (15 cases)"""

    def test_standard_youtube_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(downloader.clean_url(url), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_youtu_be_short_link(self):
        self.assertEqual(downloader.clean_url("https://youtu.be/dQw4w9WgXcQ"),
                         "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_shorts_link(self):
        self.assertEqual(downloader.clean_url("https://www.youtube.com/shorts/dQw4w9WgXcQ"),
                         "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_embed_link(self):
        self.assertEqual(downloader.clean_url("https://www.youtube.com/embed/dQw4w9WgXcQ"),
                         "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_playlist_link(self):
        url = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        cleaned = downloader.clean_url(url)
        self.assertIn("list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf", cleaned)
        self.assertIn("/playlist", cleaned)

    def test_mix_rd_playlist_extracts_video(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=RDdQw4w9WgXcQ"
        self.assertEqual(downloader.clean_url(url), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_direct_mix_playlist_url(self):
        url = "https://www.youtube.com/playlist?list=RDdQw4w9WgXcQ"
        self.assertEqual(downloader.clean_url(url), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_watch_later_WL(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=WL"
        self.assertEqual(downloader.clean_url(url), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_liked_list_LL(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=LL"
        self.assertEqual(downloader.clean_url(url), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_preserves_timestamp_t(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120"
        cleaned = downloader.clean_url(url)
        self.assertIn("v=dQw4w9WgXcQ", cleaned)
        self.assertIn("t=120", cleaned)

    def test_non_youtube_url_passthrough(self):
        url = "https://soundcloud.com/artist/track"
        self.assertEqual(downloader.clean_url(url), url)

    def test_empty_url(self):
        self.assertEqual(downloader.clean_url(""), "")

    def test_none_url(self):
        self.assertEqual(downloader.clean_url(None), "")

    def test_whitespace_url(self):
        self.assertEqual(downloader.clean_url("   "), "")

    def test_www_youtu_be(self):
        self.assertEqual(downloader.clean_url("https://www.youtu.be/dQw4w9WgXcQ"),
                         "https://www.youtube.com/watch?v=dQw4w9WgXcQ")


class Test02_URLValidation(unittest.TestCase):
    """FEATURE 2: URL Validation (_is_web_url)"""

    def test_valid_https(self):
        self.assertTrue(downloader._is_web_url("https://example.com/video"))

    def test_valid_http(self):
        self.assertTrue(downloader._is_web_url("http://example.com/video"))

    def test_invalid_ftp(self):
        self.assertFalse(downloader._is_web_url("ftp://example.com"))

    def test_invalid_no_scheme(self):
        self.assertFalse(downloader._is_web_url("invalid-url"))

    def test_invalid_empty(self):
        self.assertFalse(downloader._is_web_url(""))

    def test_invalid_just_protocol(self):
        self.assertFalse(downloader._is_web_url("https://"))

    def test_file_scheme(self):
        self.assertFalse(downloader._is_web_url("file:///C:/test.mp4"))


class Test03_TimeParsing(unittest.TestCase):
    """FEATURE 3: Time Parsing (parse_time_to_seconds)"""

    def test_integer(self):
        self.assertEqual(downloader.parse_time_to_seconds(45), 45.0)

    def test_float(self):
        self.assertEqual(downloader.parse_time_to_seconds(3.5), 3.5)

    def test_zero(self):
        self.assertEqual(downloader.parse_time_to_seconds(0), 0.0)

    def test_string_seconds(self):
        self.assertEqual(downloader.parse_time_to_seconds("90"), 90.0)

    def test_mm_ss_format(self):
        self.assertEqual(downloader.parse_time_to_seconds("01:30"), 90.0)

    def test_hh_mm_ss_format(self):
        self.assertEqual(downloader.parse_time_to_seconds("01:02:03"), 3723.0)

    def test_none(self):
        self.assertIsNone(downloader.parse_time_to_seconds(None))

    def test_empty_string(self):
        self.assertIsNone(downloader.parse_time_to_seconds(""))

    def test_whitespace(self):
        self.assertIsNone(downloader.parse_time_to_seconds("   "))

    def test_invalid_text(self):
        self.assertIsNone(downloader.parse_time_to_seconds("invalid"))

    def test_negative(self):
        self.assertIsNone(downloader.parse_time_to_seconds(-10))

    def test_float_string(self):
        self.assertEqual(downloader.parse_time_to_seconds("45.5"), 45.5)


class Test04_FormatDuration(unittest.TestCase):
    """FEATURE 4: Duration Formatting"""

    def test_zero(self):
        self.assertEqual(downloader.format_duration(0), "00:00")

    def test_seconds(self):
        self.assertEqual(downloader.format_duration(45), "00:45")

    def test_minutes(self):
        self.assertEqual(downloader.format_duration(90), "01:30")

    def test_hours(self):
        self.assertEqual(downloader.format_duration(3723), "01:02:03")

    def test_none(self):
        self.assertEqual(downloader.format_duration(None), "غير معروف")

    def test_large_value(self):
        result = downloader.format_duration(86400)  # 24 hours
        self.assertIn("24", result)

    def test_negative_clamped(self):
        result = downloader.format_duration(-5)
        self.assertEqual(result, "00:00")


class Test05_FormatBytes(unittest.TestCase):
    """FEATURE 5: Byte Formatting"""

    def test_bytes(self):
        self.assertEqual(downloader.format_bytes(500), "500 B")

    def test_kilobytes(self):
        self.assertEqual(downloader.format_bytes(1024), "1.0 KB")

    def test_megabytes(self):
        self.assertEqual(downloader.format_bytes(1024 * 1024), "1.0 MB")

    def test_gigabytes(self):
        self.assertEqual(downloader.format_bytes(1024 * 1024 * 1024 * 2.5), "2.50 GB")

    def test_none(self):
        self.assertEqual(downloader.format_bytes(None), "")

    def test_zero(self):
        self.assertEqual(downloader.format_bytes(0), "0 B")

    def test_terabytes(self):
        result = downloader.format_bytes(1024 ** 4 * 1.5)
        self.assertIn("TB", result)

    def test_get_format_size_with_filesize(self):
        fmt = {"filesize": 1024 * 1024 * 50}
        self.assertEqual(downloader.get_format_size(fmt), "50.0 MB")

    def test_get_format_size_estimated(self):
        fmt = {"tbr": 5000}  # 5000 kbps
        result = downloader.get_format_size(fmt, duration=120)
        self.assertIn("MB", result)

    def test_get_format_size_no_data(self):
        self.assertEqual(downloader.get_format_size({}), "")


class Test06_DownloadOptions(unittest.TestCase):
    """FEATURE 6: Download Options Generation"""

    def test_generates_video_options(self):
        video_opts, _ = downloader.build_download_options()
        self.assertGreaterEqual(len(video_opts), 8)

    def test_generates_audio_options(self):
        _, audio_opts = downloader.build_download_options()
        self.assertGreaterEqual(len(audio_opts), 7)

    def test_video_tags_unique(self):
        video_opts, _ = downloader.build_download_options()
        tags = [o["quality_tag"] for o in video_opts]
        self.assertEqual(len(tags), len(set(tags)))

    def test_audio_tags_unique(self):
        _, audio_opts = downloader.build_download_options()
        tags = [o["quality_tag"] for o in audio_opts]
        self.assertEqual(len(tags), len(set(tags)))

    def test_has_best_quality(self):
        video_opts, _ = downloader.build_download_options()
        tags = [o["quality_tag"] for o in video_opts]
        self.assertIn("Best", tags)

    def test_has_all_resolutions(self):
        video_opts, _ = downloader.build_download_options()
        tags = [o["quality_tag"] for o in video_opts]
        for res in ["1080p", "720p", "480p", "360p", "240p", "144p"]:
            self.assertIn(res, tags, f"Missing resolution: {res}")

    def test_has_audio_formats(self):
        _, audio_opts = downloader.build_download_options()
        tags = [o["quality_tag"] for o in audio_opts]
        for fmt in ["MP3-320k", "MP3-192k", "MP3-128k", "M4A", "FLAC"]:
            self.assertIn(fmt, tags, f"Missing audio format: {fmt}")

    def test_all_video_options_have_format_id(self):
        video_opts, _ = downloader.build_download_options()
        for opt in video_opts:
            self.assertIn("format_id", opt)
            self.assertTrue(len(opt["format_id"]) > 0)

    def test_all_audio_options_have_type(self):
        _, audio_opts = downloader.build_download_options()
        for opt in audio_opts:
            self.assertEqual(opt["type"], "audio")

    def test_all_video_options_are_video_type(self):
        video_opts, _ = downloader.build_download_options()
        for opt in video_opts:
            self.assertEqual(opt["type"], "video")


class Test07_ErrorMessages(unittest.TestCase):
    """FEATURE 7: Error Message Cleaning & Arabic Localization"""

    def test_download_cancelled(self):
        self.assertIn("إلغاء", downloader.clean_error_message(downloader.DownloadCancelled()))

    def test_unviewable_playlist(self):
        self.assertIn("ميكس", downloader.clean_error_message("This playlist type is unviewable"))

    def test_video_unavailable(self):
        self.assertIn("حُذف", downloader.clean_error_message("Video unavailable"))

    def test_private_video(self):
        self.assertIn("خاص", downloader.clean_error_message("This is a private video"))

    def test_login_required(self):
        self.assertIn("تسجيل الدخول", downloader.clean_error_message("Sign in to confirm you're not a bot"))

    def test_members_only(self):
        self.assertIn("تسجيل الدخول", downloader.clean_error_message("Members-only content"))

    def test_unsupported_url(self):
        self.assertIn("غير مدعوم", downloader.clean_error_message("Unsupported URL"))

    def test_http_403(self):
        self.assertIn("403", downloader.clean_error_message("HTTP Error 403: Forbidden"))

    def test_http_429(self):
        self.assertIn("429", downloader.clean_error_message("HTTP Error 429: Too Many Requests"))

    def test_geo_blocked(self):
        self.assertIn("منطقتك", downloader.clean_error_message("Not available in your country"))

    def test_ffmpeg_missing(self):
        self.assertIn("FFmpeg", downloader.clean_error_message("ffmpeg not found"))

    def test_network_error(self):
        self.assertIn("الشبكة", downloader.clean_error_message("Connection timed out"))

    def test_http_404(self):
        self.assertIn("غير موجود", downloader.clean_error_message("HTTP Error 404: Not Found"))

    def test_ansi_escape_stripping(self):
        result = downloader.clean_error_message("\x1b[31mSome error\x1b[0m")
        self.assertNotIn("\x1b", result)

    def test_empty_error(self):
        result = downloader.clean_error_message("")
        self.assertTrue(len(result) > 0)  # Should return generic message

    def test_exception_object(self):
        result = downloader.clean_error_message(RuntimeError("test error"))
        self.assertIsInstance(result, str)


class Test08_ConfigAndHistory(unittest.TestCase):
    """FEATURE 8: Configuration & History Management"""

    def _make_api(self):
        api = object.__new__(main.DownloaderBridgeAPI)
        api._window = None
        return api

    def test_default_save_dir(self):
        api = self._make_api()
        with tempfile.TemporaryDirectory() as tmp_dir:
            downloads = os.path.join(tmp_dir, "Downloads")
            os.makedirs(downloads, exist_ok=True)
            with mock.patch("os.path.expanduser", return_value=tmp_dir):
                save_dir = api._load_save_dir()
                self.assertTrue(os.path.exists(save_dir))

    def test_custom_save_dir_persistence(self):
        api = self._make_api()
        with tempfile.TemporaryDirectory() as tmp_dir:
            custom = os.path.join(tmp_dir, "Custom")
            os.makedirs(custom)
            with mock.patch("os.path.expanduser", return_value=tmp_dir):
                api.save_dir = custom
                api._save_config()
                loaded = api._load_save_dir()
                self.assertEqual(loaded, custom)

    def test_corrupted_config_recovery(self):
        api = self._make_api()
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_file = os.path.join(tmp_dir, ".sdn_config.json")
            downloads = os.path.join(tmp_dir, "Downloads")
            os.makedirs(downloads, exist_ok=True)
            with open(config_file, "w") as f:
                f.write("{invalid json!!!")
            with mock.patch("os.path.expanduser", return_value=tmp_dir):
                save_dir = api._load_save_dir()
                self.assertTrue(os.path.isdir(save_dir))

    def test_empty_history(self):
        api = self._make_api()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with mock.patch("os.path.expanduser", return_value=tmp_dir):
                self.assertEqual(api.get_history(), [])

    def test_add_history_items(self):
        api = self._make_api()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with mock.patch("os.path.expanduser", return_value=tmp_dir):
                api.add_history({"title": "A", "filepath": os.path.join(tmp_dir, "a.mp3")})
                api.add_history({"title": "B", "filepath": os.path.join(tmp_dir, "b.mp4")})
                hist = api.get_history()
                self.assertEqual(len(hist), 2)
                self.assertEqual(hist[0]["title"], "B")  # Most recent first

    def test_history_deduplication(self):
        api = self._make_api()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with mock.patch("os.path.expanduser", return_value=tmp_dir):
                fp = os.path.join(tmp_dir, "song.mp3")
                api.add_history({"title": "V1", "filepath": fp})
                api.add_history({"title": "V2", "filepath": fp})
                hist = api.get_history()
                self.assertEqual(len(hist), 1)
                self.assertEqual(hist[0]["title"], "V2")

    def test_history_max_200(self):
        api = self._make_api()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with mock.patch("os.path.expanduser", return_value=tmp_dir):
                for i in range(210):
                    api.add_history({"title": f"Item {i}", "filepath": os.path.join(tmp_dir, f"f{i}.mp3")})
                hist = api.get_history()
                self.assertLessEqual(len(hist), 200)

    def test_clear_history(self):
        api = self._make_api()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with mock.patch("os.path.expanduser", return_value=tmp_dir):
                api.add_history({"title": "test", "filepath": os.path.join(tmp_dir, "t.mp3")})
                api.clear_history()
                self.assertEqual(api.get_history(), [])

    def test_history_rejects_non_dict(self):
        api = self._make_api()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with mock.patch("os.path.expanduser", return_value=tmp_dir):
                result = api.add_history("not a dict")
                self.assertFalse(result)

    def test_corrupted_history_recovery(self):
        api = self._make_api()
        with tempfile.TemporaryDirectory() as tmp_dir:
            hist_file = os.path.join(tmp_dir, ".sdn_history.json")
            with open(hist_file, "w") as f:
                f.write("CORRUPTED!!!")
            with mock.patch("os.path.expanduser", return_value=tmp_dir):
                self.assertEqual(api.get_history(), [])


class Test09_MediaServer(unittest.TestCase):
    """FEATURE 9: Local Tokenized HTTP Media Server"""

    @classmethod
    def setUpClass(cls):
        cls.api = object.__new__(main.DownloaderBridgeAPI)
        cls.api._media_server = None
        cls.api._media_port = None
        cls.api._media_lock = threading.Lock()
        cls.api._media_tokens = {}
        cls.api._media_path_tokens = {}
        cls.api._media_prepare_lock = threading.Lock()
        cls.api._media_cache_dir = None
        main.MediaHTTPHandler.bridge_api = cls.api
        cls.api._start_local_media_server()

    @classmethod
    def tearDownClass(cls):
        if cls.api._media_server:
            cls.api._media_server.shutdown()
            cls.api._media_server.server_close()

    def test_server_started(self):
        self.assertIsNotNone(self.api._media_port)
        self.assertIsNotNone(self.api._media_server)

    def test_register_file_returns_url(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"ID3" + b"X" * 100)
            path = f.name
        try:
            url = self.api.get_media_url(path)
            self.assertTrue(url.startswith(f"http://127.0.0.1:{self.api._media_port}/media/"))
        finally:
            for _ in range(10):
                try:
                    os.unlink(path)
                    break
                except PermissionError:
                    time.sleep(0.05)

    def test_same_file_same_token(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"ID3" + b"X" * 100)
            path = f.name
        try:
            url1 = self.api.get_media_url(path)
            url2 = self.api.get_media_url(path)
            self.assertEqual(url1, url2)
        finally:
            for _ in range(10):
                try:
                    os.unlink(path)
                    break
                except PermissionError:
                    time.sleep(0.05)

    def test_head_request(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            content = b"ID3-PAYLOAD-" + b"A" * 500
            f.write(content)
            path = f.name
        try:
            url = self.api.get_media_url(path)
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                self.assertEqual(int(resp.headers["Content-Length"]), len(content))
                self.assertEqual(resp.headers["Accept-Ranges"], "bytes")
        finally:
            for _ in range(10):
                try:
                    os.unlink(path)
                    break
                except PermissionError:
                    time.sleep(0.05)

    def test_full_get(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            content = b"ID3-FULL-GET-TEST" + b"B" * 300
            f.write(content)
            path = f.name
        try:
            url = self.api.get_media_url(path)
            with urllib.request.urlopen(url, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                self.assertEqual(resp.read(), content)
        finally:
            for _ in range(10):
                try:
                    os.unlink(path)
                    break
                except PermissionError:
                    time.sleep(0.05)

    def test_range_request_206(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            content = b"0123456789ABCDEF" * 10
            f.write(content)
            path = f.name
        try:
            url = self.api.get_media_url(path)
            req = urllib.request.Request(url, headers={"Range": "bytes=10-25"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 206)
                self.assertEqual(resp.read(), content[10:26])
                self.assertIn("bytes 10-25/", resp.headers["Content-Range"])
        finally:
            for _ in range(10):
                try:
                    os.unlink(path)
                    break
                except PermissionError:
                    time.sleep(0.05)

    def test_invalid_range_416(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            content = b"SHORT"
            f.write(content)
            path = f.name
        try:
            url = self.api.get_media_url(path)
            req = urllib.request.Request(url, headers={"Range": f"bytes={len(content) + 100}-"})
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=5)
            self.assertEqual(ctx.exception.code, 416)
        finally:
            for _ in range(10):
                try:
                    os.unlink(path)
                    break
                except PermissionError:
                    time.sleep(0.05)

    def test_invalid_token_404(self):
        url = f"http://127.0.0.1:{self.api._media_port}/media/invalid_token_1234567890"
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(url, timeout=5)
        self.assertEqual(ctx.exception.code, 404)

    def test_resolve_media_token(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"X" * 100)
            path = f.name
        try:
            url = self.api.get_media_url(path)
            token = url.rsplit("/media/", 1)[1]
            resolved = self.api.resolve_media_token(token)
            self.assertIsNotNone(resolved)
            self.assertTrue(os.path.isfile(resolved))
        finally:
            for _ in range(10):
                try:
                    os.unlink(path)
                    break
                except PermissionError:
                    time.sleep(0.05)

    def test_prune_media_tokens(self):
        """Test that token pruning doesn't crash."""
        with self.api._media_lock:
            original_limit = main.DownloaderBridgeAPI._MEDIA_TOKEN_LIMIT
            try:
                main.DownloaderBridgeAPI._MEDIA_TOKEN_LIMIT = 5
                # Add tokens beyond limit
                for i in range(10):
                    self.api._media_tokens[f"test_prune_{i}"] = f"/fake/path_{i}.mp3"
                self.api._prune_media_tokens_locked()
                self.assertLessEqual(len(self.api._media_tokens),
                                     main.DownloaderBridgeAPI._MEDIA_TOKEN_LIMIT + 5)
            finally:
                main.DownloaderBridgeAPI._MEDIA_TOKEN_LIMIT = original_limit
                # Cleanup test tokens
                for i in range(10):
                    self.api._media_tokens.pop(f"test_prune_{i}", None)


class Test10_MusicScanner(unittest.TestCase):
    """FEATURE 10: Music Scanner"""

    def _make_api(self):
        api = object.__new__(main.DownloaderBridgeAPI)
        api._media_server = None
        api._media_port = 9876
        api._media_lock = threading.Lock()
        api._media_tokens = {}
        api._media_path_tokens = {}
        api._media_prepare_lock = threading.Lock()
        api._media_cache_dir = None
        api.save_dir = ""
        return api

    def test_scan_empty_folder(self):
        api = self._make_api()
        with tempfile.TemporaryDirectory() as tmp:
            result = api.scan_music_folder(tmp)
            self.assertEqual(result["tracks"], [])
            self.assertEqual(result["folder"], tmp)

    def test_scan_nonexistent_folder(self):
        api = self._make_api()
        result = api.scan_music_folder("/nonexistent/path/12345")
        self.assertEqual(result["tracks"], [])

    def test_scan_with_audio_files(self):
        api = self._make_api()
        ffmpeg = downloader.get_ffmpeg_path()
        with tempfile.TemporaryDirectory() as tmp:
            # Create a real WAV file
            wav_path = os.path.join(tmp, "test.wav")
            subprocess.run(
                [ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.5", wav_path],
                capture_output=True, check=True
            )
            # Create a non-audio file (should be ignored)
            Path(tmp, "notes.txt").write_text("not audio")

            result = api.scan_music_folder(tmp)
            self.assertEqual(len(result["tracks"]), 1)
            self.assertEqual(result["tracks"][0]["title"], "test")

    def test_scan_recursive_subdirs(self):
        api = self._make_api()
        ffmpeg = downloader.get_ffmpeg_path()
        with tempfile.TemporaryDirectory() as tmp:
            sub = os.path.join(tmp, "Album")
            os.makedirs(sub)
            wav_path = os.path.join(sub, "track.wav")
            subprocess.run(
                [ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.5", wav_path],
                capture_output=True, check=True
            )
            result = api.scan_music_folder(tmp)
            self.assertEqual(len(result["tracks"]), 1)


class Test11_MediaTranscoding(unittest.TestCase):
    """FEATURE 11: Audio Transcoding for WebView Compatibility"""

    def _make_api(self):
        api = object.__new__(main.DownloaderBridgeAPI)
        api._media_server = None
        api._media_port = 9876
        api._media_lock = threading.Lock()
        api._media_tokens = {}
        api._media_path_tokens = {}
        api._media_prepare_lock = threading.Lock()
        api._media_cache_dir = None
        return api

    def test_mp3_served_directly(self):
        api = self._make_api()
        ffmpeg = downloader.get_ffmpeg_path()
        with tempfile.TemporaryDirectory() as tmp:
            api._media_cache_dir = os.path.join(tmp, "cache")
            mp3_path = os.path.join(tmp, "direct.mp3")
            subprocess.run(
                [ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.5",
                 "-c:a", "libmp3lame", mp3_path],
                capture_output=True, check=True
            )
            result = api.prepare_media_playback(mp3_path)
            self.assertTrue(result["ok"])
            self.assertFalse(result["transcoded"])

    def test_wav_served_directly(self):
        api = self._make_api()
        ffmpeg = downloader.get_ffmpeg_path()
        with tempfile.TemporaryDirectory() as tmp:
            api._media_cache_dir = os.path.join(tmp, "cache")
            wav_path = os.path.join(tmp, "direct.wav")
            subprocess.run(
                [ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.5", wav_path],
                capture_output=True, check=True
            )
            result = api.prepare_media_playback(wav_path)
            self.assertTrue(result["ok"])
            self.assertFalse(result["transcoded"])

    def test_flac_transcoded_to_mp3(self):
        api = self._make_api()
        ffmpeg = downloader.get_ffmpeg_path()
        with tempfile.TemporaryDirectory() as tmp:
            api._media_cache_dir = os.path.join(tmp, "cache")
            flac_path = os.path.join(tmp, "transcode.flac")
            subprocess.run(
                [ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.5", flac_path],
                capture_output=True, check=True
            )
            result = api.prepare_media_playback(flac_path)
            self.assertTrue(result["ok"])
            self.assertTrue(result["transcoded"])

    def test_nonexistent_file(self):
        api = self._make_api()
        result = api.prepare_media_playback("/nonexistent/file.mp3")
        self.assertFalse(result["ok"])

    def test_non_audio_file(self):
        api = self._make_api()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"not audio")
            path = f.name
        try:
            result = api.prepare_media_playback(path)
            self.assertFalse(result["ok"])
        finally:
            for _ in range(10):
                try:
                    os.unlink(path)
                    break
                except PermissionError:
                    time.sleep(0.05)


class Test12_FileTrimming(unittest.TestCase):
    """FEATURE 12: FFmpeg File Trimming"""

    @classmethod
    def setUpClass(cls):
        cls.ffmpeg = downloader.get_ffmpeg_path()
        assert os.path.isfile(cls.ffmpeg)

    def _make_test_video(self, tmp_dir, duration=5):
        path = os.path.join(tmp_dir, f"test_{duration}s.mp4")
        subprocess.run(
            [self.ffmpeg, "-y",
             "-f", "lavfi", "-i", f"testsrc=duration={duration}:size=320x240:rate=30",
             "-f", "lavfi", "-i", f"sine=frequency=1000:duration={duration}",
             "-c:v", "libx264", "-c:a", "aac", path],
            capture_output=True, check=True
        )
        return path

    def test_trim_start_only(self):
        dl = downloader.MediaDownloader()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._make_test_video(tmp)
            original_size = os.path.getsize(path)
            dl._trim_file(path, "00:02", None)
            self.assertTrue(os.path.isfile(path))
            self.assertGreater(os.path.getsize(path), 0)
            self.assertLess(os.path.getsize(path), original_size)

    def test_trim_start_and_end(self):
        dl = downloader.MediaDownloader()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._make_test_video(tmp)
            dl._trim_file(path, "00:01", "00:03")
            self.assertTrue(os.path.isfile(path))
            self.assertGreater(os.path.getsize(path), 0)

    def test_no_trim_when_none(self):
        dl = downloader.MediaDownloader()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._make_test_video(tmp, 2)
            original_size = os.path.getsize(path)
            dl._trim_file(path, None, None)
            self.assertEqual(os.path.getsize(path), original_size)


class Test13_ExtensionServer(unittest.TestCase):
    """FEATURE 13: Browser Extension HTTP Bridge Security"""

    @classmethod
    def setUpClass(cls):
        cls.api = object.__new__(main.DownloaderBridgeAPI)
        cls.api._window = None
        cls.received_urls = []
        cls.api.handle_extension_url = lambda u: cls.received_urls.append(u)
        main.ExtensionHTTPHandler.bridge_api = cls.api
        main.ExtensionHTTPHandler.auth_token = None

        # Find a free port
        import socket
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        cls.port = sock.getsockname()[1]
        sock.close()

        cls.server = main.HTTPServer(('127.0.0.1', cls.port), main.ExtensionHTTPHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_reject_non_extension_origin(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/", method="OPTIONS")
        req.add_header("Origin", "https://evil-site.com")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=3)
        self.assertEqual(ctx.exception.code, 403)

    def test_allow_chrome_extension_origin(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/", method="OPTIONS")
        req.add_header("Origin", "chrome-extension://test123")
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 204)

    def test_allow_moz_extension_origin(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/", method="OPTIONS")
        req.add_header("Origin", "moz-extension://test456")
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 204)

    def test_post_valid_url(self):
        origin = "chrome-extension://test_post_valid"
        data = json.dumps({"url": "https://www.youtube.com/watch?v=test123"}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/",
            data=data,
            headers={"Content-Type": "application/json", "Origin": origin}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            body = json.loads(resp.read())
            self.assertEqual(body["status"], "ok")

    def test_post_no_url_rejected(self):
        origin = "chrome-extension://test_no_url"
        data = json.dumps({}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/",
            data=data,
            headers={"Content-Type": "application/json", "Origin": origin}
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=3)
        self.assertEqual(ctx.exception.code, 400)

    def test_cors_headers_present(self):
        origin = "chrome-extension://test_cors"
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/", method="OPTIONS")
        req.add_header("Origin", origin)
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), origin)

    def test_is_allowed_extension_origin(self):
        self.assertTrue(main._is_allowed_extension_origin("chrome-extension://abc123"))
        self.assertTrue(main._is_allowed_extension_origin("moz-extension://abc"))
        self.assertTrue(main._is_allowed_extension_origin("safari-web-extension://abc"))
        self.assertFalse(main._is_allowed_extension_origin("https://evil.com"))
        self.assertFalse(main._is_allowed_extension_origin(""))
        self.assertFalse(main._is_allowed_extension_origin(None))


class Test14_AppUpdate(unittest.TestCase):
    """FEATURE 14: App Update Logic & SHA-256 Verification"""

    def test_version_comparison_greater(self):
        self.assertGreater(main._version_key("v2.0.1"), main._version_key("v2.0.0"))

    def test_version_comparison_equal(self):
        self.assertEqual(main._version_key("v2.0.0"), main._version_key("2.0.0"))

    def test_version_comparison_major(self):
        self.assertGreater(main._version_key("2.1.0"), main._version_key("2.0.9"))

    def test_version_comparison_minor(self):
        self.assertGreater(main._version_key("1.0.5"), main._version_key("1.0.4"))

    def test_version_key_v_prefix(self):
        self.assertEqual(main._version_key("V1.0.5"), main._version_key("v1.0.5"))

    def test_sha256_verification_pass(self):
        api = object.__new__(main.DownloaderBridgeAPI)
        with tempfile.TemporaryDirectory() as tmp:
            content = b"MZ" + b"X" * (1024 * 1024)
            path = os.path.join(tmp, "update.exe")
            with open(path, "wb") as f:
                f.write(content)

            correct_hash = hashlib.sha256(content).hexdigest()
            api.pending_update_path = path
            api.pending_update_size = len(content)
            api.pending_update_sha256 = correct_hash

            resolved = api._resolve_pending_update(path)
            self.assertEqual(Path(resolved), Path(path).resolve())

    def test_sha256_verification_fail(self):
        api = object.__new__(main.DownloaderBridgeAPI)
        with tempfile.TemporaryDirectory() as tmp:
            content = b"MZ" + b"X" * (1024 * 1024)
            path = os.path.join(tmp, "update.exe")
            with open(path, "wb") as f:
                f.write(content)

            api.pending_update_path = path
            api.pending_update_size = len(content)
            api.pending_update_sha256 = "0" * 64  # Wrong hash

            with self.assertRaises(RuntimeError) as ctx:
                api._resolve_pending_update(path)
            self.assertIn("بصمة", str(ctx.exception))

    def test_mz_header_check(self):
        api = object.__new__(main.DownloaderBridgeAPI)
        with tempfile.TemporaryDirectory() as tmp:
            content = b"NOT_MZ" + b"X" * (1024 * 1024)  # No MZ header
            path = os.path.join(tmp, "fake.exe")
            with open(path, "wb") as f:
                f.write(content)

            api.pending_update_path = path
            api.pending_update_size = len(content)
            api.pending_update_sha256 = hashlib.sha256(content).hexdigest()

            with self.assertRaises(RuntimeError):
                api._resolve_pending_update(path)

    def test_too_small_file_rejected(self):
        api = object.__new__(main.DownloaderBridgeAPI)
        with tempfile.TemporaryDirectory() as tmp:
            content = b"MZ" + b"X" * 100  # Too small (< 1 MB)
            path = os.path.join(tmp, "small.exe")
            with open(path, "wb") as f:
                f.write(content)

            api.pending_update_path = path
            api.pending_update_size = len(content)
            api.pending_update_sha256 = hashlib.sha256(content).hexdigest()

            with self.assertRaises(RuntimeError):
                api._resolve_pending_update(path)

    def test_missing_pending_update(self):
        api = object.__new__(main.DownloaderBridgeAPI)
        api.pending_update_path = None
        with self.assertRaises(RuntimeError):
            api._resolve_pending_update()

    def test_release_asset_details(self):
        assets = [
            {"name": "SDN_Downloader_Setup.exe", "browser_download_url": "https://example.com/setup.exe",
             "digest": "sha256:abc123", "size": 1000}
        ]
        result = main._release_asset_details(assets, "SDN_Downloader_Setup.exe")
        self.assertIsNotNone(result)
        self.assertEqual(result["sha256"], "abc123")
        self.assertEqual(result["size"], 1000)

    def test_release_asset_not_found(self):
        result = main._release_asset_details([], "nonexistent.exe")
        self.assertIsNone(result)

    def test_trusted_update_hosts(self):
        self.assertIn("github.com", main.TRUSTED_UPDATE_HOSTS)
        self.assertIn("objects.githubusercontent.com", main.TRUSTED_UPDATE_HOSTS)


class Test15_BridgeAPI(unittest.TestCase):
    """FEATURE 15: DownloaderBridgeAPI"""

    def test_api_creation(self):
        api = main.DownloaderBridgeAPI()
        self.assertIsNotNone(api)
        if api._media_server:
            api._media_server.shutdown()

    def test_get_app_info(self):
        api = object.__new__(main.DownloaderBridgeAPI)
        api._window = None
        api.save_dir = os.path.expanduser("~/Downloads")
        info = api.get_app_info()
        self.assertEqual(info["version"], APP_VERSION)
        self.assertEqual(info["repo"], GITHUB_REPO)
        self.assertIn("yt_dlp_version", info)

    def test_set_window(self):
        api = object.__new__(main.DownloaderBridgeAPI)
        api._window = None
        api.set_window("mock_window")
        self.assertEqual(api._window, "mock_window")

    def test_get_save_dir(self):
        api = object.__new__(main.DownloaderBridgeAPI)
        api.save_dir = "/test/path"
        self.assertEqual(api.get_save_dir(), "/test/path")

    def test_all_public_methods_exist(self):
        api = object.__new__(main.DownloaderBridgeAPI)
        expected_methods = [
            'get_app_info', 'get_save_dir', 'set_window', 'open_folder',
            'locate_file', 'choose_folder', 'choose_cookie_file',
            'get_clipboard', 'validate_link', 'fetch_info', 'start_download',
            'cancel_download', 'check_app_update', 'apply_app_update',
            'restart_and_apply_update', 'scan_music_folder', 'add_music_files',
            'delete_music_track', 'get_history', 'add_history', 'clear_history',
            'handle_extension_url', 'get_media_url', 'prepare_media_playback',
            'resolve_media_token', 'report_audio_error', 'resize_window',
        ]
        for method_name in expected_methods:
            self.assertTrue(
                hasattr(api, method_name) and callable(getattr(api, method_name)),
                f"Missing method: {method_name}"
            )


class Test16_Logger(unittest.TestCase):
    """FEATURE 16: Logging & Diagnostics"""

    def test_setup_logger(self):
        logger = setup_logger("SDN.UltraTest")
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "SDN.UltraTest")

    def test_logger_idempotent(self):
        l1 = setup_logger("SDN.Idem")
        l2 = setup_logger("SDN.Idem")
        self.assertIs(l1, l2)

    def test_diagnostic_info(self):
        info = get_diagnostic_info()
        self.assertIn("os", info)
        self.assertIn("python_version", info)
        self.assertIn("frozen", info)
        self.assertIn("cpu_count", info)
        self.assertIn("log_file", info)
        self.assertIn("timestamp", info)

    def test_cleanup_old_logs(self):
        # Should not raise
        cleanup_old_logs()

    def test_log_exception(self):
        logger = setup_logger("SDN.ExcTest")
        try:
            raise ValueError("test error")
        except ValueError:
            log_exception(logger, "Test exception")

    def test_log_exception_no_active(self):
        logger = setup_logger("SDN.NoExcTest")
        log_exception(logger, "No active exception")  # Should not raise


class Test17_VersionModule(unittest.TestCase):
    """FEATURE 17: Version Module"""

    def test_version_format(self):
        parts = APP_VERSION.split(".")
        self.assertEqual(len(parts), 3)
        for p in parts:
            self.assertTrue(p.isdigit())

    def test_github_repo_format(self):
        self.assertIn("/", GITHUB_REPO)
        parts = GITHUB_REPO.split("/")
        self.assertEqual(len(parts), 2)

    def test_release_tag(self):
        self.assertEqual(RELEASE_TAG, f"v{APP_VERSION}")

    def test_current_version(self):
        import re
        self.assertRegex(APP_VERSION, r"^\d+\.\d+\.\d+$")


class Test18_PlaylistDetection(unittest.TestCase):
    """FEATURE 18: Playlist Type Detection"""

    def test_rd_mix_is_unviewable(self):
        self.assertTrue(downloader.is_unviewable_playlist_id("RDdQw4w9WgXcQ"))

    def test_rdmm_is_unviewable(self):
        self.assertTrue(downloader.is_unviewable_playlist_id("RDMMdQw4w9WgXcQ"))

    def test_ul_is_unviewable(self):
        self.assertTrue(downloader.is_unviewable_playlist_id("ULdQw4w9WgXcQ"))

    def test_wl_is_unviewable(self):
        self.assertTrue(downloader.is_unviewable_playlist_id("WL"))

    def test_ll_is_unviewable(self):
        self.assertTrue(downloader.is_unviewable_playlist_id("LL"))

    def test_lm_is_unviewable(self):
        self.assertTrue(downloader.is_unviewable_playlist_id("LM"))

    def test_pl_is_viewable(self):
        self.assertFalse(downloader.is_unviewable_playlist_id("PLrAXtmErZgOei"))

    def test_empty_is_not_unviewable(self):
        self.assertFalse(downloader.is_unviewable_playlist_id(""))

    def test_none_is_not_unviewable(self):
        self.assertFalse(downloader.is_unviewable_playlist_id(None))

    def test_extract_video_from_rd(self):
        vid = downloader.extract_video_id_from_mix("RDdQw4w9WgXcQ")
        self.assertEqual(vid, "dQw4w9WgXcQ")

    def test_extract_video_from_rdmm(self):
        vid = downloader.extract_video_id_from_mix("RDMMdQw4w9WgXcQ")
        self.assertEqual(vid, "dQw4w9WgXcQ")

    def test_extract_from_empty(self):
        self.assertIsNone(downloader.extract_video_id_from_mix(""))

    def test_extract_from_none(self):
        self.assertIsNone(downloader.extract_video_id_from_mix(None))


class Test19_SafeQualityTag(unittest.TestCase):
    """FEATURE 19: Quality Tag Sanitization"""

    def test_normal_tag(self):
        self.assertEqual(downloader._safe_quality_tag({"quality_tag": "720p"}), "720p")

    def test_special_characters(self):
        tag = downloader._safe_quality_tag({"quality_tag": "MP3 320k (Best!)"})
        self.assertFalse(any(c in tag for c in " ()!"))

    def test_empty_option(self):
        tag = downloader._safe_quality_tag({})
        self.assertTrue(len(tag) > 0)

    def test_length_limit(self):
        tag = downloader._safe_quality_tag({"quality_tag": "A" * 100})
        self.assertLessEqual(len(tag), 32)


class Test20_DownloadLock(unittest.TestCase):
    """FEATURE 20: Download Lock & Cancel"""

    def test_cancel_event(self):
        dl = downloader.MediaDownloader()
        self.assertFalse(dl._cancel_event.is_set())
        dl.cancel()
        self.assertTrue(dl._cancel_event.is_set())
        dl._cancel_event.clear()
        self.assertFalse(dl._cancel_event.is_set())

    def test_download_lock_exists(self):
        dl = downloader.MediaDownloader()
        self.assertIsNotNone(dl._download_lock)

    def test_ffmpeg_path_set(self):
        dl = downloader.MediaDownloader()
        self.assertTrue(os.path.isfile(dl.ffmpeg_path))

    def test_download_cancelled_exception(self):
        with self.assertRaises(downloader.DownloadCancelled):
            raise downloader.DownloadCancelled("cancelled")


class Test21_IntegrationChecks(unittest.TestCase):
    """BONUS: Integration & Cross-Module Checks"""

    def test_version_consistency_py_and_html(self):
        """Version in version.py must match UI index.html"""
        html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        self.assertIn(f"'{APP_VERSION}'", html_content,
                      f"Version {APP_VERSION} not found in ui/index.html")

    def test_dist_artifacts_exist(self):
        """All required build artifacts must exist in dist/ (skipped on clean checkouts)"""
        dist_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
        required = ["SDN_Downloader_Setup.exe", "SDN_Downloader_Standalone.exe", "SDN_Downloader_Ultra.apk"]
        missing = [name for name in required if not os.path.isfile(os.path.join(dist_dir, name))]
        if missing:
            self.skipTest(f"Build artifacts are not present (release assets): {', '.join(missing)}")
        for filename in required:
            path = os.path.join(dist_dir, filename)
            self.assertGreater(os.path.getsize(path), 1024 * 1024,
                               f"Artifact too small: {filename}")

    def test_ffmpeg_binary_exists(self):
        root = os.path.dirname(os.path.dirname(__file__))
        ffmpeg_path = os.path.join(root, "ffmpeg.exe")
        if not os.path.isfile(ffmpeg_path):
            self.skipTest("ffmpeg.exe is a release binary and is not committed")
        self.assertTrue(os.path.isfile(ffmpeg_path))

    def test_ui_files_exist(self):
        root = os.path.dirname(os.path.dirname(__file__))
        self.assertTrue(os.path.isfile(os.path.join(root, "ui", "index.html")))
        self.assertTrue(os.path.isfile(os.path.join(root, "ui", "installer.html")))

    def test_youtube_browser_methods(self):
        import main
        api = main.DownloaderBridgeAPI()
        # Test quick_download_from_browser
        res1 = api.quick_download_from_browser("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "best")
        self.assertTrue(res1.get("success"))

        # Test load_url_in_main
        res2 = api.load_url_in_main("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertTrue(res2.get("success"))

        # Test YouTubeBrowserBridge
        bridge = main.YouTubeBrowserBridge(api)
        res3 = bridge.download_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "mp3")
        self.assertTrue(res3.get("success") or res3.get("busy"))
        res4 = bridge.send_to_main("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertTrue(res4.get("success"))

    def test_mix_playlist_preserved_in_full_mode(self):
        url = "https://www.youtube.com/watch?v=ndCI8DIM86w&list=RDndCI8DIM86w"
        # In single/default mode, mix is stripped to single video
        cleaned_single = downloader.clean_url(url, keep_mix_playlist=False)
        self.assertEqual(cleaned_single, "https://www.youtube.com/watch?v=ndCI8DIM86w")
        # In playlist mode, mix is preserved with both v and list
        cleaned_pl = downloader.clean_url(url, keep_mix_playlist=True)
        self.assertEqual(cleaned_pl, "https://www.youtube.com/watch?v=ndCI8DIM86w&list=RDndCI8DIM86w")


if __name__ == "__main__":
    unittest.main(verbosity=2)
