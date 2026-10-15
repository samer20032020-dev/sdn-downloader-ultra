import os
import sys
import multiprocessing

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

if __name__ == '__main__':
    multiprocessing.freeze_support()

import shutil
import subprocess
import threading
import time
import winreg
import base64
import ctypes
import json
import webview
from version import APP_VERSION

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        f"SDN.Downloader.Ultra.Installer.{APP_VERSION}"
    )
except Exception:
    pass

def get_bundle_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_default_install_dir():
    local_app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
    return os.path.join(local_app_data, 'Programs', 'SDN Downloader Ultra')

def get_real_desktop():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
            val, _ = winreg.QueryValueEx(key, "Desktop")
            expanded = os.path.expandvars(val)
            if os.path.exists(expanded):
                return expanded
    except Exception:
        pass
    onedrive_desktop = os.path.join(os.path.expanduser('~'), 'OneDrive', 'Desktop')
    if os.path.exists(onedrive_desktop):
        return onedrive_desktop
    return os.path.join(os.path.expanduser('~'), 'Desktop')

def get_real_start_menu():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
            val, _ = winreg.QueryValueEx(key, "Programs")
            expanded = os.path.expandvars(val)
            if os.path.exists(expanded):
                return expanded
    except Exception:
        pass
    return os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs')

def check_dir_is_installation(folder):
    """
    Check if a folder contains an existing SDN Downloader Ultra installation.
    Returns: (is_installed: bool, version: str | None)
    """
    if not folder or not os.path.isdir(folder):
        return False, None
    has_exe = os.path.exists(os.path.join(folder, 'SDN_Downloader.exe')) or os.path.exists(os.path.join(folder, 'SDN_Downloader_Standalone.exe'))
    has_vjson = os.path.exists(os.path.join(folder, 'version.json'))
    has_uninst = os.path.exists(os.path.join(folder, 'Uninstall.exe'))
    if has_exe or has_vjson or has_uninst:
        ver = None
        if has_vjson:
            try:
                with open(os.path.join(folder, 'version.json'), 'r', encoding='utf-8') as f:
                    ver = json.load(f).get('version')
            except Exception:
                pass
        return True, ver
    return False, None

def find_existing_installation():
    """
    Search Windows Registry and known standard locations for an existing installation of SDN Downloader Ultra.
    Returns: (install_dir: str | None, version: str | None)
    """
    # 1. Search Registry Uninstall keys (HKCU first, then HKLM)
    subkeys = [
        r"Software\Microsoft\Windows\CurrentVersion\Uninstall\SDN_Downloader_Ultra",
        r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\SDN_Downloader_Ultra"
    ]
    hives = [
        winreg.HKEY_CURRENT_USER,
        winreg.HKEY_LOCAL_MACHINE
    ]
    for hive in hives:
        for subkey in subkeys:
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    loc = None
                    ver = None
                    try:
                        loc, _ = winreg.QueryValueEx(key, "InstallLocation")
                    except OSError:
                        pass
                    try:
                        ver, _ = winreg.QueryValueEx(key, "DisplayVersion")
                    except OSError:
                        pass

                    if loc and os.path.isdir(loc):
                        is_inst, f_ver = check_dir_is_installation(loc)
                        if is_inst:
                            return loc, (f_ver or ver)
                        return loc, ver
            except OSError:
                pass

    # 2. Search Default Standard Directories
    local_app_data = os.environ.get('LOCALAPPDATA', '')
    prog_files = os.environ.get('ProgramFiles', '')
    prog_files_x86 = os.environ.get('ProgramFiles(x86)', '')
    default_checks = [
        os.path.join(local_app_data, 'Programs', 'SDN Downloader Ultra') if local_app_data else None,
        os.path.join(prog_files, 'SDN Downloader Ultra') if prog_files else None,
        os.path.join(prog_files_x86, 'SDN Downloader Ultra') if prog_files_x86 else None,
    ]
    for p in default_checks:
        if p and os.path.isdir(p):
            is_inst, ver = check_dir_is_installation(p)
            if is_inst:
                return p, ver

    return None, None

