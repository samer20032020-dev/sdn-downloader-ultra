# -*- coding: utf-8 -*-
"""Build the Android APK into dist/ and optionally publish its release asset."""

from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from version import APP_VERSION, GITHUB_REPO, RELEASE_TAG


ROOT = Path(__file__).resolve().parent
ANDROID_DIR = ROOT / "android"
DIST_DIR = ROOT / "dist"
APK_TARGET = DIST_DIR / "SDN_Downloader_Ultra.apk"
ANDROID_BUILD_ROOT = Path.home() / ".cache" / "sdn-android-build" / APP_VERSION
SDK_ROOT = Path(os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or (
    Path.home() / "AppData" / "Local" / "Android" / "Sdk"
))


def find_jdk() -> Path | None:
    candidates = [
        Path(os.environ.get("JAVA_HOME", "")),
        Path(r"C:\Program Files\Android\Android Studio\jbr"),
    ]
    candidates.extend(Path(path) for path in glob.glob(r"C:\Program Files\Eclipse Adoptium\jdk*"))
    candidates.extend(Path(path) for path in glob.glob(r"C:\Program Files\Java\jdk*"))
    candidates.extend(
        Path(path)
        for path in glob.glob(str(Path.home() / ".cache" / "sdn-jdk21*" / "jdk*"))
    )
    for candidate in candidates:
        java = candidate / "bin" / ("java.exe" if os.name == "nt" else "java")
        if not candidate or not java.is_file():
            continue
        try:
            version = subprocess.run(
                [str(java), "-version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            match = re.search(r'version "(\d+)', version.stderr or version.stdout)
            if match and int(match.group(1)) >= 21:
                return candidate
        except (OSError, subprocess.SubprocessError):
            continue
    return None


def run(command: list[str], cwd: Path = ROOT, timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    print("  $", " ".join(command))
    result = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.strip())
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}")
    return result


def configure_environment() -> None:
    jdk = find_jdk()
    if not jdk:
        raise RuntimeError("JDK 21+ was not found. Install Android Studio or Eclipse Temurin 21.")
    if not SDK_ROOT.is_dir():
        raise RuntimeError(f"Android SDK was not found: {SDK_ROOT}")

    os.environ["JAVA_HOME"] = str(jdk)
    os.environ["PATH"] = str(jdk / "bin") + os.pathsep + os.environ.get("PATH", "")
    os.environ["ANDROID_HOME"] = str(SDK_ROOT)
    os.environ["ANDROID_SDK_ROOT"] = str(SDK_ROOT)
    os.environ["SDN_ANDROID_BUILD_ROOT"] = str(ANDROID_BUILD_ROOT)

    local_properties = ANDROID_DIR / "local.properties"
    local_properties.write_text(
        f"sdk.dir={str(SDK_ROOT).replace(os.sep, '/')}\n",
        encoding="utf-8",
    )
    print(f"Using JDK: {jdk}")
    print(f"Using Android SDK: {SDK_ROOT}")
    print(f"Using Android build cache: {ANDROID_BUILD_ROOT}")


def build_apk() -> Path:
    configure_environment()
    run([sys.executable, "sync_ui.py"])
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        raise RuntimeError("npx was not found.")
    run([npx, "cap", "sync", "android"])

    gradle_wrapper = ANDROID_DIR / "gradle" / "wrapper" / "gradle-wrapper.jar"
    if not gradle_wrapper.is_file():
        raise RuntimeError(f"Gradle wrapper was not found: {gradle_wrapper}")
    # Calling the wrapper JAR directly avoids cmd.exe corrupting the Arabic
    # workspace path on some Windows installations.
    gradle_command = ["java", "-jar", "gradle/wrapper/gradle-wrapper.jar"]
    run(gradle_command + ["--stop"], cwd=ANDROID_DIR, timeout=120)
    run(
        gradle_command + ["clean", "assembleDebug", "--no-daemon", "--stacktrace"],
        cwd=ANDROID_DIR,
    )

    apk_source = ANDROID_BUILD_ROOT / "app" / "outputs" / "apk" / "debug" / "app-debug.apk"
    if not apk_source.is_file():
        raise RuntimeError(f"Generated APK was not found: {apk_source}")
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(apk_source, APK_TARGET)
    print(f"Built APK: {APK_TARGET} ({APK_TARGET.stat().st_size / 1024 / 1024:.1f} MB)")
    return APK_TARGET


def upload_apk(apk_path: Path) -> bool:
    from git_push import get_github_token, get_or_create_release, upload_asset

    token = get_github_token()
    if not token:
        print("GitHub credentials are unavailable; release upload was skipped.")
        return False
    release = get_or_create_release(token)
    if not release:
        raise RuntimeError(f"Unable to create or open GitHub release {RELEASE_TAG}.")
    return upload_asset(
        release,
        "SDN_Downloader_Ultra.apk",
        str(apk_path),
        "application/vnd.android.package-archive",
        token,
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"=== SDN Android {APP_VERSION} build ({GITHUB_REPO}) ===")
    apk = build_apk()
    if "--no-upload" not in sys.argv:
        upload_apk(apk)
    print("=== Android build completed ===")


if __name__ == "__main__":
    main()
