# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

datas = [('ui', 'ui')]
if os.path.exists('extension'):
    datas.append(('extension', 'extension'))
binaries = []
if os.path.exists('ffmpeg.exe'):
    binaries.append(('ffmpeg.exe', '.'))
hiddenimports = ['requests', 'urllib.parse', 'http.server', 'wsgiref.simple_server', 'clr', 'pythonnet', 'clr_loader', 'yt_dlp_ejs']

for pkg in ('pywebview', 'yt_dlp', 'clr_loader', 'pythonnet', 'yt_dlp_ejs'):
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
    ['main.py'],
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
    [],
    exclude_binaries=True,
    name='SDN_Downloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='app_icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SDN_Downloader_App'
)
