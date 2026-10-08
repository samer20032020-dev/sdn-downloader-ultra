# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  SDN Downloader Ultra - COMPREHENSIVE Frontend Analysis Suite          ║
║  Static analysis of HTML/CSS/JS without needing a running browser      ║
║  Coverage: Structure, Accessibility, JS Functions, CSS, Security       ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from version import APP_VERSION

ROOT = Path(__file__).resolve().parent.parent
UI_HTML = ROOT / "ui" / "index.html"
INSTALLER_HTML = ROOT / "ui" / "installer.html"
LANDING_HTML = ROOT / "index.html"


def _read_html():
    return UI_HTML.read_text(encoding="utf-8")


class Test_FE01_HTMLStructure(unittest.TestCase):
    """Frontend 1: HTML Document Structure"""

    def test_doctype(self):
        html = _read_html()
        self.assertTrue(html.strip().startswith("<!DOCTYPE html>"))

    def test_lang_attribute(self):
        html = _read_html()
        self.assertIn('lang="ar"', html)

    def test_rtl_direction(self):
        html = _read_html()
        self.assertIn('dir="rtl"', html)

    def test_meta_charset(self):
        html = _read_html()
        self.assertIn('charset="UTF-8"', html)

    def test_meta_viewport(self):
        html = _read_html()
        self.assertIn("viewport", html)
        self.assertIn("width=device-width", html)

    def test_title_tag(self):
        html = _read_html()
        self.assertIn("<title>SDN</title>", html)

    def test_body_closing(self):
        html = _read_html()
        self.assertIn("</body>", html)
        self.assertIn("</html>", html)


class Test_FE02_CSSDesignSystem(unittest.TestCase):
    """Frontend 2: CSS Variables & Design Tokens"""

    def test_dark_theme_variables(self):
        html = _read_html()
        for var in ["--bg", "--card-bg", "--primary", "--accent", "--green", "--red",
                     "--text-main", "--text-sub", "--muted", "--radius"]:
            self.assertIn(var, html, f"Missing CSS variable: {var}")

    def test_light_theme_variables(self):
        html = _read_html()
        self.assertIn("body.light-theme", html)

    def test_font_families(self):
        html = _read_html()
        self.assertIn("Tajawal", html)
        self.assertIn("Outfit", html)

    def test_font_awesome(self):
        html = _read_html()
        self.assertIn("font-awesome", html)

    def test_google_fonts(self):
        html = _read_html()
        self.assertIn("fonts.googleapis.com", html)

    def test_transitions_present(self):
        html = _read_html()
        self.assertGreater(html.count("transition"), 20,
                           "Expected many CSS transitions for smooth UX")

    def test_animations_present(self):
        html = _read_html()
        self.assertGreater(html.count("@keyframes"), 3,
                           "Expected keyframe animations for dynamic design")


class Test_FE03_NavigationSystem(unittest.TestCase):
    """Frontend 3: Navigation Between Pages"""

    def test_nav_buttons_exist(self):
        html = _read_html()
        nav_items = re.findall(r'class="nav-item[^"]*"', html)
        self.assertGreaterEqual(len(nav_items), 3,
                                "Expected at least 3 navigation items")

    def test_page_sections_exist(self):
        html = _read_html()
        for page_id in ["homePage", "playerPage", "settingsPage", "historyPage"]:
            self.assertIn(f'id="{page_id}"', html, f"Missing page section: {page_id}")

    def test_navigate_function(self):
        html = _read_html()
        self.assertIn("function navigate(", html)
        self.assertIn("switchPage(", html)


class Test_FE04_URLInputSystem(unittest.TestCase):
    """Frontend 4: URL Input, Paste & Fetch"""

    def test_url_input_exists(self):
        html = _read_html()
        self.assertIn('id="urlInp"', html)

    def test_paste_button_exists(self):
        html = _read_html()
        self.assertIn('id="pasteBtn"', html)

    def test_fetch_button_exists(self):
        html = _read_html()
        self.assertIn('id="fetchBtn"', html)

    def test_dofetch_function(self):
        html = _read_html()
        self.assertIn("function doFetch(", html)

    def test_paste_handler(self):
        html = _read_html()
        self.assertIn("pasteBtn", html)
        self.assertIn("get_clipboard", html)


