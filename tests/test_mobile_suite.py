# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  SDN Downloader Ultra - Full Mobile Version Inspection & Test Suite     ║
║  Validates mobile web app, native bridge, UI features & compiled APK     ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from version import APP_VERSION

MOBILE_HTML = ROOT / "www" / "index.html"
MAIN_ACTIVITY = ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "sdn" / "downloader" / "ultra" / "MainActivity.java"
APK_PATH = ROOT / "dist" / "SDN_Downloader_Ultra.apk"


def read_mobile_html() -> str:
    return MOBILE_HTML.read_text(encoding="utf-8")


def read_main_activity() -> str:
    return MAIN_ACTIVITY.read_text(encoding="utf-8")


class TestMobileStructure(unittest.TestCase):
    """1. Mobile HTML5 & Responsive Mobile Viewport Structure"""

    @classmethod
    def setUpClass(cls):
        cls.html = read_mobile_html()

    def test_file_exists(self):
        self.assertTrue(MOBILE_HTML.is_file(), "www/index.html must exist as the standalone mobile app")

    def test_html5_doctype(self):
        self.assertTrue(self.html.strip().startswith("<!DOCTYPE html>"))

    def test_arabic_rtl(self):
        self.assertIn('lang="ar"', self.html)
        self.assertIn('dir="rtl"', self.html)

    def test_meta_charset(self):
        self.assertIn('charset="UTF-8"', self.html)

    def test_mobile_viewport_and_safe_area(self):
        self.assertIn('name="viewport"', self.html)
        self.assertIn('viewport-fit=cover', self.html)
        self.assertIn('user-scalable=no', self.html)

    def test_capacitor_tag(self):
        self.assertIn('<meta name="capacitor" content="true">', self.html)

    def test_mobile_title(self):
        self.assertIn("<title>SDN Ultra Mobile", self.html)

    def test_no_desktop_window_controls(self):
        """Mobile version must NOT have desktop window minimize/maximize/close controls"""
        self.assertNotIn('id="minBtn"', self.html)
        self.assertNotIn('id="maxBtn"', self.html)
        self.assertNotIn('id="closeBtn"', self.html)
        self.assertNotIn('window-titlebar', self.html)

    def test_mobile_navbar_and_tabs(self):
        self.assertIn('class="mobile-navbar"', self.html)
        self.assertIn('id="tabHome"', self.html)
        self.assertIn('id="tabDownloads"', self.html)
        self.assertIn('id="tabMusic"', self.html)
        self.assertIn('id="tabYouTube"', self.html)
        self.assertIn('id="tabSettings"', self.html)


class TestMobileBridgeContract(unittest.TestCase):
    """2. Complete Bridge Contract between Mobile Web and Android Java Native"""

    @classmethod
    def setUpClass(cls):
        cls.html = read_mobile_html()
        cls.java = read_main_activity()

    def test_bridge_name_match(self):
        self.assertIn('"androidInterface"', self.java)
        self.assertIn('window.androidInterface', self.html)

    def test_fetch_media_info_contract(self):
        self.assertIn('fetchMediaInfo', self.java)
        self.assertIn('fetchMediaInfoEx', self.java)
        self.assertIn('fetchMediaInfo', self.html)

    def test_download_media_contract(self):
        self.assertIn('downloadMedia', self.java)
        self.assertIn('window.androidInterface.downloadMedia', self.html)

    def test_cancel_download_contract(self):
        self.assertIn('cancelDownload', self.java)
        self.assertIn('window.androidInterface.cancelDownload', self.html)

    def test_saf_folder_picker_contract(self):
        self.assertIn('pickFolder', self.java)
        self.assertIn('window.androidInterface.pickFolder', self.html)

    def test_cookie_file_picker_contract(self):
        self.assertIn('pickCookieFile', self.java)
        self.assertIn('window.androidInterface.pickCookieFile', self.html)

    def test_audio_library_contract(self):
        self.assertIn('listAudioFiles', self.java)
        self.assertIn('window.androidInterface.listAudioFiles', self.html)

    def test_delete_file_contract(self):
        self.assertIn('deleteFile', self.java)
        self.assertIn('window.androidInterface.deleteFile', self.html)

    def test_youtube_integration_contract(self):
        self.assertIn('isYouTubeLoggedIn', self.java)
        self.assertIn('startYouTubeLogin', self.java)
        self.assertIn('logoutYouTube', self.java)
        self.assertIn('openYouTubeBrowser', self.java)
        self.assertIn('isYouTubeLoggedIn', self.html)
        self.assertIn('startYouTubeLogin', self.html)
        self.assertIn('logoutYouTube', self.html)
        self.assertIn('openYouTubeBrowser', self.html)

    def test_open_downloads_contract(self):
        self.assertIn('openDownloads', self.java)
        self.assertIn('window.androidInterface.openDownloads', self.html)

    def test_app_update_contract(self):
        self.assertIn('downloadUpdate', self.java)
        self.assertIn('window.androidInterface.downloadUpdate', self.html)

    def test_java_to_js_callbacks_implemented(self):
        """Ensure all callbacks invoked by MainActivity.java exist in www/index.html"""
        callbacks = [
            "onAndroidMediaInfo",
            "updateProgress",
            "onUpdateProgress",
            "handleSelectedFolder",
            "handleCookieFileSelected",
            "handleSharedUrl",
            "onYouTubeLoginComplete",
            "onBrowserQuickDownload",
            "onBrowserSendUrl",
        ]
        for cb in callbacks:
            with self.subTest(callback=cb):
                self.assertIn(f"window.{cb}", self.html, f"Callback window.{cb} must be defined in www/index.html")