class InstallerAPI:
    def __init__(self):
        self._window = None
        existing_dir, existing_ver = find_existing_installation()
        if existing_dir:
            self.install_dir = existing_dir
            self.is_update = True
            self.existing_version = existing_ver
        else:
            self.install_dir = get_default_install_dir()
            self.is_update = False
            self.existing_version = None
        self.exe_path = None

    def set_window(self, window):
        self._window = window

    def get_install_info(self):
        return {
            "install_dir": self.install_dir,
            "is_update": self.is_update,
            "existing_version": self.existing_version or "",
            "app_version": APP_VERSION
        }

    def get_default_dir(self):
        return self.install_dir

    def choose_install_dir(self):
        if self._window:
            res = self._window.create_file_dialog(webview.FOLDER_DIALOG, directory=self.install_dir)
            if res and len(res) > 0:
                selected = res[0]
                self.install_dir = selected
                is_inst, ver = check_dir_is_installation(selected)
                self.is_update = is_inst
                self.existing_version = ver
                return {
                    "path": self.install_dir,
                    "is_update": self.is_update,
                    "existing_version": self.existing_version or "",
                    "app_version": APP_VERSION
                }
        return {
            "path": self.install_dir,
            "is_update": self.is_update,
            "existing_version": self.existing_version or "",
            "app_version": APP_VERSION
        }

    def close_window(self):
        if self._window:
            self._window.destroy()

    def start_install(self, target_dir, create_desktop):
        if target_dir:
            target_dir = target_dir.strip()
            is_inst, ver = check_dir_is_installation(target_dir)
            if is_inst:
                self.install_dir = target_dir
                self.is_update = True
                self.existing_version = ver
            else:
                norm_target = os.path.normpath(target_dir).lower()
                if not norm_target.endswith('sdn downloader ultra'):
                    target_dir = os.path.join(target_dir, 'SDN Downloader Ultra')
                self.install_dir = target_dir
                is_inst, ver = check_dir_is_installation(self.install_dir)
                if is_inst:
                    self.is_update = True
                    self.existing_version = ver

        threading.Thread(
            target=self._run_installation,
            args=(create_desktop,),
            daemon=True
        ).start()

    def _update_progress(self, percent, text, is_done=False):
        if self._window:
            safe_text = json.dumps(str(text))
            js = f"updateInstallProgress({int(percent)}, {safe_text}, {str(is_done).lower()});"
            self._window.evaluate_js(js)

    def _run_installation(self, create_desktop):
        try:
            init_msg = 'جاري إيقاف التطبيق والعمليات النشطة...' if self.is_update else 'جاري إنشاء مجلدات النظام...'
            self._update_progress(10, init_msg)

            CREATE_NO_WINDOW = 0x08000000
            subprocess.run(['taskkill', '/f', '/im', 'SDN_Downloader.exe'], capture_output=True, creationflags=CREATE_NO_WINDOW)
            subprocess.run(['taskkill', '/f', '/im', 'SDN_Downloader_Standalone.exe'], capture_output=True, creationflags=CREATE_NO_WINDOW)
            time.sleep(0.5)

            os.makedirs(self.install_dir, exist_ok=True)
            time.sleep(0.2)

            copy_msg = 'جاري تحديث ملفات البرنامج ومكونات النظام...' if self.is_update else 'جاري نسخ ملفات البرنامج ومكونات النظام...'
            self._update_progress(30, copy_msg)
            bundle_dir = get_bundle_dir()

            # 1. Main Application Executable (SDN_Downloader.exe)
            src_exe = os.path.join(bundle_dir, 'SDN_Downloader_Standalone.exe')
            if not os.path.exists(src_exe):
                src_exe = os.path.join(bundle_dir, 'dist', 'SDN_Downloader_Standalone.exe')
            if not os.path.exists(src_exe):
                src_exe = os.path.join(os.path.dirname(bundle_dir), 'dist', 'SDN_Downloader_Standalone.exe')

            dest_exe = os.path.join(self.install_dir, 'SDN_Downloader.exe')
            if os.path.exists(src_exe):
                shutil.copy2(src_exe, dest_exe)

            # 2. Runtime DLLs (python314.dll, vcruntime140.dll, msvcp140.dll, WebView2Loader.dll)
            for dll_name in ('python314.dll', 'vcruntime140.dll', 'msvcp140.dll', 'WebView2Loader.dll'):
                src_dll = os.path.join(bundle_dir, 'dlls', dll_name)
                if not os.path.exists(src_dll):
                    src_dll = os.path.join(bundle_dir, 'assets', 'dlls', dll_name)
                if not os.path.exists(src_dll):
                    src_dll = os.path.join(os.path.dirname(bundle_dir), 'assets', 'dlls', dll_name)
                if os.path.exists(src_dll):
                    try:
                        shutil.copy2(src_dll, os.path.join(self.install_dir, dll_name))
                    except Exception:
                        pass

            # 3. Standard configuration and engine files (settings.json, app.config, engine.ini)
            for cfg_name in ('settings.json', 'app.config', 'engine.ini'):
                src_cfg = os.path.join(bundle_dir, 'config', cfg_name)
                if not os.path.exists(src_cfg):
                    src_cfg = os.path.join(bundle_dir, 'assets', 'config', cfg_name)
                if not os.path.exists(src_cfg):
                    src_cfg = os.path.join(os.path.dirname(bundle_dir), 'assets', 'config', cfg_name)
                if os.path.exists(src_cfg):
                    dest_cfg = os.path.join(self.install_dir, cfg_name)
                    # If this is an update and settings.json already exists, PRESERVE user configuration!
                    if self.is_update and cfg_name == 'settings.json' and os.path.exists(dest_cfg):
                        continue
                    try:
                        shutil.copy2(src_cfg, dest_cfg)
                    except Exception:
                        pass

            # 4. Localization files (locales directory)
            src_locales = os.path.join(bundle_dir, 'locales')
            if not os.path.exists(src_locales):
                src_locales = os.path.join(os.path.dirname(bundle_dir), 'locales')
            if os.path.exists(src_locales):
                dest_locales = os.path.join(self.install_dir, 'locales')
                try:
                    shutil.copytree(src_locales, dest_locales, dirs_exist_ok=True)
                except Exception:
                    pass

            # 5. Core support and library directory (_internal directory)
            src_internal = os.path.join(bundle_dir, '_internal')
            if not os.path.exists(src_internal):
                src_internal = os.path.join(bundle_dir, 'assets', '_internal')
            if not os.path.exists(src_internal):
                src_internal = os.path.join(os.path.dirname(bundle_dir), 'assets', '_internal')
            if not os.path.exists(src_internal):
                src_internal = os.path.join(bundle_dir, 'dist', 'SDN_Downloader_App', '_internal')
            if os.path.exists(src_internal):
                dest_internal = os.path.join(self.install_dir, '_internal')
                try:
                    shutil.copytree(src_internal, dest_internal, dirs_exist_ok=True)
                except Exception:
                    pass

            # 6. FFmpeg engine (ffmpeg.exe)
            src_ffmpeg = os.path.join(bundle_dir, 'ffmpeg.exe')
            if not os.path.exists(src_ffmpeg):
                src_ffmpeg = os.path.join(os.path.dirname(bundle_dir), 'ffmpeg.exe')
            if os.path.exists(src_ffmpeg):
                shutil.copy2(src_ffmpeg, os.path.join(self.install_dir, 'ffmpeg.exe'))

            # 7. User interface assets (ui directory)
            src_ui = os.path.join(bundle_dir, 'ui')
            if not os.path.exists(src_ui):
                src_ui = os.path.join(os.path.dirname(bundle_dir), 'ui')
            if os.path.exists(src_ui):
                dest_ui = os.path.join(self.install_dir, 'ui')
                shutil.copytree(src_ui, dest_ui, dirs_exist_ok=True)

            # 8. Documentation and License (docs directory)
            docs_dir = os.path.join(self.install_dir, 'docs')
            os.makedirs(docs_dir, exist_ok=True)
            src_docs = os.path.join(bundle_dir, 'docs')
            if not os.path.exists(src_docs):
                src_docs = os.path.join(os.path.dirname(bundle_dir), 'docs')
            if os.path.exists(src_docs) and os.path.isdir(src_docs):
                shutil.copytree(src_docs, docs_dir, dirs_exist_ok=True)
            for doc_name, doc_target in [('README.md', 'README.txt'), ('LICENSE', 'LICENSE.txt'), ('THIRD_PARTY_NOTICES.md', 'THIRD_PARTY_NOTICES.txt')]:
                src_doc = os.path.join(bundle_dir, doc_name)
                if not os.path.exists(src_doc):
                    src_doc = os.path.join(os.path.dirname(bundle_dir), doc_name)
                if os.path.exists(src_doc):
                    shutil.copy2(src_doc, os.path.join(docs_dir, doc_target))

            # 9. Version and installation metadata (version.json)
            version_info = {
                "name": "SDN Downloader Ultra",
                "version": APP_VERSION,
                "publisher": "SDN Software",
                "engine": "yt-dlp + FFmpeg",
                "platform": "Windows x64",
                "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "is_update": self.is_update,
                "previous_version": self.existing_version if self.is_update else None
            }
            try:
                with open(os.path.join(self.install_dir, "version.json"), "w", encoding="utf-8") as vf:
                    json.dump(version_info, vf, ensure_ascii=False, indent=2)
            except Exception:
                pass

            # 10. Dedicated Uninstaller (Uninstall.exe)
            src_uninst = os.path.join(bundle_dir, 'Uninstall.exe')
            if not os.path.exists(src_uninst):
                src_uninst = os.path.join(bundle_dir, 'dist', 'Uninstall.exe')
            if not os.path.exists(src_uninst):
                src_uninst = os.path.join(os.path.dirname(bundle_dir), 'dist', 'Uninstall.exe')

            dest_uninst = os.path.join(self.install_dir, 'Uninstall.exe')
            has_uninst_exe = False
            if os.path.exists(src_uninst):
                shutil.copy2(src_uninst, dest_uninst)
                has_uninst_exe = True

            # Clean up old uninstall.vbs if present
            old_vbs = os.path.join(self.install_dir, 'uninstall.vbs')
            if os.path.exists(old_vbs):
                try:
                    os.remove(old_vbs)
                except Exception:
                    pass

            self.exe_path = dest_exe

            # 11. Copy icon file to install directory
            dest_icon = os.path.join(self.install_dir, 'app_icon.ico')
            src_icon = os.path.join(bundle_dir, 'app_icon.ico')
            if not os.path.exists(src_icon):
                src_icon = os.path.join(os.path.dirname(bundle_dir), 'app_icon.ico')
            if os.path.exists(src_icon):
                try:
                    shutil.copy2(src_icon, dest_icon)
                except Exception:
                    pass

            icon_path_for_lnk = dest_icon if os.path.exists(dest_icon) else dest_exe

            time.sleep(0.4)
            short_msg = 'جاري تحديث الاختصارات...' if self.is_update else 'جاري إنشاء الاختصارات...'
            self._update_progress(65, short_msg)
            app_name = "SDN Downloader Ultra"

            # Create Desktop Shortcut
            if create_desktop:
                desktop_folder = get_real_desktop()
                shortcut_path = os.path.join(desktop_folder, f"{app_name}.lnk")
                self._create_shortcut(dest_exe, shortcut_path, icon_path_for_lnk)

            # Create Start Menu Shortcuts
            start_menu = get_real_start_menu()
            start_shortcut = os.path.join(start_menu, f"{app_name}.lnk")
            self._create_shortcut(dest_exe, start_shortcut, icon_path_for_lnk)

            if has_uninst_exe and os.path.exists(dest_uninst):
                uninst_shortcut = os.path.join(start_menu, f"إلغاء تثبيت {app_name}.lnk")
                self._create_shortcut(dest_uninst, uninst_shortcut, dest_uninst)
            else:
                uninstaller_cmd = self._create_uninstaller_script(dest_exe)
                if uninstaller_cmd and os.path.exists(uninstaller_cmd):
                    uninst_shortcut = os.path.join(start_menu, f"إلغاء تثبيت {app_name}.lnk")
                    self._create_shortcut("wscript.exe", uninst_shortcut, icon_path_for_lnk, args=f'//nologo "{uninstaller_cmd}"')

            time.sleep(0.3)
            reg_msg = 'جاري تحديث سجل النظام (Windows Registry)...' if self.is_update else 'جاري تسجيل البرنامج في Windows...'
            self._update_progress(85, reg_msg)
            self._register_uninstall(dest_exe, dest_uninst if has_uninst_exe else None)

            time.sleep(0.3)
            done_msg = f'🎉 اكتمل تحديث البرنامج بنجاح إلى الإصدار {APP_VERSION}!' if self.is_update else '🎉 اكتمل التثبيت بنجاح!'
            self._update_progress(100, done_msg, is_done=True)

        except Exception as e:
            self._update_progress(0, f'❌ حدث خطأ أثناء التثبيت: {str(e)}', is_done=False)

    def _create_uninstaller_script(self, target_exe):
        install_folder = os.path.dirname(target_exe)
        uninstaller_path = os.path.join(install_folder, 'uninstall.vbs')

        script_content = (
            'On Error Resume Next\n'
            'Set WshShell = CreateObject("WScript.Shell")\n'
            'Set fso = CreateObject("Scripting.FileSystemObject")\n'
            '\n'
            'WshShell.Run "taskkill /f /im SDN_Downloader.exe", 0, True\n'
            'WshShell.Run "taskkill /f /im SDN_Downloader_Standalone.exe", 0, True\n'
            '\n'
            'Set env = WshShell.Environment("Process")\n'
            'userProfile = env("USERPROFILE")\n'
            'appData = env("APPDATA")\n'
            '\n'
            'fso.DeleteFile userProfile & "\\Desktop\\SDN Downloader Ultra.lnk", True\n'
            'fso.DeleteFile userProfile & "\\OneDrive\\Desktop\\SDN Downloader Ultra.lnk", True\n'
            'fso.DeleteFile appData & "\\Microsoft\\Windows\\Start Menu\\Programs\\SDN Downloader Ultra.lnk", True\n'
            'fso.DeleteFile appData & "\\Microsoft\\Windows\\Start Menu\\Programs\\\u0625\u0644\u063a\u0627\u0621 \u062a\u062b\u0628\u064a\u062a SDN Downloader Ultra.lnk", True\n'
            '\n'
            'WshShell.RegDelete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SDN_Downloader_Ultra\\"\n'
            '\n'
            'installDir = fso.GetParentFolderName(WScript.ScriptFullName)\n'
            'targetExeFile = installDir & "\\SDN_Downloader.exe"\n'
            'internalDir = installDir & "\\_internal"\n'
            'uiDir = installDir & "\\ui"\n'
            '\n'
            'If fso.FileExists(targetExeFile) Then fso.DeleteFile targetExeFile, True\n'
            'If fso.FolderExists(internalDir) Then fso.DeleteFolder internalDir, True\n'
            'If fso.FolderExists(uiDir) Then fso.DeleteFolder uiDir, True\n'
            '\n'
            'scriptPath = WScript.ScriptFullName\n'
            'cmdStr = "cmd /c timeout /t 2 /nobreak >nul & del /f /q """ & scriptPath & """ & rmdir """ & installDir & """"\n'
            'WshShell.Run cmdStr, 0, False\n'
        )
        try:
            with open(uninstaller_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
        except Exception:
            pass
        return uninstaller_path

    def _create_shortcut(self, target_exe, shortcut_path, icon_path=None, args=None):
        if not icon_path or not os.path.exists(icon_path):
            icon_path = target_exe

        args_str = f"$Shortcut.Arguments = '{args}'; " if args else ""

        ps_script = (
            f"$WshShell = New-Object -ComObject WScript.Shell; "
            f"$Shortcut = $WshShell.CreateShortcut('{shortcut_path}'); "
            f"$Shortcut.TargetPath = '{target_exe}'; "
            f"{args_str}"
            f"$Shortcut.WorkingDirectory = '{os.path.dirname(target_exe)}'; "
            f"$Shortcut.IconLocation = '{icon_path},0'; "
            f"$Shortcut.Save()"
        )
        try:
            encoded_script = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
            CREATE_NO_WINDOW = 0x08000000
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded_script],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW
            )
        except Exception:
            pass

    def _register_uninstall(self, target_exe, uninstaller_cmd=None):
        try:
            install_folder = os.path.dirname(target_exe)
            if uninstaller_cmd and uninstaller_cmd.lower().endswith('.exe') and os.path.exists(uninstaller_cmd):
                uninst_string = f'"{uninstaller_cmd}"'
                uninst_icon = f'"{uninstaller_cmd},0"'
            elif uninstaller_cmd and os.path.exists(uninstaller_cmd):
                uninst_string = f'wscript.exe //nologo "{uninstaller_cmd}"'
                uninst_icon = target_exe
            else:
                uninst_string = f'cmd /c "rmdir /s /q \\"{install_folder}\\""'
                uninst_icon = target_exe

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\SDN_Downloader_Ultra"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "SDN Downloader Ultra")
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "SDN Software")
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_folder)
                winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, uninst_icon)
                winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninst_string)
                winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, 275000)
        except Exception:
            pass

    def launch_app(self):
        try:
            if self.exe_path and os.path.exists(self.exe_path):
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen([self.exe_path], creationflags=CREATE_NO_WINDOW)
            self.close_window()
        except Exception:
            self.close_window()