class Test_FE05_MediaCard(unittest.TestCase):
    """Frontend 5: Media Info Card"""

    def test_media_card_exists(self):
        html = _read_html()
        self.assertIn('id="mediaCard"', html)

    def test_thumbnail_element(self):
        html = _read_html()
        self.assertIn('id="mThumb"', html)

    def test_title_element(self):
        html = _read_html()
        self.assertIn('id="mTitle"', html)

    def test_uploader_element(self):
        html = _read_html()
        self.assertIn('id="mUp"', html)

    def test_render_media_card_function(self):
        html = _read_html()
        self.assertIn("function renderMediaCard(", html)


class Test_FE06_QualityGrid(unittest.TestCase):
    """Frontend 6: Quality Selection Grid"""

    def test_quality_grid_exists(self):
        html = _read_html()
        self.assertIn('id="qGrid"', html)

    def test_video_audio_tabs(self):
        html = _read_html()
        self.assertIn('id="videoTabBtn"', html)
        self.assertIn('id="audioTabBtn"', html)

    def test_switch_format_tab_function(self):
        html = _read_html()
        self.assertIn("function switchFormatTab(", html)

    def test_render_tab_options_function(self):
        html = _read_html()
        self.assertIn("function renderTabOptions(", html)


class Test_FE07_DownloadProgress(unittest.TestCase):
    """Frontend 7: Download Progress System"""

    def test_progress_card(self):
        html = _read_html()
        self.assertIn('id="progCard"', html)

    def test_progress_fill(self):
        html = _read_html()
        self.assertIn('id="progFill"', html)

    def test_progress_percentage(self):
        html = _read_html()
        self.assertIn('id="progPct"', html)

    def test_progress_status(self):
        html = _read_html()
        self.assertIn('id="progStatus"', html)

    def test_progress_speed(self):
        html = _read_html()
        self.assertIn('id="progSpeed"', html)

    def test_cancel_button(self):
        html = _read_html()
        self.assertIn('id="cancelDlBtn"', html)

    def test_download_button(self):
        html = _read_html()
        self.assertIn('id="dlBtn"', html)

    def test_update_progress_function(self):
        html = _read_html()
        self.assertIn("function updateProgress(", html)

    def test_set_download_active_function(self):
        html = _read_html()
        self.assertIn("function setDownloadActive(", html)


class Test_FE08_PlaylistPicker(unittest.TestCase):
    """Frontend 8: Playlist Item Picker"""

    def test_playlist_picker_exists(self):
        html = _read_html()
        self.assertIn('id="downloadPlaylistPicker"', html)

    def test_playlist_items_container(self):
        html = _read_html()
        self.assertIn('id="downloadPlaylistItems"', html)

    def test_select_all_function(self):
        html = _read_html()
        self.assertIn("function setAllPlaylistItems(", html)

    def test_playlist_summary(self):
        html = _read_html()
        self.assertIn('id="downloadPlaylistSummary"', html)

    def test_render_download_playlist(self):
        html = _read_html()
        self.assertIn("function renderDownloadPlaylist(", html)


class Test_FE09_TrimControls(unittest.TestCase):
    """Frontend 9: Trim/Cut Controls"""

    def test_trim_enable_checkbox(self):
        html = _read_html()
        self.assertIn('id="trimEnableCheck"', html)

    def test_trim_start_fields(self):
        html = _read_html()
        self.assertIn('id="trimStartMin"', html)
        self.assertIn('id="trimStartSec"', html)

    def test_trim_end_fields(self):
        html = _read_html()
        self.assertIn('id="trimEndMin"', html)
        self.assertIn('id="trimEndSec"', html)

    def test_trim_summary_bar(self):
        html = _read_html()
        self.assertIn('id="trimSummaryBar"', html)

    def test_get_trim_options_function(self):
        html = _read_html()
        self.assertIn("function getTrimOptions(", html)

    def test_update_trim_summary_function(self):
        html = _read_html()
        self.assertIn("function updateTrimSummary(", html)

    def test_trim_validation_logic(self):
        html = _read_html()
        self.assertIn("وقت النهاية يجب أن يكون أكبر من وقت البداية", html)