class TestMobileFeaturesAndUI(unittest.TestCase):
    """3. Mobile App Features and UI Elements Completeness"""

    @classmethod
    def setUpClass(cls):
        cls.html = read_mobile_html()

    def test_version_sync(self):
        match = re.search(r"let CURRENT_VERSION\s*=\s*'([^']+)';", self.html)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), APP_VERSION)

    def test_url_input_elements(self):
        self.assertIn('id="urlInput"', self.html)
        self.assertIn('id="btnClearUrl"', self.html)
        self.assertIn('id="btnPasteUrl"', self.html)

    def test_format_quality_elements(self):
        self.assertIn('id="btnTypeVideo"', self.html)
        self.assertIn('id="btnTypeAudio"', self.html)
        self.assertIn('id="videoQualityGrid"', self.html)
        self.assertIn('id="audioQualityGrid"', self.html)
        self.assertIn('id="turboSwitch"', self.html)

    def test_download_progress_card(self):
        self.assertIn('id="progressCard"', self.html)
        self.assertIn('id="progressBarFill"', self.html)
        self.assertIn('id="progressPercentTxt"', self.html)
        self.assertIn('id="progressStatusMsg"', self.html)
        self.assertIn('id="btnCancelDownload"', self.html)

    def test_music_player_elements(self):
        self.assertIn('id="playerDiscArt"', self.html)
        self.assertIn('id="nowPlayingTitle"', self.html)
        self.assertIn('id="nowPlayingArtist"', self.html)
        self.assertIn('id="audioSeekRange"', self.html)
        self.assertIn('id="btnAudioPlayPause"', self.html)
        self.assertIn('id="nativeAudioPlayer"', self.html)

    def test_settings_elements(self):
        self.assertIn('id="currentSavePathTxt"', self.html)
        self.assertIn('id="cookieStatusTxt"', self.html)
        self.assertIn('id="appVersionTxt"', self.html)


class TestMobileApkPackage(unittest.TestCase):
    """4. Compiled Android APK Binary Integrity Check"""

    def test_apk_file_exists(self):
        self.assertTrue(APK_PATH.is_file(), f"APK file must exist at {APK_PATH}")
        self.assertGreater(APK_PATH.stat().st_size, 100 * 1024 * 1024, "APK must be over 100MB containing full ffmpeg and python")

    def test_apk_zip_integrity(self):
        with zipfile.ZipFile(APK_PATH, "r") as apk:
            bad_file = apk.testzip()
            self.assertIsNone(bad_file, f"Corrupted file inside APK: {bad_file}")

    def test_apk_manifest_and_dex(self):
        with zipfile.ZipFile(APK_PATH, "r") as apk:
            names = set(apk.namelist())
            self.assertIn("AndroidManifest.xml", names)
            self.assertTrue(any(n.startswith("classes") and n.endswith(".dex") for n in names))

    def test_apk_native_libraries(self):
        with zipfile.ZipFile(APK_PATH, "r") as apk:
            names = set(apk.namelist())
            self.assertIn("lib/arm64-v8a/libffmpeg.so", names)
            self.assertIn("lib/arm64-v8a/libffprobe.so", names)
            self.assertIn("lib/arm64-v8a/libpython.so", names)

    def test_apk_contains_standalone_mobile_ui(self):
        with zipfile.ZipFile(APK_PATH, "r") as apk:
            names = set(apk.namelist())
            self.assertIn("assets/public/index.html", names)
            content = apk.read("assets/public/index.html").decode("utf-8", errors="replace")
            self.assertIn("SDN Ultra Mobile", content)
            self.assertIn("androidInterface", content)
            self.assertNotIn("window-titlebar", content)


if __name__ == "__main__":
    unittest.main()
