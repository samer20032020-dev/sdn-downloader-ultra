import os
import sys
import zipfile
import subprocess
import urllib.request
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "samer20032020-dev/sdn-downloader-ultra"
RELEASE_ID = 357054700
OLD_ASSET_ID = 484092256
SDK_ROOT = r"C:\Users\samer\AppData\Local\Android\Sdk"
ZIP_PATH = os.path.expandvars(r"%TEMP%\cmdline-tools.zip")

print("=== Starting Real Android APK Build & Upload Pipeline ===")

# 1. Check SDK / ZIP
if not os.path.exists(SDK_ROOT) and not os.path.exists(ZIP_PATH):
    print(f"Warning: Neither {SDK_ROOT} nor {ZIP_PATH} found!")
elif os.path.exists(ZIP_PATH):
    print(f"Found {ZIP_PATH}, size: {os.path.getsize(ZIP_PATH)} bytes")

# 2. Extract cmdline-tools
latest_dir = os.path.join(SDK_ROOT, "cmdline-tools", "latest")
os.makedirs(latest_dir, exist_ok=True)

sdkmanager_exe = os.path.join(latest_dir, "bin", "sdkmanager.bat")

if not os.path.exists(sdkmanager_exe) and os.path.exists(ZIP_PATH):
    print("Extracting cmdline-tools...")
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        temp_extract = os.path.expandvars(r"%TEMP%\cmdline-temp")
        zip_ref.extractall(temp_extract)
        
        # Move inner cmdline-tools contents to latest
        inner_cmd = os.path.join(temp_extract, "cmdline-tools")
        if os.path.exists(inner_cmd):
            import shutil
            for item in os.listdir(inner_cmd):
                s = os.path.join(inner_cmd, item)
                d = os.path.join(latest_dir, item)
                if os.path.isdir(s):
                    if os.path.exists(d): shutil.rmtree(d)
                    shutil.move(s, d)
                else:
                    shutil.move(s, d)

print(f"Sdkmanager ready at: {sdkmanager_exe}")

# 3. Accept Licenses
lic_dir = os.path.join(SDK_ROOT, "licenses")
os.makedirs(lic_dir, exist_ok=True)

with open(os.path.join(lic_dir, "android-sdk-license"), "w") as f:
    f.write("24333f8a63b6825696821368febe3fe303470648\n")
    f.write("d56f51874794514bf003d9230377c411b903d3d1\n")
    f.write("84831b94fe705e20623404e98d2b9e6a5528a552\n")

if os.path.exists(sdkmanager_exe):
    print("Installing Android SDK platforms and build-tools...")
    cmd_install = f'"{sdkmanager_exe}" --sdk_root="{SDK_ROOT}" "platforms;android-34" "build-tools;34.0.0" "platform-tools"'
    res = subprocess.run(cmd_install, shell=True, capture_output=True, text=True)
    print("Sdkmanager output:", res.stdout[:500])

# 5. Create local.properties
proj_dir = os.path.abspath(".")
android_dir = os.path.join(proj_dir, "android")
local_prop = os.path.join(android_dir, "local.properties")

with open(local_prop, "w") as f:
    f.write(f"sdk.dir={SDK_ROOT.replace('\\', '/')}\n")

print(f"Created local.properties at {local_prop}")

# 6. Build APK
print("Building APK via Gradle...")
orig_cwd = os.getcwd()
os.chdir(android_dir)

cmd_stop = 'java -jar gradle/wrapper/gradle-wrapper.jar --stop'
cmd_build = 'java -jar gradle/wrapper/gradle-wrapper.jar assembleDebug --no-daemon'

subprocess.run(cmd_stop, shell=True, capture_output=True)

import time
res_build = None
for attempt in range(1, 4):
    print(f"Gradle build attempt {attempt}/3...")
    res_build = subprocess.run(cmd_build, shell=True, capture_output=True, text=True)
    if res_build.returncode == 0:
        break
    print(f"Attempt {attempt} failed, stopping daemons and retrying in 3s...")
    subprocess.run(cmd_stop, shell=True, capture_output=True)
    time.sleep(3)

os.chdir(orig_cwd)

if res_build.returncode != 0:
    print("Build Failed after 3 attempts!")
    print(res_build.stdout)
    print(res_build.stderr)
    sys.exit(1)

apk_source = os.path.join(android_dir, "app", "build", "outputs", "apk", "debug", "app-debug.apk")
apk_target = os.path.join(proj_dir, "SDN_Downloader_Ultra.apk")
dist_apk_target = os.path.join(proj_dir, "dist", "SDN_Downloader_Ultra.apk")

if not os.path.exists(apk_source):
    print(f"Generated APK not found at {apk_source}")
    sys.exit(1)

import shutil
shutil.copyfile(apk_source, apk_target)
os.makedirs(os.path.dirname(dist_apk_target), exist_ok=True)
shutil.copyfile(apk_source, dist_apk_target)
apk_size = os.path.getsize(apk_target)
print(f"Successfully built real APK: {apk_target} ({apk_size} bytes)")

# 7. Delete Existing GitHub Release Assets for SDN_Downloader_Ultra.apk
print(f"Checking existing release assets for {REPO} (Release ID {RELEASE_ID})...")
try:
    req_rel = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/{RELEASE_ID}",
        headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "Python"}
    )
    with urllib.request.urlopen(req_rel) as resp:
        rel_data = json.loads(resp.read().decode())
        for asset in rel_data.get("assets", []):
            if asset.get("name") == "SDN_Downloader_Ultra.apk":
                a_id = asset.get("id")
                print(f"Deleting existing asset '{asset.get('name')}' (ID: {a_id})...")
                req_del = urllib.request.Request(
                    f"https://api.github.com/repos/{REPO}/releases/assets/{a_id}",
                    method="DELETE",
                    headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "Python"}
                )
                with urllib.request.urlopen(req_del):
                    print(f"Deleted asset ID {a_id} successfully.")
except Exception as e:
    print(f"Warning fetching/deleting assets: {e}")

# 8. Upload New APK to GitHub Release
print("Uploading new SDN_Downloader_Ultra.apk to GitHub Release v2.0.0...")
upload_url = f"https://uploads.github.com/repos/{REPO}/releases/{RELEASE_ID}/assets?name=SDN_Downloader_Ultra.apk"

with open(apk_target, "rb") as f:
    apk_data = f.read()

req_up = urllib.request.Request(
    upload_url,
    data=apk_data,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/vnd.android.package-archive",
        "User-Agent": "Python"
    }
)

with urllib.request.urlopen(req_up) as response:
    resp_data = json.loads(response.read().decode())
    print("=== Upload Complete! ===")
    print("Asset ID:", resp_data.get("id"))
    print("Download URL:", resp_data.get("browser_download_url"))
    print("Size:", resp_data.get("size"))
