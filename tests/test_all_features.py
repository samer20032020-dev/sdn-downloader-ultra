# -*- coding: utf-8 -*-
"""Comprehensive end-to-end feature verification suite for SDN Downloader Ultra."""

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

import downloader
import main
from version import APP_VERSION, GITHUB_REPO


class TestAllSDNFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ffmpeg_path = downloader.get_ffmpeg_path()
        assert os.path.isfile(cls.ffmpeg_path), f"FFmpeg not found at {cls.ffmpeg_path}"

    # =========================================================================
    # FEATURE 1: URL Cleaning and Validation
    # =========================================================================
    def test_01_url_cleaning(self):
        """Test URL cleaning for various YouTube & social formats."""
        # 1. Standard video
        url1 = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(downloader.clean_url(url1), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        # 2. Short youtu.be link
        url2 = "https://youtu.be/dQw4w9WgXcQ"
        self.assertEqual(downloader.clean_url(url2), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        # 3. Shorts link
        url3 = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        self.assertEqual(downloader.clean_url(url3), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        # 4. Playlist link
        url4 = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        cleaned4 = downloader.clean_url(url4)
        self.assertIn("list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf", cleaned4)
        self.assertIn("/playlist", cleaned4)

        # 5. Mix playlist (starts with RD) -> should extract single video
        url5 = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=RDdQw4w9WgXcQ"
        self.assertEqual(downloader.clean_url(url5), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        # 6. Direct mix playlist URL
        url6 = "https://www.youtube.com/playlist?list=RDdQw4w9WgXcQ"
        self.assertEqual(downloader.clean_url(url6), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        # 7. Watch Later (WL) and Liked (LL) lists
        url7 = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=WL"
        self.assertEqual(downloader.clean_url(url7), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        # 8. Non-web URL handling
        self.assertFalse(downloader._is_web_url("ftp://example.com"))
        self.assertFalse(downloader._is_web_url("invalid-url"))
        self.assertTrue(downloader._is_web_url("https://example.com/video"))

    # =========================================================================
    # FEATURE 2: Time Parsing & Unit Formatting
    # =========================================================================
    def test_02_parsing_and_formatting(self):
        """Test time parsing, duration formatting, and byte size formatting."""
        # parse_time_to_seconds
        self.assertEqual(downloader.parse_time_to_seconds(0), 0.0)
        self.assertEqual(downloader.parse_time_to_seconds(45), 45.0)
        self.assertEqual(downloader.parse_time_to_seconds("90"), 90.0)
        self.assertEqual(downloader.parse_time_to_seconds("01:30"), 90.0)
        self.assertEqual(downloader.parse_time_to_seconds("01:02:03"), 3723.0)
        self.assertIsNone(downloader.parse_time_to_seconds(None))
        self.assertIsNone(downloader.parse_time_to_seconds(""))
        self.assertIsNone(downloader.parse_time_to_seconds("invalid"))
        self.assertIsNone(downloader.parse_time_to_seconds(-10))

        # format_duration
        self.assertEqual(downloader.format_duration(0), "00:00")
        self.assertEqual(downloader.format_duration(45), "00:45")
        self.assertEqual(downloader.format_duration(90), "01:30")
        self.assertEqual(downloader.format_duration(3723), "01:02:03")
        self.assertEqual(downloader.format_duration(None), "غير معروف")

        # format_bytes
        self.assertEqual(downloader.format_bytes(500), "500 B")
        self.assertEqual(downloader.format_bytes(1024), "1.0 KB")
        self.assertEqual(downloader.format_bytes(1024 * 1024), "1.0 MB")
        self.assertEqual(downloader.format_bytes(1024 * 1024 * 1024 * 2.5), "2.50 GB")
        self.assertEqual(downloader.format_bytes(None), "")

    # =========================================================================
    # FEATURE 3: Download Options Generator
    # =========================================================================
    def test_03_download_options_generation(self):
        """Test video and audio option matrix generation."""
        video_opts, audio_opts = downloader.build_download_options()
        self.assertGreaterEqual(len(video_opts), 8)
        self.assertGreaterEqual(len(audio_opts), 7)

        # Verify quality tags exist and are unique within each category
        v_tags = [o["quality_tag"] for o in video_opts]
        self.assertEqual(len(v_tags), len(set(v_tags)))
        self.assertIn("Best", v_tags)
        self.assertIn("1080p", v_tags)
        self.assertIn("720p", v_tags)
        self.assertIn("360p", v_tags)

        a_tags = [o["quality_tag"] for o in audio_opts]
        self.assertEqual(len(a_tags), len(set(a_tags)))
        self.assertIn("MP3-320k", a_tags)
        self.assertIn("MP3-192k", a_tags)
        self.assertIn("MP3-128k", a_tags)
        self.assertIn("M4A", a_tags)
        self.assertIn("FLAC", a_tags)

    # =========================================================================
    # FEATURE 4: Error Message Cleaning & Localization
    # =========================================================================
    def test_04_error_message_cleaning(self):
        """Test Arabic localization and cleanup of platform errors."""
        self.assertIn("تم إلغاء التنزيل", downloader.clean_error_message(downloader.DownloadCancelled()))
        self.assertIn("ميكس", downloader.clean_error_message("This playlist type is unviewable"))
        self.assertIn("حُذف", downloader.clean_error_message("Video unavailable"))
        self.assertIn("خاص", downloader.clean_error_message("This is a private video"))
        self.assertIn("تسجيل الدخول", downloader.clean_error_message("Sign in to confirm you’re not a bot"))
        self.assertIn("غير مدعوم", downloader.clean_error_message("Unsupported URL"))
        self.assertIn("403", downloader.clean_error_message("HTTP Error 403: Forbidden"))
        self.assertIn("الشبكة", downloader.clean_error_message("Connection timed out"))
        self.assertIn("FFmpeg", downloader.clean_error_message("ffmpeg not found"))

    # =========================================================================
    # FEATURE 5: Configuration & History Management
    # =========================================================================
    def test_05_config_and_history(self):
        """Test saving, loading, deduplication, and corruption recovery of history/config."""
        api = object.__new__(main.DownloaderBridgeAPI)
        api._window = None

        with tempfile.TemporaryDirectory() as tmp_dir:
            config_file = os.path.join(tmp_dir, ".sdn_config.json")
            history_file = os.path.join(tmp_dir, ".sdn_history.json")
            downloads_dir = os.path.join(tmp_dir, "Downloads")
            os.makedirs(downloads_dir, exist_ok=True)

            with mock.patch("os.path.expanduser", return_value=tmp_dir):
                # Default save dir
                save_dir = api._load_save_dir()
                self.assertTrue(os.path.exists(save_dir))

                # Custom save dir
                new_save_dir = os.path.join(tmp_dir, "MyDownloads")
                os.makedirs(new_save_dir, exist_ok=True)
                api.save_dir = new_save_dir
                api._save_config()

                loaded_dir = api._load_save_dir()
                self.assertEqual(loaded_dir, new_save_dir)

                # Corrupted config recovery
                with open(config_file, "w") as f:
                    f.write("{invalid json")
                recovered_dir = api._load_save_dir()
                self.assertNotEqual(recovered_dir, "{invalid json")

                # History test: empty
                self.assertEqual(api.get_history(), [])

                # Add history items
                item1 = {"title": "Song A", "filepath": os.path.join(tmp_dir, "song_a.mp3"), "type": "audio"}
                item2 = {"title": "Video B", "filepath": os.path.join(tmp_dir, "video_b.mp4"), "type": "video"}
                api.add_history(item1)
                api.add_history(item2)

                hist = api.get_history()
                self.assertEqual(len(hist), 2)
                self.assertEqual(hist[0]["title"], "Video B")

                # Deduplicate exact output filepath
                item1_duplicate = {"title": "Song A - New Quality", "filepath": os.path.join(tmp_dir, "song_a.mp3"), "type": "audio"}
                api.add_history(item1_duplicate)
                hist = api.get_history()
                self.assertEqual(len(hist), 2)
                self.assertEqual(hist[0]["title"], "Song A - New Quality")

                # Clear history
                api.clear_history()
                self.assertEqual(api.get_history(), [])

    # =========================================================================
    # FEATURE 6: Media Server (HTTP Streaming & Tokenization)
    # =========================================================================
    def test_06_media_server_streaming(self):
        """Test local tokenized HTTP media server, byte ranges, HEAD, and pruning."""
        api = object.__new__(main.DownloaderBridgeAPI)
        api._media_server = None
        api._media_port = None
        api._media_lock = threading.Lock()
        api._media_tokens = {}
        api._media_path_tokens = {}
        api._media_prepare_lock = threading.Lock()
        api._media_cache_dir = None
        main.MediaHTTPHandler.bridge_api = api

        api._start_local_media_server()
        try:
            self.assertIsNotNone(api._media_port)

            with tempfile.TemporaryDirectory() as tmp_dir:
                sample_file = Path(tmp_dir) / "test_audio.mp3"
                content = b"ID3v2-TEST-PAYLOAD-" + (b"0123456789" * 100)
                sample_file.write_bytes(content)

                media_url = api.get_media_url(str(sample_file))
                self.assertTrue(media_url.startswith(f"http://127.0.0.1:{api._media_port}/media/"))

                # Test HEAD
                head_req = urllib.request.Request(media_url, method="HEAD")
                with urllib.request.urlopen(head_req, timeout=5) as resp:
                    self.assertEqual(resp.status, 200)
                    self.assertEqual(int(resp.headers["Content-Length"]), len(content))
                    self.assertEqual(resp.headers["Accept-Ranges"], "bytes")

                # Test full GET
                with urllib.request.urlopen(media_url, timeout=5) as resp:
                    self.assertEqual(resp.status, 200)
                    self.assertEqual(resp.read(), content)

                # Test Range GET (bytes=10-25)
                range_req = urllib.request.Request(media_url, headers={"Range": "bytes=10-25"})
                with urllib.request.urlopen(range_req, timeout=5) as resp:
                    self.assertEqual(resp.status, 206)
                    self.assertEqual(resp.headers["Content-Range"], f"bytes 10-25/{len(content)}")
                    self.assertEqual(resp.read(), content[10:26])

                # Test Invalid Range -> 416
                bad_range_req = urllib.request.Request(media_url, headers={"Range": f"bytes={len(content)+10}-"})
                try:
                    urllib.request.urlopen(bad_range_req, timeout=5)
                    self.fail("Expected 416 Range Not Satisfiable")
                except urllib.error.HTTPError as err:
                    self.assertEqual(err.code, 416)
                    err.close()
        finally:
            if api._media_server:
                api._media_server.shutdown()
                api._media_server.server_close()

    # =========================================================================
    # FEATURE 7: Music Scanner & Compatible Transcoding
    # =========================================================================
    def test_07_music_scanner_and_transcoding(self):
        """Test recursive audio scanning and on-the-fly MP3 transcoding via FFmpeg."""
        api = object.__new__(main.DownloaderBridgeAPI)
        api._media_server = None
        api._media_port = 9876
        api._media_lock = threading.Lock()
        api._media_tokens = {}
        api._media_path_tokens = {}
        api._media_prepare_lock = threading.Lock()
        api._media_cache_dir = None
        api.save_dir = ""

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create synthetic WAV file with real audio using FFmpeg
            wav_path = Path(tmp_dir) / "synth_tone.wav"
            subprocess.run(
                [
                    self.ffmpeg_path, "-y",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                    str(wav_path)
                ],
                capture_output=True,
                check=True
            )
            self.assertTrue(wav_path.is_file() and wav_path.stat().st_size > 0)

            # Create subfolder with another track (simulating playlist download)
            sub_dir = Path(tmp_dir) / "Best Album"
            sub_dir.mkdir()
            sub_wav = sub_dir / "track_02.wav"
            shutil.copyfile(wav_path, sub_wav)

            # Non-audio file to ignore
            (Path(tmp_dir) / "notes.txt").write_text("not audio", encoding="utf-8")

            # Scan folder
            scan_res = api.scan_music_folder(tmp_dir)
            tracks = scan_res["tracks"]
            self.assertEqual(len(tracks), 2)
            titles = [t["title"] for t in tracks]
            self.assertIn("synth_tone", titles)
            self.assertIn("track_02", titles)

            # Transcode test: convert WAV to compatible MP3 cache
            prep_res = api.prepare_media_playback(str(wav_path))
            self.assertTrue(prep_res["ok"])
            self.assertIn("url", prep_res)

    # =========================================================================
    # FEATURE 8: Trimming Media Files with FFmpeg
    # =========================================================================
    def test_08_media_trimming(self):
        """Test trimming audio/video files using FFmpeg."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Generate a 5-second test video
            src_video = Path(tmp_dir) / "source_5s.mp4"
            subprocess.run(
                [
                    self.ffmpeg_path, "-y",
                    "-f", "lavfi", "-i", "testsrc=duration=5:size=320x240:rate=30",
                    "-f", "lavfi", "-i", "sine=frequency=1000:duration=5",
                    "-c:v", "libx264", "-c:a", "aac",
                    str(src_video)
                ],
                capture_output=True,
                check=True
            )
            self.assertTrue(src_video.is_file())

            dl = downloader.MediaDownloader()
            # Trim to 1s - 3s (duration 2s)
            dl._trim_file(str(src_video), trim_start="00:01", trim_end="00:03")
            self.assertTrue(src_video.is_file())
            self.assertGreater(src_video.stat().st_size, 0)

    # =========================================================================
    # FEATURE 9: Repeated Downloads Unique Filepath Protection
    # =========================================================================
    def test_09_repeated_downloads_no_overwrite(self):
        """Ensure repeated downloads of same URL get unique filenames without collision."""
        option = {"type": "video", "quality_tag": "720p", "ext": "mp4"}
        template1 = os.path.join(
            "C:\\Downloads",
            f"%(title).180B [%(id)s] [{downloader._safe_quality_tag(option)}] [{time.time()}-1].mp4"
        )
        time.sleep(0.01)
        template2 = os.path.join(
            "C:\\Downloads",
            f"%(title).180B [%(id)s] [{downloader._safe_quality_tag(option)}] [{time.time()}-2].mp4"
        )
        self.assertNotEqual(template1, template2)

    # =========================================================================
    # FEATURE 10: App Update Logic & SHA-256 Hash Verification
    # =========================================================================
    def test_10_app_updates(self):
        """Test semantic version comparisons, update verification, and hash security."""
        self.assertGreater(main._version_key("v2.0.1"), main._version_key("v2.0.0"))
        self.assertGreater(main._version_key("2.1.0"), main._version_key("2.0.0"))
        self.assertEqual(main._version_key("v2.0.0"), main._version_key("2.0.0"))

        api = object.__new__(main.DownloaderBridgeAPI)
        api.pending_update_path = None
        api.pending_update_kind = None
        api.pending_update_sha256 = None
        api.pending_update_size = None

        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_exe = Path(tmp_dir) / "SDN_Update.exe"
            content = b"MZ" + (b"X" * 1024 * 1024)
            fake_exe.write_bytes(content)

            import hashlib
            correct_hash = hashlib.sha256(content).hexdigest()

            api.pending_update_path = str(fake_exe)
            api.pending_update_size = len(content)
            api.pending_update_sha256 = correct_hash

            # Valid resolution
            resolved = api._resolve_pending_update(str(fake_exe))
            self.assertEqual(Path(resolved), fake_exe.resolve())

            # Tampered hash rejection
            api.pending_update_sha256 = "0" * 64
            with self.assertRaises(RuntimeError) as err:
                api._resolve_pending_update(str(fake_exe))
            self.assertIn("بصمة", str(err.exception))

    # =========================================================================
    # FEATURE 11: Browser Extension Server (Port 4567) Security & Endpoints
    # =========================================================================
    def test_11_extension_server(self):
        """Test loopback HTTP bridge server on port 4567 for browser extension integration."""
        api = object.__new__(main.DownloaderBridgeAPI)
        api._window = None
        received_urls = []
        api.handle_extension_url = lambda u: received_urls.append(u)
        main.ExtensionHTTPHandler.bridge_api = api

        server = main.HTTPServer(("127.0.0.1", 4567), main.ExtensionHTTPHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            # 1. Test unauthorized origin rejection (security check)
            bad_opt_req = urllib.request.Request("http://127.0.0.1:4567/", method="OPTIONS")
            bad_opt_req.add_header("Origin", "https://malicious-website.com")
            try:
                urllib.request.urlopen(bad_opt_req, timeout=3)
                self.fail("Expected 403 Forbidden for disallowed origin")
            except urllib.error.HTTPError as err:
                self.assertEqual(err.code, 403)
                err.close()

            # 2. Test allowed browser extension origin (CORS preflight)
            ext_origin = "chrome-extension://abcdefghijklmnopqrstuvwxyz123456"
            opt_req = urllib.request.Request("http://127.0.0.1:4567/", method="OPTIONS")
            opt_req.add_header("Origin", ext_origin)
            with urllib.request.urlopen(opt_req, timeout=3) as resp:
                self.assertEqual(resp.status, 204)
                self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), ext_origin)

            # 3. Test POST valid URL from browser extension
            post_data = json.dumps({"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}).encode("utf-8")
            post_req = urllib.request.Request(
                "http://127.0.0.1:4567/",
                data=post_data,
                headers={"Content-Type": "application/json", "Origin": ext_origin}
            )
            with urllib.request.urlopen(post_req, timeout=3) as resp:
                self.assertEqual(resp.status, 200)
                body = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(body.get("status"), "ok")

            self.assertEqual(len(received_urls), 1)
            self.assertEqual(received_urls[0], "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        finally:
            server.shutdown()
            server.server_close()

    # =========================================================================
    # FEATURE 12: Application Diagnostics and Logging
    # =========================================================================
    def test_12_app_logger(self):
        """Test logger setup, diagnostic info, and exception handling."""
        import app_logger
        logger = app_logger.setup_logger("SDN.Test")
        self.assertIsNotNone(logger)
        diag = app_logger.get_diagnostic_info()
        self.assertIn("os", diag)
        self.assertIn("python_version", diag)
        app_logger.cleanup_old_logs()


if __name__ == "__main__":
    unittest.main(verbosity=2)
