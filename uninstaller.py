# -*- coding: utf-8 -*-
"""SDN Downloader Ultra - Uninstaller"""
import os
import sys
import time
import subprocess
import shutil
import winreg
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def show_msg(text, title="SDN Downloader Ultra", flags=0x40):
    ctypes.windll.user32.MessageBoxW(0, text, title, flags)

def ask_yes_no(text, title="SDN Downloader Ultra"):
    # MB_YESNO = 0x04, MB_ICONQUESTION = 0x20
    res = ctypes.windll.user32.MessageBoxW(0, text, title, 0x04 | 0x20)
    return res == 6  # IDYES = 6

def run_uninstall(install_dir, parent_pid=None):
    if parent_pid:
        # Wait for the launcher process to exit so we can delete its exe
        try:
            p = subprocess.Popen(["powershell", "-NoProfile", "-Command", f"Wait-Process -Id {parent_pid} -Timeout 5 -ErrorAction SilentlyContinue"])
            p.wait(timeout=6)
        except Exception:
            time.sleep(1)

    # 1. Kill any running instances
    subprocess.run(["taskkill", "/f", "/im", "SDN_Downloader.exe"], capture_output=True, creationflags=0x08000000)
    subprocess.run(["taskkill", "/f", "/im", "SDN_Downloader_Standalone.exe"], capture_output=True, creationflags=0x08000000)
    time.sleep(0.5)

    # 2. Remove Shortcuts
    user_profile = os.environ.get("USERPROFILE", "")
    app_data = os.environ.get("APPDATA", "")
    shortcut_names = [
        "SDN Downloader Ultra.lnk",
        "إلغاء تثبيت SDN Downloader Ultra.lnk"
    ]
    shortcut_dirs = [
        os.path.join(user_profile, "Desktop"),
        os.path.join(user_profile, "OneDrive", "Desktop"),
        os.path.join(app_data, "Microsoft", "Windows", "Start Menu", "Programs")
    ]
    for d in shortcut_dirs:
        for s in shortcut_names:
            p = os.path.join(d, s)
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

    # 3. Remove Registry
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\SDN_Downloader_Ultra")
    except Exception:
        pass

    # 4. Remove Installation Directory using background cmd
    clean_cmd = f'timeout /t 1 /nobreak >nul & rmdir /s /q "{install_dir}"'
    subprocess.Popen(f'cmd /c {clean_cmd}', shell=True, creationflags=0x08000000)

    show_msg("تم إلغاء تثبيت SDN Downloader Ultra بنجاح من جهازك.", "اكتمل إلغاء التثبيت")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        # We are running from TEMP, perform actual deletion
        target_dir = sys.argv[2]
        parent_pid = int(sys.argv[3]) if len(sys.argv) > 3 else None
        run_uninstall(target_dir, parent_pid)
        sys.exit(0)

    # Normal user launch: confirm uninstall
    if not ask_yes_no("هل أنت متأكد من رغبتك في إلغاء تثبيت برنامج SDN Downloader Ultra بالكامل؟", "تأكيد إلغاء التثبيت"):
        sys.exit(0)

    # Copy self to temp and launch worker so that install directory files can be removed
    my_exe = os.path.abspath(sys.argv[0])
    install_dir = os.path.dirname(my_exe)

    temp_uninst = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "sdn_uninstaller_worker.exe")
    try:
        shutil.copy2(my_exe, temp_uninst)
        subprocess.Popen([temp_uninst, "--worker", install_dir, str(os.getpid())])
    except Exception as e:
        # Fallback to direct uninstall
        run_uninstall(install_dir)

if __name__ == "__main__":
    main()
