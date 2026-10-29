# -*- coding: utf-8 -*-
"""
SDN Downloader Ultra — Automatic Version Bump & Synchronizer
Increments semver (patch by default) and synchronizes across all project files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent


def get_current_version() -> str:
    version_file = ROOT / "version.py"
    match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', version_file.read_text(encoding="utf-8"))
    if not match:
        raise ValueError("Could not find APP_VERSION in version.py")
    return match.group(1).strip()


def compute_next_version(current: str, mode: str = "patch", explicit: str | None = None) -> str:
    if explicit:
        return explicit.strip().lstrip("v")
    parts = [int(p) for p in current.split(".")]
    while len(parts) < 3:
        parts.append(0)
    major, minor, patch = parts[:3]

    if mode == "major":
        return f"{major + 1}.0.0"
    elif mode == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"


def update_version_py(new_version: str) -> None:
    path = ROOT / "version.py"
    text = (
        '"""Single source of truth for SDN release metadata."""\n\n'
        f'APP_VERSION = "{new_version}"\n'
        'GITHUB_REPO = "samer20032020-dev/sdn-downloader-ultra"\n'
        'RELEASE_TAG = f"v{APP_VERSION}"\n'
    )
    path.write_text(text, encoding="utf-8")
    print(f"  [✓] Updated version.py -> {new_version}")


def update_android_gradle(new_version: str) -> None:
    gradle_file = ROOT / "android" / "app" / "build.gradle"
    if not gradle_file.is_file():
        return
    major, minor, patch = (int(p) for p in new_version.split(".")[:3])
    version_code = major * 10000 + minor * 100 + patch

    text = gradle_file.read_text(encoding="utf-8")
    text = re.sub(r"versionCode \d+", f"versionCode {version_code}", text, count=1)
    text = re.sub(r'versionName "[^"]*"', f'versionName "{new_version}"', text, count=1)
    gradle_file.write_text(text, encoding="utf-8")
    print(f"  [✓] Updated android/app/build.gradle -> versionCode {version_code}, versionName {new_version}")


def update_ui_index_html(new_version: str) -> None:
    ui_file = ROOT / "ui" / "index.html"
    if not ui_file.is_file():
        return
    text = ui_file.read_text(encoding="utf-8")

    # JS CURRENT_VERSION
    text = re.sub(r"let CURRENT_VERSION\s*=\s*'[^']*';", f"let CURRENT_VERSION = '{new_version}';", text, count=1)

    # Header update txt badge: <span id="updateHeaderTxt">vX.X.X</span>
    text = re.sub(r'<span id="updateHeaderTxt">v[^<]*</span>', f'<span id="updateHeaderTxt">v{new_version}</span>', text)

    # Welcome banner badge: <span>الإصدار X.X.X — ...</span>
    text = re.sub(r'الإصدار\s+[\d\.]+\s+—', f'الإصدار {new_version} —', text)

    # Settings version desc: <span class="settings-desc" id="settingsVersionTxt">SDN vX.X.X</span>
    text = re.sub(r'<span class="settings-desc" id="settingsVersionTxt">SDN v[^<]*</span>',
                  f'<span class="settings-desc" id="settingsVersionTxt">SDN v{new_version}</span>', text)

    ui_file.write_text(text, encoding="utf-8")
    print(f"  [✓] Updated ui/index.html (PC UI) -> v{new_version}")


def update_mobile_index_html(new_version: str) -> None:
    mobile_file = ROOT / "www" / "index.html"
    if not mobile_file.is_file():
        return
    text = mobile_file.read_text(encoding="utf-8")
    text = re.sub(r"let CURRENT_VERSION\s*=\s*'[^']*';", f"let CURRENT_VERSION = '{new_version}';", text, count=1)
    text = re.sub(r'SDN Ultra v[\d\.]+', f'SDN Ultra v{new_version}', text)
    mobile_file.write_text(text, encoding="utf-8")
    print(f"  [✓] Updated www/index.html (Mobile UI) -> v{new_version}")


def update_installer_iss(new_version: str) -> None:
    iss_file = ROOT / "installer_setup.iss"
    if not iss_file.is_file():
        return
    text = iss_file.read_text(encoding="utf-8")
    text = re.sub(r'#define MyAppVersion "[^"]*"', f'#define MyAppVersion "{new_version}"', text, count=1)
    iss_file.write_text(text, encoding="utf-8")
    print(f"  [✓] Updated installer_setup.iss -> {new_version}")


def update_service_worker(new_version: str) -> None:
    sw_file = ROOT / "www" / "service-worker.js"
    if not sw_file.is_file():
        return
    text = sw_file.read_text(encoding="utf-8")
    text = re.sub(r"const CACHE_NAME = 'sdn-mobile-v[\d\.]+'", f"const CACHE_NAME = 'sdn-mobile-v{new_version}'", text, count=1)
    sw_file.write_text(text, encoding="utf-8")
    print(f"  [✓] Updated www/service-worker.js -> v{new_version}")


def update_metadata_json(new_version: str) -> None:
    meta_file = ROOT / "assets" / "_internal" / "metadata" / "components.json"
    if not meta_file.is_file():
        return
    try:
        data = json.loads(meta_file.read_text(encoding="utf-8"))
        data["version"] = new_version
        meta_file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  [✓] Updated assets/_internal/metadata/components.json -> {new_version}")
    except Exception as e:
        print(f"  [!] Failed to update components.json: {e}")


def update_installer_html(new_version: str) -> None:
    html_file = ROOT / "ui" / "installer.html"
    if not html_file.is_file():
        return
    text = html_file.read_text(encoding="utf-8")
    text = re.sub(r'v\d+\.\d+\.\d+', f'v{new_version}', text)
    html_file.write_text(text, encoding="utf-8")
    print(f"  [✓] Updated ui/installer.html -> v{new_version}")


def update_app_config(new_version: str) -> None:
    cfg = ROOT / "assets" / "config" / "app.config"
    if not cfg.is_file():
        return
    text = cfg.read_text(encoding="utf-8")
    text = re.sub(r'<add key="Version" value="[^"]*" />', f'<add key="Version" value="{new_version}" />', text, count=1)
    cfg.write_text(text, encoding="utf-8")
    print(f"  [✓] Updated assets/config/app.config -> {new_version}")


def update_extensions(new_version: str) -> None:
    for name in ["manifest.json", "manifest.firefox.json"]:
        mf = ROOT / "extension" / name
        if not mf.is_file():
            continue
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
            data["version"] = new_version
            mf.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"  [✓] Updated extension/{name} -> {new_version}")
        except Exception as e:
            print(f"  [!] Failed to update extension/{name}: {e}")


def sync_ui() -> None:
    sync_script = ROOT / "sync_ui.py"
    if sync_script.is_file():
        import subprocess
        subprocess.run([sys.executable, str(sync_script)], cwd=str(ROOT), check=True)


def bump(mode: str = "patch", explicit: str | None = None) -> str:
    current = get_current_version()
    new_version = compute_next_version(current, mode=mode, explicit=explicit)
    print(f"🚀 Bumping version: {current} -> {new_version}")

    update_version_py(new_version)
    update_android_gradle(new_version)
    update_ui_index_html(new_version)
    update_mobile_index_html(new_version)
    update_service_worker(new_version)
    update_installer_html(new_version)
    update_installer_iss(new_version)
    update_app_config(new_version)
    update_metadata_json(new_version)
    update_extensions(new_version)
    sync_ui()

    print(f"✅ Successfully bumped and synchronized version to v{new_version}")
    return new_version


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bump SDN project version")
    parser.add_argument("--minor", action="store_true", help="Bump minor version")
    parser.add_argument("--major", action="store_true", help="Bump major version")
    parser.add_argument("--to", type=str, default=None, help="Explicit version target")
    args = parser.parse_args()

    mode = "patch"
    if args.major:
        mode = "major"
    elif args.minor:
        mode = "minor"

    bump(mode=mode, explicit=args.to)
