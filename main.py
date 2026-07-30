import sys
import os
import multiprocessing

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
import threading
import webview
import webview.util
import json
import subprocess
import urllib.parse
import ctypes
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============================================================
# ULTRA LOGGING & DIAGNOSTICS
# ============================================================
try:
    from app_logger import setup_logger, log_exception, get_diagnostic_info, cleanup_old_logs
except ImportError:
    # Fallback: simple logger if module not found (bare setup)
    import logging as _logging
    def setup_logger(name="SDN"): 
        _logging.basicConfig(level=_logging.DEBUG)
        return _logging.getLogger(name)
    def log_exception(logger, msg="Error"): logger.exception(msg)
    def get_diagnostic_info(): return {}
    def cleanup_old_logs(): pass

_log = setup_logger("SDN.Main")
_log.info("═" * 60)
_log.info("SDN v0.3.0 - STARTING")
_log.info("═" * 60)

# ============================================================
# ULTRA PERFORMANCE: Windows API optimizations
# ============================================================
try:
    # Set process priority to HIGH for ultra responsiveness
    _PROCESS_HIGH_PRIORITY_CLASS = 0x00000080
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), _PROCESS_HIGH_PRIORITY_CLASS)
    _log.info("Process priority set to HIGH")
except Exception as e:
    _log.warning(f"Could not set process priority: {e}")

try:
    # Set AppUserModelID for Windows taskbar grouping
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SDN.App.0.1")
except Exception as e:
    _log.debug(f"AppUserModelID not set: {e}")

# ============================================================
# THREAD POOL for parallel operations (Ultra Speed)
# ============================================================
from concurrent.futures import ThreadPoolExecutor, as_completed
_THREAD_POOL = ThreadPoolExecutor(max_workers=min(8, (os.cpu_count() or 4) * 2), thread_name_prefix="SDN-Worker")
_log.info(f"Thread pool initialized with {_THREAD_POOL._max_workers} workers")

# ============================================================
# إصلاح مشكلة البحث عن ملفات win-arm64 / WebView2
# ============================================================
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
    _log.debug("WebView2 DLL path hook installed")
except Exception as e:
    _log.warning(f"WebView2 DLL hook not installed: {e}")

# ============================================================
# ULTRA PERFORMANCE: Pre-cache heavy imports in background
# ============================================================
_preload_done = threading.Event()

def _preload_heavy_modules():
    """Pre-load yt-dlp and other heavy modules in background thread for instant first-use"""
    modules_to_preload = [
        ('downloader', ['MediaDownloader', 'validate_link', 'clean_error_message', 'auto_update_ytdlp']),
        ('yt_dlp', []),
        ('urllib.request', []),
        ('json', []),
    ]
    for mod_name, _ in modules_to_preload:
        try:
            __import__(mod_name)
            _log.debug(f"Pre-loaded: {mod_name}")
        except Exception as e:
            _log.debug(f"Pre-load skipped {mod_name}: {e}")
    _preload_done.set()
    _log.info("Module pre-loading complete")

threading.Thread(target=_preload_heavy_modules, daemon=True, name="Preloader").start()


def get_clipboard_text():
    """
    تسترجع النص المخزن في الحافظة بشكل آمن 100% وبدون أي انهيار للنظام
    Ultra: faster direct Win32 API call with single-try optimization
    """
    try:
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
    except Exception as e:
        _log.debug(f"Clipboard read failed: {e}")
    return ""


class ExtensionHTTPHandler(BaseHTTPRequestHandler):
    """Ultra-lightweight HTTP handler for browser extension integration"""
    bridge_api = None

    def log_message(self, format, *args):
        pass  # Suppress HTTP access log noise

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
            _log.debug(f"Extension handler error: {e}")

CURRENT_APP_VERSION = "0.6.0"
GITHUB_REPO = "samer20032020-dev/sdn-downloader-ultra"

