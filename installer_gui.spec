# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

datas = [
    ('ui/installer.html', 'ui')
]
if os.path.exists('app_icon.ico'):
    datas.append(('app_icon.ico', '.'))
if os.path.exists('dist/SDN_Downloader_Standalone.exe'):
    datas.append(('dist/SDN_Downloader_Standalone.exe', '.'))
elif os.path.exists('SDN_Downloader_Standalone.exe'):
    datas.append(('SDN_Downloader_Standalone.exe', '.'))
elif os.path.exists('dist/SDN_Downloader_App'):
    datas.append(('dist/SDN_Downloader_App', 'SDN_Downloader_App'))
binaries = []
hiddenimports = ['webview', 'clr', 'pythonnet', 'clr_loader']

for pkg in ('pywebview', 'clr_loader', 'pythonnet'):
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

try:
    import webview
    pyw_lib = os.path.join(os.path.dirname(webview.__file__), 'lib')
    if os.path.exists(pyw_lib):
        runtimes_dir = os.path.join(pyw_lib, 'runtimes')
        if os.path.exists(runtimes_dir):
            for platform_name in ('win-x64', 'win-x86', 'win-arm64'):
                native_dir = os.path.join(runtimes_dir, platform_name, 'native')
                if os.path.exists(native_dir):
                    datas.append((native_dir, f'{platform_name}/native'))
except Exception:
    pass

a = Analysis(
    ['installer_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc'],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SDN_Downloader_Setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico' if os.path.exists('app_icon.ico') else None
)
