# -*- coding: utf-8 -*-
"""
SDN Downloader Ultra — سكريبت Git Push التلقائي
يبحث عن git تلقائياً ويرفع الكود إلى GitHub مع إنشاء/تحديث الـ Release
"""

import os
import sys
import subprocess
import json
import urllib.request
import urllib.error
import shutil

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# الإعدادات
# ============================================================
REPO          = "samer20032020-dev/sdn-downloader-ultra"
BRANCH        = "main"
RELEASE_TAG   = "v3.0.0"
RELEASE_NAME  = "SDN Downloader Ultra v3.0.0"
RELEASE_BODY  = (
    "## ⚡ SDN Downloader Ultra v3.0.0 — التحديث الرئيسي الكبير\n\n"
    "### ✨ المميزات الجديدة والتحديثات:\n"
    "- 🌟 خيار جديد في قسم الإعدادات: وضع الفائق فائق السرعة والمزامنة الذكية (Quantum Speed Multi-Thread v3.0)\n"
    "- 🚀 نظام التثبيت الصامت الفوري وإعادة التشغيل بنقرة واحدة من التنبيهات\n"
    "- 🎯 تحسين التوافقية وأعلى مستويات السرعة للتحميلات\n"
)

DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
ASSETS = [
    ("SDN_Downloader_Setup.exe",      "application/octet-stream"),
    ("SDN_Downloader_Standalone.exe", "application/octet-stream"),
    ("SDN_Downloader_Ultra.apk",      "application/vnd.android.package-archive"),
]