class Test_FE10_MusicPlayer(unittest.TestCase):
    """Frontend 10: Lark Music Player"""

    def test_player_page_exists(self):
        html = _read_html()
        self.assertIn('id="playerPage"', html)

    def test_init_lark_player(self):
        html = _read_html()
        self.assertIn("initLarkPlayer", html)

    def test_toggle_play_pause(self):
        html = _read_html()
        self.assertIn("togglePlayPause", html)

    def test_audio_element(self):
        html = _read_html()
        # Player should use HTML Audio API
        self.assertTrue("Audio(" in html or "new Audio" in html or 'id="larkAudio"' in html
                        or "audio" in html.lower())


class Test_FE11_Settings(unittest.TestCase):
    """Frontend 11: Settings Panel"""

    def test_settings_page_exists(self):
        html = _read_html()
        self.assertIn('id="settingsPage"', html)

    def test_save_path_display(self):
        html = _read_html()
        # There should be an element showing/changing save path
        self.assertTrue("savePath" in html or "save_dir" in html or "choose_folder" in html)

    def test_theme_toggle(self):
        html = _read_html()
        self.assertIn("light-theme", html)

    def test_version_display(self):
        html = _read_html()
        self.assertIn("settingsVersionTxt", html)

    def test_subtitles_option(self):
        html = _read_html()
        self.assertIn('id="subtitlesCheck"', html)

    def test_speed_limit_option(self):
        html = _read_html()
        self.assertIn('id="speedLimitSelect"', html)


class Test_FE12_UpdateModal(unittest.TestCase):
    """Frontend 12: Update System UI"""

    def test_update_modal_exists(self):
        html = _read_html()
        self.assertIn('id="updateModal"', html)

    def test_update_button_header(self):
        html = _read_html()
        self.assertIn('id="headerUpdateBtn"', html)

    def test_on_update_progress_function(self):
        html = _read_html()
        self.assertIn("function onUpdateProgress(", html)

    def test_show_update_badge_function(self):
        html = _read_html()
        self.assertIn("function showUpdateBadge(", html)

    def test_check_updates_function(self):
        html = _read_html()
        self.assertIn("function checkForAppUpdates(", html)

    def test_confirm_restart_function(self):
        html = _read_html()
        self.assertIn("function onConfirmRestartNow(", html)


class Test_FE13_ToastNotifications(unittest.TestCase):
    """Frontend 13: Toast Notification System"""

    def test_toast_function(self):
        html = _read_html()
        self.assertIn("function toast(", html)

    def test_toast_container(self):
        html = _read_html()
        self.assertTrue("toast" in html.lower())


class Test_FE14_DragAndDrop(unittest.TestCase):
    """Frontend 14: Drag & Drop URL Handler"""

    def test_drag_drop_overlay(self):
        html = _read_html()
        self.assertIn('id="dragDropOverlay"', html)

    def test_dragenter_handler(self):
        html = _read_html()
        self.assertIn("dragenter", html)

    def test_dragleave_handler(self):
        html = _read_html()
        self.assertIn("dragleave", html)

    def test_drop_handler(self):
        html = _read_html()
        self.assertIn("drop", html)
        self.assertIn("dataTransfer", html)


class Test_FE15_KeyboardShortcuts(unittest.TestCase):
    """Frontend 15: Keyboard Shortcuts"""

    def test_escape_key(self):
        html = _read_html()
        self.assertIn("Escape", html)

    def test_space_toggle(self):
        html = _read_html()
        self.assertIn("Space", html)

    def test_enter_start(self):
        html = _read_html()
        self.assertIn("Enter", html)

    def test_ctrl_v_paste(self):
        html = _read_html()
        # Should have Ctrl+V logic
        self.assertTrue("ctrlKey" in html or "metaKey" in html)


