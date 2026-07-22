import sys
import os
import multiprocessing

if __name__ == '__main__':
    multiprocessing.freeze_support()

import threading
import webview
import webview.util
import json
import subprocess
import urllib.parse
import ctypes
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SDN.Downloader.Ultra.App.2.0")
except Exception:
    pass

# إصلاح مشكلة البحث عن ملفات win-arm64 / WebView2 عند تجميع البرنامج بواسطة PyInstaller
try:
    _orig_interop_dll_path = webview.util.interop_dll_path
    def _safe_interop_dll_path(dll_name: str) -> str:
        try:
            return _orig_interop_dll_path(dll_name)
        except Exception:
            if hasattr(sys, '_MEIPASS'):
                base = sys._MEIPASS
                candidate = os.path.join(base, dll_name)
                if os.path.exists(candidate):
                    return candidate
                candidate_runtime = os.path.join(base, 'webview', 'lib', 'runtimes', dll_name, 'native')
                if os.path.exists(candidate_runtime):
                    return candidate_runtime
            if dll_name in ('win-arm64', 'win-x64', 'win-x86'):
                return sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
            raise
    webview.util.interop_dll_path = _safe_interop_dll_path
except Exception:
    pass


def get_clipboard_text():
    """
    تسترجع النص المخزن في الحافظة بشكل آمن 100% وبدون أي انهيار للنظام
    """
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.GetClipboardData.restype = ctypes.c_void_p
        user32.OpenClipboard.argtypes = [ctypes.c_void_p]
        user32.CloseClipboard.argtypes = []

        if user32.OpenClipboard(None):
            try:
                handle = user32.GetClipboardData(13) # CF_UNICODETEXT
                if handle:
                    val = ctypes.c_wchar_p(handle).value
                    if val and isinstance(val, str):
                        return val.strip()
            finally:
                user32.CloseClipboard()
    except Exception:
        pass
    return ""

class ExtensionHTTPHandler(BaseHTTPRequestHandler):
    bridge_api = None

    def log_message(self, format, *args):
        pass # Disable console log noise

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        try:
            payload = json.loads(post_data.decode('utf-8'))
            url = payload.get('url')
            if url and ExtensionHTTPHandler.bridge_api:
                ExtensionHTTPHandler.bridge_api.handle_extension_url(url)
                self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({'status': 'error', 'msg': 'No URL provided'}).encode('utf-8'))
        except Exception as e:
            self.wfile.write(json.dumps({'status': 'error', 'msg': str(e)}).encode('utf-8'))

CURRENT_APP_VERSION = "2.2.0"
GITHUB_REPO = "samer20032020-dev/sdn-downloader-ultra"