# ============================================================
# البحث عن Git
# ============================================================
def find_git() -> str:
    """يبحث عن git.exe في كل المسارات المعروفة"""
    # 1. PATH العادي
    git_in_path = shutil.which("git")
    if git_in_path:
        return git_in_path

    # 2. مسارات تثبيت Git for Windows الشائعة
    common_paths = [
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
        os.path.join(os.path.expanduser("~"), r"AppData\Local\Programs\Git\cmd\git.exe"),
        os.path.join(os.path.expanduser("~"), r"scoop\apps\git\current\cmd\git.exe"),
        r"C:\ProgramData\chocolatey\bin\git.exe",
        os.path.join(os.path.expanduser("~"), r".cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"),
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p

    # 3. بحث في مسار AppData
    appdata = os.environ.get("LOCALAPPDATA", "")
    if appdata:
        candidate = os.path.join(appdata, "Programs", "Git", "cmd", "git.exe")
        if os.path.exists(candidate):
            return candidate

    return None


def run_git(*args, cwd=None, check=True):
    """ينفذ أمر git بأمان"""
    git_exe = find_git()
    if not git_exe:
        print("❌ Git غير مثبت على هذا الجهاز!")
        print("   يرجى تحميل Git من: https://git-scm.com/download/win")
        print("   ثم أعد تشغيل السكريبت.")
        sys.exit(1)

    cmd = [git_exe] + list(args)
    proj_dir = cwd or os.path.dirname(os.path.abspath(__file__))
    print(f"  $ git {' '.join(args)}")
    result = subprocess.run(cmd, cwd=proj_dir, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        # git يطبع بعض المعلومات العادية في stderr
        print(result.stderr.strip())
    if check and result.returncode != 0:
        print(f"❌ فشل الأمر: git {' '.join(args)}")
        sys.exit(1)
    return result


# ============================================================
# GitHub API helpers
# ============================================================
def github_request(url, method="GET", data=None, headers=None, token=None):
    """إرسال طلب إلى GitHub API"""
    _headers = {"User-Agent": "SDN-AutoPush/2.4.0", "Accept": "application/vnd.github+json"}
    if token:
        _headers["Authorization"] = f"Bearer {token}"
    if headers:
        _headers.update(headers)

    req = urllib.request.Request(url, data=data, headers=_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            content = resp.read().decode("utf-8")
            if not content.strip():
                return {}
            return json.loads(content)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP {e.code}: {body[:200]}")
        return None


def get_or_create_release(token):
    """يجلب الـ Release الحالي أو ينشئ واحداً جديداً لـ RELEASE_TAG"""
    url = f"https://api.github.com/repos/{REPO}/releases/tags/{RELEASE_TAG}"
    data = github_request(url, token=token)
    if data and data.get("id"):
        print(f"  ✅ تم العثور على Release موجود لـ {RELEASE_TAG}: ID={data['id']}")
        return data

    print(f"  📌 إنشاء Release جديد برقم: {RELEASE_TAG}...")
    payload = json.dumps({
        "tag_name": RELEASE_TAG,
        "name": RELEASE_NAME,
        "body": RELEASE_BODY,
        "draft": False,
        "prerelease": False,
    }).encode("utf-8")
    data = github_request(
        f"https://api.github.com/repos/{REPO}/releases",
        method="POST",
        data=payload,
        headers={"Content-Type": "application/json"},
        token=token,
    )
    if data and data.get("id"):
        print(f"  ✅ تم إنشاء Release جديد لـ {RELEASE_TAG}: ID={data['id']}")
        return data
    print("  ❌ فشل إنشاء الـ Release")
    return None


def upload_asset(release_data, asset_name, asset_path, content_type, token):
    """يرفع ملفاً إلى GitHub Release"""
    # حذف الأصل القديم إن وجد
    for asset in release_data.get("assets", []):
        if asset.get("name") == asset_name:
            del_url = f"https://api.github.com/repos/{REPO}/releases/assets/{asset['id']}"
            github_request(del_url, method="DELETE", token=token)
            print(f"  🗑️  حُذف الأصل القديم: {asset_name}")

    # رفع الجديد
    upload_base = release_data.get("upload_url", "").split("{")[0]
    upload_url = f"{upload_base}?name={asset_name}"
    size = os.path.getsize(asset_path)
    print(f"  ⬆️  رفع {asset_name} ({size // 1024 // 1024:.1f} MB)...")

    with open(asset_path, "rb") as f:
        data = f.read()

    result = github_request(
        upload_url,
        method="POST",
        data=data,
        headers={"Content-Type": content_type},
        token=token,
    )
    if result and result.get("id"):
        print(f"  ✅ تم الرفع: {result.get('browser_download_url')}")
        return True
    print(f"  ❌ فشل رفع: {asset_name}")
    return False


def get_github_token():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    try:
        git_exe = find_git()
        if git_exe:
            res = subprocess.run(
                [git_exe, 'credential', 'fill'],
                input='protocol=https\nhost=github.com\n',
                capture_output=True,
                text=True,
                timeout=10
            )
            for line in res.stdout.splitlines():
                if line.startswith('password='):
                    return line.split('password=')[1].strip()
    except Exception:
        pass
    return None

# ============================================================
# الدالة الرئيسية
# ============================================================
def main():
    print("=" * 60)
    print("🚀 SDN Downloader Ultra — Git Push & Release Uploader")
    print("=" * 60)

    proj_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. التحقق من Git
    git_exe = find_git()
    if not git_exe:
        print("\n❌ Git غير مثبت على هذا الجهاز!")
        print("   حمّل Git من: https://git-scm.com/download/win")
        print("   بعد التثبيت أعد تشغيل هذا السكريبت.")
        sys.exit(1)
    print(f"\n✅ Git موجود: {git_exe}")

    # 2. Git Push
    print("\n📤 رفع الكود إلى GitHub...")
    run_git("add", "-A")
    run_git("commit", "-m", f"🔄 Auto-sync: source code update [{RELEASE_TAG}]", check=False)
    run_git("push", "origin", BRANCH, check=False)
    print("✅ Push تم بنجاح (أو لا يوجد تغييرات جديدة)")

    # 3. GITHUB_TOKEN
    token = get_github_token()
    if not token:
        print("\n⚠️  GITHUB_TOKEN غير محدد — سيتم تخطي رفع الـ Release assets.")
        print("   لتفعيل الرفع التلقائي: set GITHUB_TOKEN=<your_token>")
        print("\n✅ انتهى! الكود رُفع إلى GitHub بنجاح.")
        return

    # 4. رفع Release Assets
    print("\n📦 رفع ملفات الإصدار إلى GitHub Releases...")
    release = get_or_create_release(token)
    if not release:
        print("❌ تعذر الوصول إلى GitHub Releases. تأكد من صحة GITHUB_TOKEN.")
        sys.exit(1)

    success_count = 0
    for asset_name, content_type in ASSETS:
        asset_path = os.path.join(DIST_DIR, asset_name)
        if not os.path.exists(asset_path):
            print(f"  ⚠️  ملف غير موجود، يُتخطى: {asset_path}")
            continue
        if upload_asset(release, asset_name, asset_path, content_type, token):
            success_count += 1

    print(f"\n✅ اكتمل! تم رفع {success_count}/{len(ASSETS)} ملفات إلى GitHub Releases.")
    print(f"   رابط الإصدار: https://github.com/{REPO}/releases/tag/{RELEASE_TAG}")


if __name__ == "__main__":
    main()
