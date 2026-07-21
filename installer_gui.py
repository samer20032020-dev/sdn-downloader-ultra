import os
import sys
import multiprocessing

if __name__ == '__main__':
    multiprocessing.freeze_support()

import shutil
import subprocess
import threading
import time
import winreg
import base64
import ctypes
import webview

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SDN.Downloader.Ultra.Installer.2.0")
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

class InstallerAPI:
    def __init__(self):
        self._window = None
        self.install_dir = get_default_install_dir()
        self.exe_path = None

    def set_window(self, window):
        self._window = window

    def get_default_dir(self):
        return self.install_dir

    def choose_install_dir(self):
        if self._window:
            res = self._window.create_file_dialog(webview.FOLDER_DIALOG, directory=self.install_dir)
            if res and len(res) > 0:
                self.install_dir = res[0]
                return self.install_dir
        return self.install_dir

    def close_window(self):
        if self._window:
            self._window.destroy()

    def start_install(self, target_dir, create_desktop):
        if target_dir:
            target_dir = target_dir.strip()
            norm_target = os.path.normpath(target_dir).lower()
            if not norm_target.endswith('sdn downloader ultra'):
                target_dir = os.path.join(target_dir, 'SDN Downloader Ultra')
            self.install_dir = target_dir

        threading.Thread(
            target=self._run_installation,
            args=(create_desktop,),
            daemon=True
        ).start()

    def _update_progress(self, percent, text, is_done=False):
        if self._window:
            js = f"updateInstallProgress({percent}, '{text}', {str(is_done).lower()});"
            self._window.evaluate_js(js)

    def _run_installation(self, create_desktop):
        try:
            self._update_progress(10, 'جاري إنشاء مجلدات النظام...')
            os.makedirs(self.install_dir, exist_ok=True)
            time.sleep(0.3)

            self._update_progress(30, 'جاري نسخ ملفات البرنامج فائقة السرعة...')
            bundle_dir = get_bundle_dir()
            
            src_exe = os.path.join(bundle_dir, 'SDN_Downloader_Standalone.exe')
            if not os.path.exists(src_exe):
                src_exe = os.path.join(bundle_dir, 'dist', 'SDN_Downloader_Standalone.exe')
            if not os.path.exists(src_exe):
                src_exe = os.path.join(os.path.dirname(bundle_dir), 'dist', 'SDN_Downloader_Standalone.exe')

            if os.path.exists(src_exe):
                shutil.copy2(src_exe, os.path.join(self.install_dir, 'SDN_Downloader.exe'))
            else:
                src_app_dir = os.path.join(bundle_dir, 'SDN_Downloader_App')
                if not os.path.exists(src_app_dir):
                    parent_dist = os.path.join(bundle_dir, 'dist', 'SDN_Downloader_App')
                    if os.path.exists(parent_dist):
                        src_app_dir = parent_dist
                    else:
                        src_app_dir = os.path.join(os.path.dirname(bundle_dir), 'dist', 'SDN_Downloader_App')

                if os.path.exists(src_app_dir):
                    shutil.copytree(src_app_dir, self.install_dir, dirs_exist_ok=True)

            dest_exe = os.path.join(self.install_dir, 'SDN_Downloader.exe')
            self.exe_path = dest_exe

            # Copy icon file to install directory if available
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

            # Create uninstaller script inside install directory
            uninstaller_cmd = self._create_uninstaller_script(dest_exe)

            time.sleep(0.4)
            self._update_progress(65, 'جاري إنشاء الاختصارات...')
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

            if uninstaller_cmd and os.path.exists(uninstaller_cmd):
                uninst_shortcut = os.path.join(start_menu, f"إلغاء تثبيت {app_name}.lnk")
                self._create_shortcut("wscript.exe", uninst_shortcut, icon_path_for_lnk, args=f'//nologo "{uninstaller_cmd}"')

            time.sleep(0.3)
            self._update_progress(85, 'جاري تسجيل البرنامج في Windows...')
            self._register_uninstall(dest_exe, uninstaller_cmd)

            time.sleep(0.3)
            self._update_progress(100, '🎉 اكتمل التثبيت بنجاح!', is_done=True)

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
            'fso.DeleteFile appData & "\\Microsoft\\Windows\\Start Menu\\Programs\\إلغاء تثبيت SDN Downloader Ultra.lnk", True\n'
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
            uninst_string = f'wscript.exe //nologo "{uninstaller_cmd}"' if uninstaller_cmd else f'cmd /c "rmdir /s /q \"{install_folder}\""'
            
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\SDN_Downloader_Ultra"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "SDN Downloader Ultra")
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "2.0")
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "SDN Software")
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_folder)
                winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, target_exe)
                winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninst_string)
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
    if '--silent' in sys.argv or '-s' in sys.argv or '/SILENT' in sys.argv:
        try:
            api = InstallerAPI()
            subprocess.run(['taskkill', '/f', '/im', 'SDN_Downloader.exe'], capture_output=True)
            time.sleep(1.5)
            target_dir = get_default_install_dir()
            api.install_dir = target_dir
            api._run_installation(create_desktop=True)
            time.sleep(0.5)
            api.launch_app()
        except Exception:
            pass
        sys.exit(0)

    api = InstallerAPI()
    bundle_dir = get_bundle_dir()
    html_file = os.path.join(bundle_dir, 'ui', 'installer.html')

    window = webview.create_window(
        title='تثبيت SDN Downloader Ultra',
        url=html_file,
        width=560,
        height=450,
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