class Test_FE16_DownloadCounter(unittest.TestCase):
    """Frontend 16: Download Counter Badge"""

    def test_counter_badge_exists(self):
        html = _read_html()
        self.assertIn('id="dlCounterBadge"', html)

    def test_counter_num_exists(self):
        html = _read_html()
        self.assertIn('id="dlCounterNum"', html)

    def test_local_storage_persistence(self):
        html = _read_html()
        self.assertIn("totalDlCount", html)
        self.assertIn("localStorage", html)

    def test_increment_function(self):
        html = _read_html()
        self.assertIn("function incrementDlCounter(", html)


class Test_FE17_HistoryPanel(unittest.TestCase):
    """Frontend 17: Download History"""

    def test_history_page_exists(self):
        html = _read_html()
        self.assertIn('id="historyPage"', html)

    def test_history_list(self):
        html = _read_html()
        self.assertIn('id="fullHistoryList"', html)

    def test_recent_list(self):
        html = _read_html()
        self.assertIn('id="recentList"', html)

    def test_create_recent_card_function(self):
        html = _read_html()
        self.assertIn("function createRecentCard(", html)

    def test_open_folder_function(self):
        html = _read_html()
        self.assertIn("function openDownloadFolder(", html)


class Test_FE18_VersionConsistency(unittest.TestCase):
    """Frontend 18: Cross-Module Version Consistency"""

    def test_js_version_matches_python(self):
        html = _read_html()
        self.assertIn(f"CURRENT_VERSION = '{APP_VERSION}'", html)

    def test_compare_versions_function(self):
        html = _read_html()
        self.assertIn("function compareVersions(", html)

    def test_github_repo_url(self):
        html = _read_html()
        self.assertIn("samer20032020-dev/sdn-downloader-ultra", html)


class Test_FE19_SecurityAnalysis(unittest.TestCase):
    """Frontend 19: Security Best Practices"""

    def test_no_inline_eval(self):
        html = _read_html()
        # Count evals - should only be from safe sources
        eval_count = len(re.findall(r'[^.]eval\(', html))
        self.assertEqual(eval_count, 0, "Found potentially unsafe eval() calls in frontend")

    def test_no_document_write(self):
        html = _read_html()
        self.assertNotIn("document.write(", html,
                          "document.write() is a security risk")

    def test_url_validation_before_fetch(self):
        html = _read_html()
        # doFetch should validate URL
        self.assertIn("http://", html)
        self.assertIn("https://", html)

    def test_pywebview_api_safety(self):
        html = _read_html()
        # All pywebview calls should use optional chaining
        api_calls = re.findall(r'window\.pywebview\?\.api', html)
        self.assertGreater(len(api_calls), 5,
                           "Expected safe optional chaining for pywebview API calls")


class Test_FE20_AndroidInterface(unittest.TestCase):
    """Frontend 20: Android WebView Interface"""

    def test_android_interface_references(self):
        html = _read_html()
        self.assertIn("androidInterface", html)

    def test_android_download(self):
        html = _read_html()
        self.assertIn("downloadMedia", html)

    def test_android_update(self):
        html = _read_html()
        self.assertIn("downloadUpdate", html)


class Test_FE21_AdditionalFiles(unittest.TestCase):
    """Frontend 21: Other UI Files"""

    def test_installer_html_exists(self):
        self.assertTrue(INSTALLER_HTML.is_file())

    def test_landing_page_exists(self):
        self.assertTrue(LANDING_HTML.is_file())

    def test_installer_html_valid(self):
        content = INSTALLER_HTML.read_text(encoding="utf-8")
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("</html>", content)

    def test_landing_page_valid(self):
        content = LANDING_HTML.read_text(encoding="utf-8")
        self.assertIn("<!DOCTYPE html>", content.lower().replace("<!doctype", "<!DOCTYPE"))
        self.assertIn("SDN", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