class DownloaderBridgeAPI:
    def __init__(self):
        self._window = None
        self.save_dir = self._load_save_dir()
        self.downloader = None
        self.latest_update_info = None
        ExtensionHTTPHandler.bridge_api = self
        self._start_local_extension_server()
        self._trigger_bg_auto_updates()
        self._start_auto_cache_cleaner()

    def _start_auto_cache_cleaner(self):
        def _clean_job():
            import time
            import glob
            import shutil
            import tempfile

            while True:
                try:
                    # 1. Clean temporary files (.tmp, .part, SDN_Update_*.exe) in %temp%
                    temp_dir = tempfile.gettempdir()
                    now = time.time()
                    for pattern in ('SDN_Update_*.exe', '*.ytdl', '*.part', '*.tmp'):
                        for f_path in glob.glob(os.path.join(temp_dir, pattern)):
                            try:
                                if os.path.exists(f_path) and (now - os.path.getmtime(f_path)) > 14400:
                                    os.remove(f_path)
                            except Exception:
                                pass

                    # 2. Clean yt-dlp cache folder
                    yt_cache_dirs = [
                        os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'yt-dlp', 'cache'),
                        os.path.join(os.path.expanduser('~'), '.cache', 'yt-dlp')
                    ]
                    for yt_c in yt_cache_dirs:
                        if os.path.exists(yt_c):
                            try:
                                shutil.rmtree(yt_c, ignore_errors=True)
                            except Exception:
                                pass

                    # 3. Clean Webview cache if present
                    web_cache = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Programs', 'SDN Downloader Ultra', 'EBWebView', 'Default', 'Cache')
                    if os.path.exists(web_cache):
                        try:
                            shutil.rmtree(web_cache, ignore_errors=True)
                        except Exception:
                            pass
                except Exception:
                    pass

                # Repeat every 12 hours (43200 seconds)
                time.sleep(43200)

        threading.Thread(target=_clean_job, daemon=True).start()

    def _trigger_bg_auto_updates(self):
        def _update_job():
            try:
                import time
                time.sleep(2)
                from downloader import auto_update_ytdlp
                auto_update_ytdlp()

                # Check app updates from GitHub
                up_info = self.check_app_update()
                if up_info and up_info.get('has_update'):
                    self.latest_update_info = up_info
                    if self._window:
                        self._window.evaluate_js(f"if (typeof showUpdateBadge === 'function') showUpdateBadge({json.dumps(up_info)});")
            except Exception:
                pass
        threading.Thread(target=_update_job, daemon=True).start()

    def _start_local_extension_server(self):
        def _run_server():
            try:
                HTTPServer.allow_reuse_address = True
                server = HTTPServer(('127.0.0.1', 4567), ExtensionHTTPHandler)
                server.serve_forever()
            except Exception:
                pass
        threading.Thread(target=_run_server, daemon=True).start()

    def handle_extension_url(self, url):
        if self._window:
            js_code = f"if (typeof handleExtensionInput === 'function') handleExtensionInput({json.dumps(url)});"
            self._window.evaluate_js(js_code)

    def _load_save_dir(self):
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    dir_path = data.get("save_dir")
                    if dir_path and os.path.isdir(dir_path):
                        return dir_path
        except Exception:
            pass
        return os.path.join(os.path.expanduser("~"), "Downloads")

    def _save_config(self):
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({"save_dir": self.save_dir}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_history(self):
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_history.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def add_history(self, item):
        history = self.get_history()
        history.insert(0, item)
        history = history[:50]
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_history.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def clear_history(self):
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_history.json")
        try:
            if os.path.exists(config_path):
                os.remove(config_path)
            return True
        except Exception:
            return False

    def set_window(self, window):
        self._window = window

    def get_save_dir(self):
        return self.save_dir

    def open_folder(self, path=None):
        target = path or self.save_dir
        try:
            if os.path.exists(target):
                if sys.platform == 'win32':
                    os.startfile(target)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', target])
                else:
                    subprocess.Popen(['xdg-open', target])
        except Exception:
            pass

    def locate_file(self, filepath):
        """
        تفتح Windows Explorer وتقوم بتظليل/تحديد الملف المحدد فوراً
        """
        try:
            if not filepath:
                return self.open_folder()

            norm_path = os.path.normpath(filepath)
            if os.path.exists(norm_path):
                if sys.platform == 'win32':
                    subprocess.Popen(['explorer.exe', '/select,', norm_path])
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', '-R', norm_path])
                else:
                    self.open_folder(os.path.dirname(norm_path))
            else:
                self.open_folder(os.path.dirname(norm_path) if os.path.dirname(norm_path) else None)
        except Exception:
            self.open_folder()

    def choose_folder(self):
        if self._window:
            result = self._window.create_file_dialog(webview.FOLDER_DIALOG, directory=self.save_dir)
            if result and len(result) > 0:
                self.save_dir = result[0]
                self._save_config()
                return self.save_dir
        return self.save_dir

    def choose_cookie_file(self):
        if self._window:
            file_types = ('Cookie Files (*.txt)', 'All files (*.*)')
            result = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
            if result and len(result) > 0:
                return result[0]
        return ""

    def get_clipboard(self):
        return get_clipboard_text()

    def validate_link(self, url, proxy=None):
        try:
            from downloader import validate_link
            return validate_link(url, proxy=proxy)
        except Exception as e:
            return {'valid': False, 'reason': str(e)}

    def fetch_info(self, url, browser_cookies='none', proxy=None):
        try:
            if not self.downloader:
                from downloader import MediaDownloader
                self.downloader = MediaDownloader()
            
            info = self.downloader.fetch_info(url, browser_cookies=browser_cookies, proxy=proxy)
            return {'data': info, 'error': None}
        except Exception as e:
            return {'data': None, 'error': str(e)}

    def start_download(self, url, option, browser_cookies='none'):
        threading.Thread(
            target=self._async_download,
            args=(url, option, browser_cookies),
            daemon=True
        ).start()

    def _async_download(self, url, option, browser_cookies):
        def progress_callback(p_data):
            if self._window:
                self._window.evaluate_js(f'updateProgress({json.dumps(p_data)})')

        def status_callback(msg):
            if self._window:
                payload = {'status': 'processing', 'msg': msg}
                self._window.evaluate_js(f'updateProgress({json.dumps(payload)})')

        try:
            if not self.downloader:
                from downloader import MediaDownloader
                self.downloader = MediaDownloader()

            saved_filepath = self.downloader.download(
                url,
                option,
                self.save_dir,
                progress_callback=progress_callback,
                status_callback=status_callback,
                browser_cookies=browser_cookies
            )
            if self._window:
                payload = {'status': 'complete', 'filepath': saved_filepath}
                self._window.evaluate_js(f'updateProgress({json.dumps(payload)})')
        except Exception as e:
            if self._window:
                payload = {'status': 'error', 'error': str(e)}
                self._window.evaluate_js(f'updateProgress({json.dumps(payload)})')

    def resize_window(self, width, height):
        if self._window:
            try:
                self._window.resize(int(width), int(height))
            except Exception:
                pass

    def check_app_update(self):
        try:
            import urllib.request
            req = urllib.request.Request(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                headers={'User-Agent': 'SDN-Downloader-App'}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                tag_name = data.get('tag_name', '').lstrip('v')
                body = data.get('body', '')
                assets = data.get('assets', [])
                exe_download_url = None
                release_html_url = data.get('html_url', f"https://github.com/{GITHUB_REPO}/releases/latest")

                for asset in assets:
                    if asset.get('name', '').endswith('.exe'):
                        exe_download_url = asset.get('browser_download_url')
                        break

                if tag_name and tag_name != CURRENT_APP_VERSION:
                    return {
                        'has_update': True,
                        'latest_version': tag_name,
                        'current_version': CURRENT_APP_VERSION,
                        'download_url': exe_download_url or release_html_url,
                        'html_url': release_html_url,
                        'notes': body or 'تحديث جديد لتحسين الأداء وحل المشاكل.'
                    }
        except Exception:
            pass
        return {'has_update': False, 'current_version': CURRENT_APP_VERSION}

    def apply_app_update(self, download_url=None):
        import webbrowser
        if not download_url and self.latest_update_info:
            download_url = self.latest_update_info.get('download_url')

        if not download_url:
            download_url = f"https://github.com/{GITHUB_REPO}/releases/latest"

        # If it's a webpage URL, open in default browser
        if not download_url.endswith('.exe'):
            try:
                webbrowser.open(download_url)
                return {'success': True, 'msg': 'تم فتح صفحة التحديث في المتصفح'}
            except Exception:
                pass

        def _do_update():
            try:
                import urllib.request
                import tempfile
                import subprocess
                import time

                if self._window:
                    payload = {'status': 'processing', 'msg': 'جاري تنزيل التحديث الجديد (SDN_Downloader_Setup.exe)... ⬇️'}
                    self._window.evaluate_js(f'updateProgress({json.dumps(payload)})')

                temp_dir = tempfile.gettempdir()
                setup_filename = f"SDN_Update_{int(time.time())}.exe"
                setup_path = os.path.join(temp_dir, setup_filename)

                # Custom User-Agent header for GitHub releases download
                req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as resp, open(setup_path, 'wb') as out_f:
                    out_f.write(resp.read())

                if self._window:
                    payload = {'status': 'processing', 'msg': 'تم التحميل! جاري فتح تثبيت التحديث... 🚀'}
                    self._window.evaluate_js(f'updateProgress({json.dumps(payload)})')

                time.sleep(0.5)
                # Launch setup installer
                subprocess.Popen([setup_path])
                time.sleep(0.5)
                os._exit(0)
            except Exception as e:
                # Fallback: open browser release page if download failed
                webbrowser.open(download_url)
                if self._window:
                    payload = {'status': 'error', 'error': f'تم فتح صفحة التحديث في المتصفح ({str(e)})'}
                    self._window.evaluate_js(f'updateProgress({json.dumps(payload)})')

        threading.Thread(target=_do_update, daemon=True).start()
        return {'success': True}

def main():
    api = DownloaderBridgeAPI()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(base_dir, 'ui', 'index.html')

    window = webview.create_window(
        title='SDN Downloader ⚡ Ultra Edition',
        url=html_file,
        width=820,
        height=640,
        resizable=True,
        background_color='#07090e',
        js_api=api
    )
    api.set_window(window)
    webview.start(debug=False)

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