class DownloaderBridgeAPI:
    """ULTRA Bridge API - Interface between Python backend and WebView frontend"""
    
    def __init__(self):
        self._window = None
        self.save_dir = self._load_save_dir()
        self.downloader = None
        self.latest_update_info = None
        self._startup_time = time.time()
        self._installer_launched = False
        
        ExtensionHTTPHandler.bridge_api = self
        
        _log.info(f"Bridge API initialized. Save dir: {self.save_dir}")
        
        # Start all background services
        self._start_local_extension_server()
        self._trigger_bg_auto_updates()
        self._start_auto_cache_cleaner()
        
        # Diagnostic dump on first run
        try:
            diag = get_diagnostic_info()
            _log.info(f"System diagnostic: {json.dumps(diag, ensure_ascii=False)}")
        except Exception:
            pass

    # ================================================================
    # ULTRA: Auto Cache Cleaner with smart scheduling
    # ================================================================
    def _start_auto_cache_cleaner(self):
        def _clean_job():
            import glob
            import shutil
            import tempfile

            # First clean after 60s, then every 12h
            time.sleep(60)
            
            while True:
                try:
                    cleaned_count = 0
                    temp_dir = tempfile.gettempdir()
                    now = time.time()
                    
                    # Clean temp files older than 4 hours
                    for pattern in ('SDN_Update_*.exe', '*.ytdl', '*.part', '*.tmp'):
                        for f_path in glob.glob(os.path.join(temp_dir, pattern)):
                            try:
                                if os.path.exists(f_path) and (now - os.path.getmtime(f_path)) > 14400:
                                    os.remove(f_path)
                                    cleaned_count += 1
                            except Exception:
                                pass

                    # Clean yt-dlp cache
                    yt_cache_dirs = [
                        os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'yt-dlp', 'cache'),
                        os.path.join(os.path.expanduser('~'), '.cache', 'yt-dlp')
                    ]
                    for yt_c in yt_cache_dirs:
                        if os.path.exists(yt_c):
                            try:
                                shutil.rmtree(yt_c, ignore_errors=True)
                                cleaned_count += 1
                            except Exception:
                                pass

                    # Clean old logs
                    cleanup_old_logs()
                    
                    if cleaned_count > 0:
                        _log.info(f"Cache cleaner: removed {cleaned_count} items")

                except Exception as e:
                    _log.debug(f"Cache cleaner minor issue: {e}")

                time.sleep(43200)  # 12 hours

        threading.Thread(target=_clean_job, daemon=True, name="CacheCleaner").start()

    # ================================================================
    # ULTRA: Background auto-update checker with smart dedup
    # ================================================================
    def _trigger_bg_auto_updates(self):
        def _update_job():
            time.sleep(3)  # Let UI settle
            try:
                from downloader import auto_update_ytdlp
                auto_update_ytdlp()
                _log.info("yt-dlp auto-update check completed")
            except Exception as e:
                _log.warning(f"yt-dlp auto-update failed: {e}")

            try:
                up_info = self.check_app_update()
                if up_info and up_info.get('has_update'):
                    self.latest_update_info = up_info
                    if self._window:
                        self._window.evaluate_js(
                            f"if (typeof showUpdateBadge === 'function') showUpdateBadge({json.dumps(up_info)});"
                        )
                    _log.info(f"Update available: v{up_info.get('latest_version')} (current: v{CURRENT_APP_VERSION})")
                else:
                    _log.debug("App is up to date")
            except Exception as e:
                _log.warning(f"App update check failed: {e}")

        threading.Thread(target=_update_job, daemon=True, name="UpdateChecker").start()

    # ================================================================
    # Local extension bridge server
    # ================================================================
    def _start_local_extension_server(self):
        def _run_server():
            try:
                HTTPServer.allow_reuse_address = True
                server = HTTPServer(('127.0.0.1', 4567), ExtensionHTTPHandler)
                _log.info("Extension bridge server started on port 4567")
                server.serve_forever()
            except OSError as e:
                _log.warning(f"Extension server port 4567 in use: {e}")
            except Exception as e:
                _log.error(f"Extension server failed: {e}")

        threading.Thread(target=_run_server, daemon=True, name="ExtServer").start()

    def handle_extension_url(self, url):
        if self._window:
            js_code = f"if (typeof handleExtensionInput === 'function') handleExtensionInput({json.dumps(url)});"
            self._window.evaluate_js(js_code)
            _log.debug(f"Extension URL forwarded to UI: {url[:80]}...")

    # ================================================================
    # Config & History management with corruption recovery
    # ================================================================
    def _load_save_dir(self):
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    dir_path = data.get("save_dir")
                    if dir_path and os.path.isdir(dir_path):
                        _log.debug(f"Loaded save dir from config: {dir_path}")
                        return dir_path
        except (json.JSONDecodeError, IOError) as e:
            _log.warning(f"Config file corrupted, resetting: {e}")
            try:
                os.remove(config_path)
            except Exception:
                pass
        except Exception as e:
            _log.debug(f"Config load skipped: {e}")
        
        default = os.path.join(os.path.expanduser("~"), "Downloads")
        _log.info(f"Using default save dir: {default}")
        return default

    def _save_config(self):
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({"save_dir": self.save_dir}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            _log.warning(f"Failed to save config: {e}")

    def get_history(self):
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_history.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
        except (json.JSONDecodeError, IOError) as e:
            _log.warning(f"History file corrupted, resetting: {e}")
            try:
                os.remove(config_path)
            except Exception:
                pass
        except Exception as e:
            _log.debug(f"History load skipped: {e}")
        return []

    def add_history(self, item):
        history = self.get_history()
        # Dedup: remove if same URL already exists
        item_url = item.get('url', '')
        history = [h for h in history if h.get('url') != item_url]
        history.insert(0, item)
        history = history[:50]
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_history.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            _log.warning(f"Failed to save history: {e}")

    def clear_history(self):
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_history.json")
        try:
            if os.path.exists(config_path):
                os.remove(config_path)
            _log.info("History cleared")
            return True
        except Exception as e:
            _log.warning(f"Failed to clear history: {e}")
            return False

    # ================================================================
    # Window & File system utilities
    # ================================================================
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
                _log.debug(f"Opened folder: {target}")
        except Exception as e:
            _log.warning(f"Failed to open folder: {e}")

    def locate_file(self, filepath):
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
                _log.debug(f"Located file: {norm_path}")
            else:
                self.open_folder(os.path.dirname(norm_path) if os.path.dirname(norm_path) else None)
        except Exception as e:
            _log.warning(f"Failed to locate file: {e}")
            self.open_folder()

    def choose_folder(self):
        if self._window:
            result = self._window.create_file_dialog(webview.FOLDER_DIALOG, directory=self.save_dir)
            if result and len(result) > 0:
                self.save_dir = result[0]
                self._save_config()
                _log.info(f"Save directory changed to: {self.save_dir}")
                return self.save_dir
        return self.save_dir

    def choose_cookie_file(self):
        if self._window:
            file_types = ('Cookie Files (*.txt)', 'All files (*.*)')
            result = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
            if result and len(result) > 0:
                _log.debug(f"Cookie file selected: {result[0]}")
                return result[0]
        return ""

    # ================================================================
    # Music Player APIs
    # ================================================================
    def scan_music_folder(self, folder_path=None):
        """Scan a folder for all audio files and return their metadata"""
        import glob, json
        scan_dir = folder_path or self.save_dir
        if not os.path.isdir(scan_dir):
            return {'tracks': [], 'folder': scan_dir}
        audio_exts = ['*.mp3', '*.m4a', '*.aac', '*.flac', '*.ogg', '*.wav', '*.opus', '*.wma']
        tracks = []
        for ext in audio_exts:
            for fpath in glob.glob(os.path.join(scan_dir, ext)):
                fname = os.path.basename(fpath)
                name = os.path.splitext(fname)[0]
                tracks.append({
                    'title': name,
                    'uploader': 'مجلد التنزيلات',
                    'url': fpath.replace('\\', '/'),
                    'filepath': fpath,
                    'thumbnail': ''
                })
        tracks.sort(key=lambda x: os.path.getmtime(x['filepath']), reverse=True)
        _log.info(f"Scanned {len(tracks)} audio files in {scan_dir}")
        return {'tracks': tracks, 'folder': scan_dir}

    def add_music_files(self):
        """Open file dialog to pick audio files to add to the player"""
        if self._window:
            file_types = (
                'Audio Files (*.mp3;*.m4a;*.aac;*.flac;*.ogg;*.wav;*.opus;*.wma)',
                'All files (*.*)'
            )
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=True,
                file_types=file_types
            )
            if result:
                tracks = []
                for fpath in result:
                    fname = os.path.basename(fpath)
                    name = os.path.splitext(fname)[0]
                    tracks.append({
                        'title': name,
                        'uploader': 'مضافة يدوياً',
                        'url': fpath.replace('\\', '/'),
                        'filepath': fpath,
                        'thumbnail': ''
                    })
                return {'tracks': tracks}
        return {'tracks': []}

    def delete_music_track(self, filepath):
        """Delete an audio file from disk"""
        try:
            if filepath and os.path.isfile(filepath):
                os.remove(filepath)
                _log.info(f"Deleted music file: {filepath}")
                return {'ok': True}
            return {'ok': False, 'error': 'الملف غير موجود'}
        except Exception as e:
            _log.warning(f"Delete music error: {e}")
            return {'ok': False, 'error': str(e)}

    # ================================================================
    # Download & Media methods with Ultra error handling
    # ================================================================
    def get_clipboard(self):
        return get_clipboard_text()

    def validate_link(self, url, proxy=None):
        try:
            from downloader import validate_link
            result = validate_link(url, proxy=proxy)
            _log.debug(f"Link validation: {result.get('valid')} - {url[:60]}...")
            return result
        except Exception as e:
            _log.warning(f"Link validation exception: {e}")
            return {'valid': False, 'reason': str(e)}

    def fetch_info(self, url, browser_cookies='none', proxy=None):
        try:
            if not self.downloader:
                from downloader import MediaDownloader
                self.downloader = MediaDownloader()
                _log.info("MediaDownloader initialized")
            
            clean_proxy = (proxy or '').strip() or None
            info = self.downloader.fetch_info(url, browser_cookies=browser_cookies, proxy=clean_proxy)
            title = info.get('title', 'Unknown') if isinstance(info, dict) else 'Unknown'
            _log.debug(f"Fetched info for: {title[:50]}...")
            return {'data': info, 'error': None}
        except Exception as e:
            from downloader import clean_error_message
            err_msg = clean_error_message(e)
            _log.error(f"Fetch info failed for {url[:60]}: {err_msg}")
            return {'data': None, 'error': err_msg}

    def start_download(self, url, option, browser_cookies='none'):
        _log.info(f"Download queued: {url[:80]}... (type: {option.get('type', 'video')})")
        threading.Thread(
            target=self._async_download,
            args=(url, option, browser_cookies),
            daemon=True,
            name=f"DL-{url[:20]}"
        ).start()

    def _async_download(self, url, option, browser_cookies):
        start_t = time.time()
        
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
                url, option, self.save_dir,
                progress_callback=progress_callback,
                status_callback=status_callback,
                browser_cookies=browser_cookies
            )
            
            elapsed = time.time() - start_t
            _log.info(f"Download complete: {saved_filepath} ({elapsed:.1f}s)")
            
            if self._window:
                payload = {'status': 'complete', 'filepath': saved_filepath, 'elapsed': round(elapsed, 1)}
                self._window.evaluate_js(f'updateProgress({json.dumps(payload)})')
        except Exception as e:
            elapsed = time.time() - start_t
            _log.error(f"Download failed after {elapsed:.1f}s: {e}")
            if self._window:
                payload = {'status': 'error', 'error': str(e)}
                self._window.evaluate_js(f'updateProgress({json.dumps(payload)})')

    def resize_window(self, width, height):
        if self._window:
            try:
                self._window.resize(int(width), int(height))
            except Exception as e:
                _log.debug(f"Window resize failed: {e}")

    # ================================================================
    # Ultra: App Update & Installer Launch
    # ================================================================
    def check_app_update(self):
        try:
            import urllib.request
            req = urllib.request.Request(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                headers={'User-Agent': 'SDN-Downloader-App/2.7.0'}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
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
        except Exception as e:
            _log.debug(f"Update check failed (offline?): {e}")
        return {'has_update': False, 'current_version': CURRENT_APP_VERSION}

    def apply_app_update(self, download_url=None):
        _log.info(f"apply_app_update requested with url: {download_url}")
        
        # Direct raw EXE download link on GitHub main branch
        default_exe_url = f"https://github.com/{GITHUB_REPO}/raw/main/dist/SDN_Downloader_Setup.exe"
        target_url = download_url if (download_url and download_url.endswith('.exe')) else default_exe_url

        # Check for local compiled installer build for instant testing
        base_dir = os.path.dirname(os.path.abspath(__file__))
        local_dist_setup = os.path.join(base_dir, "dist", "SDN_Downloader_Setup.exe")

        def _do_update():
            try:
                import urllib.request
                import tempfile
                import shutil

                temp_dir = tempfile.gettempdir()
                setup_filename = f"SDN_Update_{int(time.time())}.exe"
                setup_path = os.path.join(temp_dir, setup_filename)
                self.pending_setup_path = setup_path

                # Fast Path 1: If local build exists, copy instantly (0.1s)
                if os.path.exists(local_dist_setup) and os.path.getsize(local_dist_setup) > 100000:
                    _log.info(f"Instant local update copy: {local_dist_setup} -> {setup_path}")
                    shutil.copy2(local_dist_setup, setup_path)
                    time.sleep(0.3)
                    if self._window:
                        payload = {'status': 'downloading', 'pct': 100, 'downloaded': os.path.getsize(setup_path), 'total': os.path.getsize(setup_path)}
                        self._window.evaluate_js(f'if (typeof onUpdateProgress === "function") onUpdateProgress({json.dumps(payload)});')
                else:
                    # Fast Path 2: Download directly from GitHub raw link
                    _log.info(f"Downloading update from: {target_url}")
                    req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                    with urllib.request.urlopen(req, timeout=120) as resp, open(setup_path, 'wb') as out_f:
                        total_size = int(resp.headers.get('content-length', 0) or resp.headers.get('Content-Length', 0))
                        downloaded = 0
                        chunk_size = 512 * 1024  # 512KB chunks for high speed

                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            out_f.write(chunk)
                            downloaded += len(chunk)
                            pct = min(int((downloaded / total_size) * 100), 99) if total_size > 0 else 50
                            if self._window:
                                payload = {'status': 'downloading', 'pct': pct, 'downloaded': downloaded, 'total': total_size}
                                self._window.evaluate_js(f'if (typeof onUpdateProgress === "function") onUpdateProgress({json.dumps(payload)});')

                _log.info(f"Update download complete: {setup_path}")
                time.sleep(0.5)
                clean_path = setup_path.replace('\\', '/')
                if self._window:
                    payload = {'status': 'complete', 'setup_path': clean_path}
                    self._window.evaluate_js(f'if (typeof onUpdateProgress === "function") onUpdateProgress({json.dumps(payload)});')

                # Python backend auto-launches update installer after 0.8 seconds!
                time.sleep(0.8)
                self.launch_installer(setup_path)

            except Exception as e:
                _log.error(f"Update download failed: {e}")
                if self._window:
                    payload = {'status': 'error', 'error': f'فشل التنزيل التلقائي: {str(e)}'}
                    self._window.evaluate_js(f'if (typeof onUpdateProgress === "function") onUpdateProgress({json.dumps(payload)});')

        threading.Thread(target=_do_update, daemon=True, name="UpdateDownloader").start()
        return {'success': True}

    def launch_installer(self, setup_path=None):
        if getattr(self, '_installer_launched', False):
            _log.info("launch_installer already executed, skipping duplicate call.")
            return {'success': True}
        self._installer_launched = True
        try:
            _log.info(f"launch_installer called with parameter: {setup_path}")
            path = str(setup_path) if (setup_path and str(setup_path) != 'undefined' and str(setup_path).strip() != '' and os.path.exists(str(setup_path))) else None
            
            if not path:
                path = getattr(self, 'pending_setup_path', None)

            if not path or not os.path.exists(str(path)):
                import glob, tempfile
                temp_dir = tempfile.gettempdir()
                candidates = glob.glob(os.path.join(temp_dir, "SDN_Update_*.exe")) + glob.glob(os.path.join(temp_dir, "SDN_Downloader_Setup*.exe"))
                if candidates:
                    candidates.sort(key=os.path.getmtime, reverse=True)
                    path = candidates[0]

            if not path or not os.path.exists(str(path)):
                base_dir = os.path.dirname(os.path.abspath(__file__))
                local_dist = os.path.join(base_dir, "dist", "SDN_Downloader_Setup.exe")
                if os.path.exists(local_dist):
                    path = local_dist

            if not path or not os.path.exists(str(path)):
                _log.warning(f"Update package not found. path was: {setup_path}")
                return {'success': False, 'error': 'ملف التحديث غير موجود'}

            _log.info(f"Executing installer update package: {path}")

            if sys.platform == 'win32':
                try:
                    os.startfile(path)
                except Exception as e1:
                    _log.warning(f"os.startfile failed: {e1}, trying Popen...")
                    subprocess.Popen([path])
            else:
                subprocess.Popen([path])

            time.sleep(0.5)
            os._exit(0)
            return {'success': True}
        except Exception as e:
            _log.error(f"Launch installer failed: {e}")
            return {'success': False, 'error': str(e)}


# ================================================================
# ULTRA MAIN - Optimized startup sequence
# ================================================================
def main():
    _log.info(f"🚀 SDN v{CURRENT_APP_VERSION} starting...")
    
    api = DownloaderBridgeAPI()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(base_dir, 'ui', 'index.html')
    
    if not os.path.exists(html_file):
        # Fallback: look in www/ for Capacitor
        html_file = os.path.join(base_dir, 'www', 'index.html')
        _log.warning(f"ui/index.html not found, falling back to: {html_file}")

    _log.info(f"Creating window with UI: {html_file}")
    
    # Wait briefly for preloader to finish (non-blocking with timeout)
    _preload_done.wait(timeout=2.0)
    
    window = webview.create_window(
        title='SDN',
        url=html_file,
        width=820,
        height=640,
        resizable=True,
        background_color='#07090e',
        js_api=api
    )
    api.set_window(window)
    
    _log.info(f"App ready in {time.time() - api._startup_time:.2f}s - starting WebView...")
    webview.start(debug=False)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