def main():
    args_lower = [arg.lower() for arg in sys.argv]
    is_silent = any(flag in args_lower for flag in ('--silent', '-s', '/silent', '/verysilent'))
    
    if is_silent:
        try:
            api = InstallerAPI()
            CREATE_NO_WINDOW = 0x08000000
            subprocess.run(['taskkill', '/f', '/im', 'SDN_Downloader.exe'], capture_output=True, creationflags=CREATE_NO_WINDOW)
            subprocess.run(['taskkill', '/f', '/im', 'SDN_Downloader_Standalone.exe'], capture_output=True, creationflags=CREATE_NO_WINDOW)
            time.sleep(1.0)
            
            target_dir = None
            for arg in sys.argv:
                if arg.upper().startswith('/DIR='):
                    target_dir = arg.split('=', 1)[1].strip('\"\'')
                elif arg.lower().startswith('--dir='):
                    target_dir = arg.split('=', 1)[1].strip('\"\'')
            
            if target_dir:
                api.install_dir = target_dir
                is_inst, ver = check_dir_is_installation(target_dir)
                if is_inst:
                    api.is_update = True
                    api.existing_version = ver
            
            api._run_installation(create_desktop=True)
            time.sleep(0.5)
            api.launch_app()
        except Exception:
            pass
        sys.exit(0)

    api = InstallerAPI()
    bundle_dir = get_bundle_dir()
    html_file = os.path.join(bundle_dir, 'ui', 'installer.html')

    window_title = f"تحديث SDN Downloader Ultra ({APP_VERSION})" if api.is_update else f"تثبيت SDN Downloader Ultra ({APP_VERSION})"
    window = webview.create_window(
        title=window_title,
        url=html_file,
        width=560,
        height=480,
        resizable=False,
        frameless=True,
        easy_drag=True,
        background_color='#070a14',
        js_api=api
    )
    api.set_window(window)
    webview.start(debug=False)

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
