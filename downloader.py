# -*- coding: utf-8 -*-
"""Reliable yt-dlp based media engine used by the desktop application."""

from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


def _user_ytdlp_path() -> str:
    """Directory holding an optional user-updated copy of yt-dlp."""
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / ".cache"
    return str(root / "SDN" / "yt_dlp_update")


def _activate_user_ytdlp() -> None:
    override = _user_ytdlp_path()
    if os.path.isfile(os.path.join(override, "yt_dlp", "__init__.py")):
        sys.path.insert(0, override)


_activate_user_ytdlp()

import yt_dlp

try:
    from app_logger import setup_logger
except ImportError:
    import logging as _logging

    def setup_logger(name="SDN"):
        _logging.basicConfig(level=_logging.DEBUG)
        return _logging.getLogger(name)

_log = setup_logger("SDN.Downloader")



ProgressCallback = Callable[[dict[str, Any]], None]
StatusCallback = Callable[[str], None]

AUDIO_EXTENSIONS = {
    ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wav", ".wma",
}
VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".mov", ".avi",
}
MEDIA_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


class DownloadCancelled(Exception):
    """Raised from a yt-dlp hook when the user cancels the active download."""


def get_ffmpeg_path() -> str:
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    candidate = os.path.join(base, "ffmpeg.exe")
    if os.path.isfile(candidate):
        return candidate

    try:
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if ffmpeg_exe and os.path.isfile(ffmpeg_exe):
            return ffmpeg_exe
    except Exception:
        pass

    return shutil.which("ffmpeg") or "ffmpeg"


def is_unviewable_playlist_id(playlist_id: str) -> bool:
    if not playlist_id:
        return False
    upper = str(playlist_id).strip().upper()
    return upper.startswith(("RD", "UL", "PU")) or upper in {"WL", "LL", "LM"}


def extract_video_id_from_mix(playlist_id: str) -> str | None:
    if not playlist_id:
        return None
    match = re.search(r"^RD(?:MM|AMVM)?([a-zA-Z0-9_-]{11})$", str(playlist_id).strip(), re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def extract_youtube_mix(
    video_id: str,
    playlist_id: str,
    proxy: str | None = None,
) -> list[dict[str, Any]] | None:
    """Extract tracks from YouTube mixes (RD...), radios, and playlist panels via Innertube next endpoint."""
    v_id = (video_id or "").strip()
    p_id = (playlist_id or "").strip()
    if not v_id and p_id:
        v_id = extract_video_id_from_mix(p_id) or ""
    if not v_id and not p_id:
        return None

    api_url = "https://www.youtube.com/youtubei/v1/next"
    payload: dict[str, Any] = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240301.00.00",
                "hl": "ar",
                "gl": "US",
            }
        },
    }
    if v_id:
        payload["videoId"] = v_id
    if p_id:
        payload["playlistId"] = p_id

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        },
    )

    try:
        opener = urllib.request.build_opener()
        if proxy and proxy.strip():
            opener.add_handler(urllib.request.ProxyHandler({"http": proxy.strip(), "https": proxy.strip()}))
        with opener.open(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    def find_all(obj: Any, key: str) -> list[Any]:
        results: list[Any] = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == key:
                    results.append(v)
                results.extend(find_all(v, key))
        elif isinstance(obj, list):
            for it in obj:
                results.extend(find_all(it, key))
        return results

    panels = find_all(data, "playlistPanelVideoRenderer")
    if not panels:
        return None

    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for idx, p in enumerate(panels, 1):
        vid = p.get("videoId") or ""
        if not vid or vid in seen_ids:
            continue
        seen_ids.add(vid)

        title = p.get("title", {}).get("simpleText")
        if not title:
            runs = p.get("title", {}).get("runs") or []
            title = "".join(r.get("text", "") for r in runs) or f"مقطع {idx}"

        length = p.get("lengthText", {}).get("simpleText")
        if not length:
            runs = p.get("lengthText", {}).get("runs") or []
            length = "".join(r.get("text", "") for r in runs) or ""

        thumbs = p.get("thumbnail", {}).get("thumbnails") or []
        thumb_url = thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

        items.append(
            {
                "index": len(items) + 1,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={vid}",
                "duration": length,
                "thumbnail": thumb_url,
                "selected": True,
            }
        )

    return items if items else None


def _find_youtube_video_fallback(url: str) -> str | None:
    try:
        parsed = urllib.parse.urlsplit(url or "")
        host = (parsed.hostname or "").lower()
        if not (host in {"youtu.be", "www.youtu.be"} or host.endswith("youtube.com")):
            return None
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        v = (query.get("v") or [""])[0].strip()
        if v:
            return f"https://www.youtube.com/watch?v={v}"
        if host in {"youtu.be", "www.youtu.be"}:
            path_part = parsed.path.strip("/").split("/", 1)[0]
            if path_part:
                return f"https://www.youtube.com/watch?v={path_part}"
        if parsed.path.startswith("/shorts/"):
            parts = parsed.path.split("/shorts/", 1)[1].split("/", 1)
            if parts and parts[0]:
                return f"https://www.youtube.com/watch?v={parts[0]}"
        playlist_id = (query.get("list") or [""])[0].strip()
        if playlist_id:
            mix_vid = extract_video_id_from_mix(playlist_id)
            if mix_vid:
                return f"https://www.youtube.com/watch?v={mix_vid}"
    except Exception:
        pass
    return None


def clean_url(url: str, keep_mix_playlist: bool = False) -> str:
    """Normalize common YouTube links without breaking mixes or unviewable playlists."""
    value = (url or "").strip()
    if not value:
        return ""

    try:
        parsed = urllib.parse.urlsplit(value)
        host = (parsed.hostname or "").lower()
        if not (host in {"youtu.be", "www.youtu.be"} or host.endswith("youtube.com")):
            return value

        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        playlist_id = (query.get("list") or [""])[0].strip()

        video_id = (query.get("v") or [""])[0].strip()
        if not video_id:
            if host in {"youtu.be", "www.youtu.be"}:
                video_id = parsed.path.strip("/").split("/", 1)[0]
            elif parsed.path.startswith("/shorts/"):
                video_id = parsed.path.split("/shorts/", 1)[1].split("/", 1)[0]
            elif parsed.path.startswith("/embed/"):
                video_id = parsed.path.split("/embed/", 1)[1].split("/", 1)[0]

        if not video_id and playlist_id:
            video_id = extract_video_id_from_mix(playlist_id) or ""

        if playlist_id:
            upper_list = playlist_id.upper()
            # YouTube Mixes & special radio lists (RD, UL, PU) must be accessed via /watch?v=...&list=...
            # because YouTube has no /playlist page for them and returns 'unviewable'.
            if upper_list.startswith(("RD", "UL", "PU")):
                if video_id:
                    clean_query: dict[str, Any] = {"v": video_id}
                    if keep_mix_playlist:
                        clean_query["list"] = playlist_id
                    if "t" in query:
                        clean_query["t"] = query["t"][0]
                    return f"https://www.youtube.com/watch?{urllib.parse.urlencode(clean_query)}"
                return value

            # Account private lists like Watch Later (WL) and Liked Videos (LL/LM):
            if upper_list in {"WL", "LL", "LM"}:
                if video_id:
                    clean_query = {"v": video_id}
                    if keep_mix_playlist:
                        clean_query["list"] = playlist_id
                    if "t" in query:
                        clean_query["t"] = query["t"][0]
                    return f"https://www.youtube.com/watch?{urllib.parse.urlencode(clean_query)}"
                return f"https://www.youtube.com/playlist?{urllib.parse.urlencode({'list': playlist_id})}"

            # Standard playlists (PL..., OLAK..., etc.)
            return urllib.parse.urlunsplit(
                (
                    "https",
                    "www.youtube.com",
                    "/playlist",
                    urllib.parse.urlencode({"list": playlist_id}),
                    "",
                )
            )

        if video_id:
            clean_query = {"v": video_id}
            if "t" in query:
                clean_query["t"] = query["t"][0]
            return f"https://www.youtube.com/watch?{urllib.parse.urlencode(clean_query)}"

    except Exception:
        return value

    return value


clean_media_url = clean_url


def _is_web_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url)
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def clean_error_message(err: Exception | str, url: str | None = None) -> str:
    text = str(err or "").strip()
    lowered = text.lower()
    url_lowered = str(url or "").lower()

    if isinstance(err, DownloadCancelled) or "download cancelled by user" in lowered:
        return "تم إلغاء التنزيل."
    if "the page needs to be reloaded" in lowered or "page needs to be reloaded" in lowered:
        return "⚠️ خوادم YouTube تطلب تحديث الجلسة. أعد المحاولة أو سجّل الدخول مجدداً من الإعدادات إذا كان المحتوى خاصاً."
    if "unviewable" in lowered or "this playlist type is unviewable" in lowered:
        return "❌ قائمة التشغيل هذه من نوع ميكس (Mix) أو خاصة وغير متاحة كقائمة كاملة."
    if "playlist does not exist" in lowered:
        if "wl" in lowered or "watch later" in lowered or "list=wl" in url_lowered:
            return "🔒 قائمة «المشاهدة لاحقاً» (Watch Later) خاصة بحسابك في يوتيوب ولا يمكن الوصول إليها بدون تسجيل دخول. الحل السريع: انقل الفيديوهات إلى قائمة تشغيل جديدة (غير مدرجة أو عامة)، أو استخدم ملف cookies.txt من الإعدادات."
        if "ll" in lowered or "liked" in lowered or "list=ll" in url_lowered:
            return "🔒 قائمة «الفيديوهات التي أعجبتني» (Liked Videos) خاصة بحسابك الشخصي. الحل السريع: انقل الفيديوهات إلى قائمة تشغيل جديدة (غير مدرجة أو عامة)، أو استخدم ملف cookies.txt من الإعدادات."
        return "❌ قائمة التشغيل غير موجودة أو تم حذفها، أو أنها خاصة وتتطلب تسجيل الدخول عبر الكوكيز (Cookies)."
    if "failed to decrypt with dpapi" in lowered or "could not copy chrome cookie database" in lowered or "cookie database" in lowered:
        return "🔒 تعذر قراءة كوكيز المتصفح بسبب تشفير النظام أو قفل المتصفح. أغلق المتصفح أولاً، أو استخدم ملف cookies.txt من الإعدادات."
    if "video unavailable" in lowered or "is unavailable" in lowered:
        return "❌ هذا المقطع غير متوفر أو حُذف من المنصة."
    if "private video" in lowered or "sign in if you've been granted access" in lowered or "this is a private video" in lowered:
        return "🔒 هذا المحتوى خاص. اختر ملف Cookies أو سجّل الدخول في المتصفح."
    if "members-only" in lowered or "login required" in lowered or "sign in to confirm" in lowered:
        return "🔐 يتطلب هذا المحتوى تسجيل الدخول. استخدم Cookies من المتصفح."
    if "unsupported url" in lowered:
        return "❌ الرابط غير مدعوم حاليًا أو ليس رابط وسائط صالحًا."
    if "403" in text or "forbidden" in lowered:
        return "🔒 خوادم المنصة رفضت الطلب مؤقتًا (HTTP 403: Forbidden). جرب جودة أخرى أو أعد المحاولة بعد قليل."
    if "429" in text or "too many requests" in lowered:
        return "⏳ المنصة حدّت عدد الطلبات مؤقتًا (HTTP 429: Too Many Requests). انتظر قليلًا أو استخدم Cookies/Proxy."
    if "geo" in lowered or "not available in your country" in lowered:
        return "🌍 هذا المحتوى غير متاح في منطقتك الجغرافية."
    if "ffmpeg" in lowered and ("not found" in lowered or "not installed" in lowered):
        return "⚙️ ملف FFmpeg المطلوب لدمج الفيديو والصوت غير موجود."
    if "404" in text or "not found" in lowered:
        return "❌ الرابط غير موجود أو القائمة خاصة."
    if any(part in lowered for part in ("network", "connection", "timed out", "temporary failure")):
        return "🌐 تعذر الاتصال بالشبكة. تحقق من الإنترنت ثم أعد المحاولة."

    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    text = re.sub(r"(?i)ERROR:\s*(?:\[.*?\]\s*)?", "", text)
    text = re.sub(r"^[a-zA-Z0-9_-]{11}:\s*", "", text)
    return text.strip() or "حدث خطأ غير متوقع أثناء معالجة الرابط."


def _common_ydl_options(proxy: str | None = None) -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "socket_timeout": 30,
        "retries": 15,
        "fragment_retries": 15,
        "extractor_retries": 5,
        "file_access_retries": 5,
        "concurrent_fragment_downloads": 1,
        "continuedl": True,
        "windowsfilenames": True,
        "http_chunk_size": 10485760,
        "buffersize": 1024 * 16,
    }
    if proxy and proxy.strip():
        options["proxy"] = proxy.strip()
    node_path = shutil.which("node")
    if node_path:
        options["js_runtimes"] = {"node": {"path": node_path}}
    return options


def get_youtube_session_cookie_path() -> str:
    """Path to the internally saved YouTube login cookie file."""
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / ".config"
    target_dir = root / "SDN"
    target_dir.mkdir(parents=True, exist_ok=True)
    return str(target_dir / "youtube_session_cookies.txt")


def save_cookies_to_netscape_file(cookies: list[Any], output_file: str) -> bool:
    """Convert SimpleCookie objects or cookie dictionaries to standard Netscape cookie file."""
    lines = [
        "# Netscape HTTP Cookie File\n",
        "# https://curl.haxx.se/rfc/cookie_spec.html\n",
        "# This is a generated file by SDN Downloader. Do not edit.\n\n",
    ]
    seen = set()
    now = int(time.time())
    default_expiry = now + 365 * 24 * 3600

    from http.cookies import BaseCookie

    for item in cookies or []:
        if isinstance(item, BaseCookie):
            for morsel in item.values():
                name = getattr(morsel, "key", "")
                val = getattr(morsel, "value", "")
                if not name:
                    continue
                domain = morsel.get("domain") or ".youtube.com"
                if not domain.startswith(".") and not domain.startswith("www"):
                    domain = "." + domain
                path = morsel.get("path") or "/"
                secure = "TRUE" if morsel.get("secure") else "FALSE"
                exp_raw = morsel.get("expires")
                expires = default_expiry
                if exp_raw:
                    try:
                        import email.utils
                        parsed = email.utils.parsedate_to_datetime(str(exp_raw))
                        expires = int(parsed.timestamp())
                    except Exception:
                        try:
                            expires = int(float(exp_raw))
                        except Exception:
                            expires = default_expiry
                key = (domain, path, name)
                if key not in seen:
                    seen.add(key)
                    sub = "TRUE" if domain.startswith(".") else "FALSE"
                    lines.append(f"{domain}\t{sub}\t{path}\t{secure}\t{expires}\t{name}\t{val}\n")
        elif isinstance(item, dict):
            name = item.get("name") or item.get("key")
            val = item.get("value") or item.get("val")
            if not name:
                continue
            domain = item.get("domain") or ".youtube.com"
            if not domain.startswith(".") and not domain.startswith("www"):
                domain = "." + domain
            path = item.get("path") or "/"
            secure = "TRUE" if item.get("secure") else "FALSE"
            exp_raw = item.get("expires")
            expires = default_expiry
            if exp_raw:
                try:
                    expires = int(float(exp_raw))
                except Exception:
                    expires = default_expiry
            key = (domain, path, name)
            if key not in seen:
                seen.add(key)
                sub = "TRUE" if domain.startswith(".") else "FALSE"
                lines.append(f"{domain}\t{sub}\t{path}\t{secure}\t{expires}\t{name}\t{val}\n")
        elif hasattr(item, "key") and hasattr(item, "value"):
            name = getattr(item, "key", "")
            val = getattr(item, "value", "")
            if not name:
                continue
            domain = getattr(item, "domain", None) or ".youtube.com"
            if not domain.startswith(".") and not domain.startswith("www"):
                domain = "." + domain
            path = getattr(item, "path", "/") or "/"
            secure = "TRUE" if getattr(item, "secure", False) else "FALSE"
            key = (domain, path, name)
            if key not in seen:
                seen.add(key)
                sub = "TRUE" if domain.startswith(".") else "FALSE"
                lines.append(f"{domain}\t{sub}\t{path}\t{secure}\t{default_expiry}\t{name}\t{val}\n")

    if not seen:
        return False

    target_path = Path(output_file)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True


def is_youtube_logged_in() -> bool:
    """Check if valid YouTube session cookies exist."""
    path = get_youtube_session_cookie_path()
    if not os.path.isfile(path) or os.path.getsize(path) < 20:
        return False
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return "LOGIN_INFO" in content or ("SID" in content and "SAPISID" in content)
    except Exception:
        return False


def logout_youtube() -> bool:
    """Remove saved YouTube session cookies."""
    path = get_youtube_session_cookie_path()
    try:
        if os.path.isfile(path):
            os.remove(path)
        return True
    except Exception:
        return False


def _apply_cookies(options: dict[str, Any], browser_cookies: str | None) -> None:
    cookie_source = (browser_cookies or "").strip()
    session_path = get_youtube_session_cookie_path()
    has_session = os.path.isfile(session_path) and os.path.getsize(session_path) > 20

    if cookie_source in ("no_cookies", "disabled", "off"):
        return

    if not cookie_source or cookie_source in ("none", "auto"):
        if has_session:
            options["cookiefile"] = session_path
        return

    if cookie_source == "youtube_login":
        if has_session:
            options["cookiefile"] = session_path
        return

    if os.path.isfile(cookie_source):
        options["cookiefile"] = cookie_source
    else:
        options["cookiesfrombrowser"] = (cookie_source,)


def validate_link(url: str, proxy: str | None = None) -> dict[str, Any]:
    normalized = clean_url(url, keep_mix_playlist=True)
    if not _is_web_url(normalized):
        return {"valid": False, "reason": "أدخل رابطًا يبدأ بـ http:// أو https://"}

    options = _common_ydl_options(proxy)
    options.update({"extract_flat": True, "playlistend": 1})
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(normalized, download=False)
        if not info:
            return {"valid": False, "reason": "تعذر الوصول للرابط أو المنصة غير مدعومة."}
        return {
            "valid": True,
            "title": info.get("title") or "مقطع وسائط",
            "platform": info.get("extractor_key") or info.get("extractor") or "منصة وسائط",
            "cleaned_url": normalized,
        }
    except Exception as exc:
        if "unviewable" in str(exc).lower():
            fallback = _find_youtube_video_fallback(url) or _find_youtube_video_fallback(normalized)
            if fallback and fallback != normalized:
                try:
                    with yt_dlp.YoutubeDL(options) as ydl:
                        fallback_info = ydl.extract_info(fallback, download=False)
                    if fallback_info:
                        return {
                            "valid": True,
                            "title": fallback_info.get("title") or "مقطع وسائط",
                            "platform": fallback_info.get("extractor_key") or fallback_info.get("extractor") or "منصة وسائط",
                            "cleaned_url": fallback,
                        }
                except Exception:
                    pass
        return {"valid": False, "reason": clean_error_message(exc, url=normalized)}


def _current_ytdlp_version() -> str:
    return str(getattr(getattr(yt_dlp, "version", None), "__version__", "unknown"))


def _version_tuple(value: str) -> tuple:
    numbers = [int(part) for part in re.findall(r"\d+", str(value or ""))[:4]]
    return tuple((numbers + [0, 0, 0, 0])[:4])


def _write_ytdlp_state(state_path: str, checked_at: float, returncode: int, version: str | None = None) -> None:
    try:
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(
                {"checked_at": checked_at, "returncode": returncode, "version": version or _current_ytdlp_version()},
                handle,
            )
    except Exception:
        pass


def _extract_ytdlp_wheel(wheel_path: str, target_dir: str) -> None:
    import zipfile

    staging = target_dir + ".staging"
    shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(staging, exist_ok=True)
    try:
        with zipfile.ZipFile(wheel_path) as archive:
            members = [name for name in archive.namelist() if name.startswith("yt_dlp/")]
            if "yt_dlp/__init__.py" not in members:
                raise RuntimeError("حزمة yt-dlp المنزّلة غير صالحة")
            archive.extractall(staging, members=members)
        if os.path.isdir(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)
        os.replace(staging, target_dir)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _update_ytdlp_frozen(state_path: str, force: bool) -> dict[str, Any]:
    """Download the latest yt-dlp wheel from PyPI and stage it for the next run."""
    import tempfile
    import urllib.request

    now = time.time()
    current_version = _current_ytdlp_version()

    if not force:
        try:
            with open(state_path, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            if now - float(state.get("checked_at", 0)) < 24 * 60 * 60:
                return {"updated": False, "reason": "recently_checked", "version": current_version}
        except Exception:
            pass

    try:
        request = urllib.request.Request(
            "https://pypi.org/pypi/yt-dlp/json",
            headers={"User-Agent": "SDN-Downloader-Ultra"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))

        latest_version = str((data.get("info") or {}).get("version") or "")
        wheel_url = ""
        wheel_sha256 = ""
        for file_info in data.get("urls") or []:
            if file_info.get("packagetype") == "bdist_wheel" and str(file_info.get("filename", "")).endswith(".whl"):
                wheel_url = str(file_info.get("url") or "")
                wheel_sha256 = str((file_info.get("digests") or {}).get("sha256") or "")
                break

        if not latest_version or not wheel_url:
            return {"updated": False, "reason": "no_release_found", "version": current_version}

        if _version_tuple(latest_version) <= _version_tuple(current_version):
            _write_ytdlp_state(state_path, now, 0, current_version)
            return {"updated": False, "reason": "up_to_date", "version": current_version}

        with tempfile.TemporaryDirectory(prefix="sdn-ytdlp-") as temp_dir:
            wheel_path = os.path.join(temp_dir, "yt_dlp_update.whl")
            wheel_request = urllib.request.Request(wheel_url, headers={"User-Agent": "SDN-Downloader-Ultra"})
            with urllib.request.urlopen(wheel_request, timeout=180) as response, open(wheel_path, "wb") as output:
                shutil.copyfileobj(response, output)

            if wheel_sha256:
                digest = hashlib.sha256()
                with open(wheel_path, "rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                if digest.hexdigest().lower() != wheel_sha256.lower():
                    raise RuntimeError("فشل التحقق من بصمة حزمة yt-dlp")

            _extract_ytdlp_wheel(wheel_path, _user_ytdlp_path())

        _write_ytdlp_state(state_path, now, 0, latest_version)
        _log.info(f"yt-dlp engine updated: {current_version} -> {latest_version} (restart required)")
        return {"updated": True, "reason": "installed", "version": latest_version, "restart_required": True}
    except Exception as exc:
        _log.warning(f"yt-dlp engine update failed: {exc}")
        _write_ytdlp_state(state_path, now, 1, current_version)
        return {"updated": False, "reason": clean_error_message(exc), "version": current_version}


def auto_update_ytdlp(force: bool = False) -> dict[str, Any]:
    """Update yt-dlp: pip in development, verified PyPI wheel in packaged builds."""
    state_path = os.path.join(os.path.expanduser("~"), ".sdn_ytdlp_update.json")

    if getattr(sys, "frozen", False):
        return _update_ytdlp_frozen(state_path, force)

    now = time.time()
    if not force:
        try:
            with open(state_path, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            if now - float(state.get("checked_at", 0)) < 24 * 60 * 60:
                return {
                    "updated": False,
                    "reason": "recently_checked",
                    "version": _current_ytdlp_version(),
                }
        except Exception:
            pass

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--upgrade",
                "yt-dlp",
            ],
            capture_output=True,
            text=True,
            timeout=180,
            creationflags=_NO_WINDOW,
        )
        _write_ytdlp_state(state_path, now, result.returncode)
        return {
            "updated": result.returncode == 0,
            "reason": "checked",
            "version": _current_ytdlp_version(),
        }
    except Exception as exc:
        return {"updated": False, "reason": clean_error_message(exc), "version": _current_ytdlp_version()}



def format_duration(seconds: int | float | None) -> str:
    if seconds is None:
        return "غير معروف"
    try:
        total = max(0, int(seconds))
        minutes, secs = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"
    except Exception:
        return "غير معروف"


def format_bytes(bytes_num: int | float | None) -> str:
    if bytes_num is None:
        return ""
    try:
        size = float(bytes_num)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                precision = 0 if unit == "B" else (2 if unit in {"GB", "TB"} else 1)
                return f"{size:.{precision}f} {unit}"
            size /= 1024
    except Exception:
        return ""
    return ""


def get_format_size(fmt: dict[str, Any], duration: int | float | None = None) -> str:
    file_size = fmt.get("filesize") or fmt.get("filesize_approx")
    if file_size:
        return format_bytes(file_size)
    total_bitrate = fmt.get("tbr")
    if total_bitrate and duration:
        return format_bytes((float(total_bitrate) * 1000 / 8) * float(duration))
    return ""


def _video_selector(height: int | None) -> str:
    height_filter = f"[height<={height}]" if height else ""
    # Prefer H.264 + M4A for broad Windows/Android compatibility, with resilient fallbacks.
    return (
        f"bestvideo{height_filter}[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/"
        f"bestvideo{height_filter}[ext=mp4]+bestaudio[ext=m4a]/"
        f"bestvideo{height_filter}+bestaudio/"
        f"best{height_filter}[ext=mp4]/best{height_filter}/best"
    )


def build_download_options() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    video_specs = [
        ("🎬 أفضل جودة متاحة", None, "Best"),
        ("🎥 جودة 4K Ultra HD (2160p)", 2160, "2160p"),
        ("📺 جودة 2K Quad HD (1440p)", 1440, "1440p"),
        ("💻 جودة Full HD (1080p)", 1080, "1080p"),
        ("📱 جودة HD (720p)", 720, "720p"),
        ("⚙️ جودة SD (480p)", 480, "480p"),
        ("⚡ جودة خفيفة (360p)", 360, "360p"),
        ("📉 جودة اقتصادية (240p)", 240, "240p"),
        ("📦 أصغر حجم فيديو متاح", 144, "144p"),
    ]
    video_options = [
        {
            "label": label,
            "format_id": _video_selector(height),
            "ext": "mp4",
            "type": "video",
            "quality_tag": tag,
            "size_str": "أعلى جودة" if height is None else tag,
        }
        for label, height, tag in video_specs
    ]

    audio_options = [
        {
            "label": f"🎵 صوت MP3 بجودة {quality} kbps",
            "format_id": "bestaudio/best",
            "ext": "mp3",
            "type": "audio",
            "quality": str(quality),
            "quality_tag": f"MP3-{quality}k",
            "size_str": f"{quality}k",
        }
        for quality in (320, 256, 192, 128, 64)
    ]
    audio_options.extend(
        [
            {
                "label": "🎶 صوت M4A/AAC متوافق وعالي الجودة",
                "format_id": "bestaudio[ext=m4a]/bestaudio/best",
                "ext": "m4a",
                "type": "audio",
                "quality": "256",
                "quality_tag": "M4A",
                "size_str": "M4A",
            },
            {
                "label": "🎼 صوت FLAC بدون فقدان",
                "format_id": "bestaudio/best",
                "ext": "flac",
                "type": "audio",
                "quality": "0",
                "quality_tag": "FLAC",
                "size_str": "Lossless",
            },
        ]
    )
    return video_options, audio_options


def _safe_quality_tag(option: dict[str, Any]) -> str:
    raw = option.get("quality_tag") or option.get("quality") or option.get("ext") or option.get("type") or "media"
    return re.sub(r"[^0-9A-Za-z._-]+", "-", str(raw)).strip("-")[:32] or "media"


def _path_to_uri(path: str | None) -> str:
    if not path:
        return ""
    try:
        return Path(path).resolve().as_uri()
    except Exception:
        return ""


class MediaDownloader:
    def __init__(self) -> None:
        self.ffmpeg_path = get_ffmpeg_path()
        self._cancel_event = threading.Event()
        self._download_lock = threading.Lock()

    def cancel(self) -> bool:
        self._cancel_event.set()
        return True

    def fetch_info(
        self,
        url: str,
        browser_cookies: str = "none",
        proxy: str | None = None,
    ) -> dict[str, Any]:
        normalized = clean_url(url, keep_mix_playlist=True)
        if not _is_web_url(normalized):
            raise ValueError("أدخل رابطًا صالحًا يبدأ بـ http:// أو https://")

        ydl_options = _common_ydl_options(proxy)
        ydl_options.update(
            {
                "extract_flat": "in_playlist",
                "ffmpeg_location": self.ffmpeg_path,
            }
        )
        parsed_norm = urllib.parse.urlsplit(normalized)
        norm_query = urllib.parse.parse_qs(parsed_norm.query)
        norm_list = (norm_query.get("list") or [""])[0].strip()
        norm_vid = (norm_query.get("v") or [""])[0].strip() or extract_video_id_from_mix(norm_list) or ""
        if norm_list.upper().startswith(("RD", "UL", "PU")):
            ydl_options["playlistend"] = 50

        _apply_cookies(ydl_options, browser_cookies)

        used_cookies = bool(ydl_options.get("cookiefile") or ydl_options.get("cookiesfrombrowser"))
        cookie_session_file = ydl_options.get("cookiefile")

        info = None
        try:
            with yt_dlp.YoutubeDL(ydl_options) as ydl:
                info = ydl.extract_info(normalized, download=False)
        except Exception as exc:
            # If cookies were used and extraction failed (e.g. YouTube session invalidation/reload),
            # automatically fallback to retry without cookies
            if used_cookies:
                exc_str = str(exc).lower()
                is_cookie_block = any(p in exc_str for p in (
                    "the page needs to be reloaded",
                    "page needs to be reloaded",
                    "sign in to confirm",
                    "unplayable",
                    "playability",
                    "dpapi",
                    "cookie database",
                    "403",
                    "forbidden",
                )) or "youtube" in exc_str
                if is_cookie_block:
                    try:
                        no_cookie_opts = dict(ydl_options)
                        no_cookie_opts.pop("cookiefile", None)
                        no_cookie_opts.pop("cookiesfrombrowser", None)
                        with yt_dlp.YoutubeDL(no_cookie_opts) as ydl_clean:
                            info = ydl_clean.extract_info(normalized, download=False)
                        if "page needs to be reloaded" in exc_str and cookie_session_file == get_youtube_session_cookie_path():
                            try:
                                logout_youtube()
                            except Exception:
                                pass
                    except Exception:
                        pass

            if not info:
                if norm_list:
                    mix_items = extract_youtube_mix(norm_vid, norm_list, proxy=proxy)
                    if mix_items:
                        video_options, audio_options = build_download_options()
                        return {
                            "is_playlist": True,
                            "title": f"قائمة تشغيل ({len(mix_items)} مقطع)",
                            "uploader": "YouTube Mix",
                            "thumbnail": mix_items[0].get("thumbnail") if mix_items else "",
                            "entry_count": len(mix_items),
                            "items": mix_items,
                            "video_options": video_options,
                            "audio_options": audio_options,
                            "cleaned_url": normalized,
                        }

                if "unviewable" in str(exc).lower():
                    fallback_url = _find_youtube_video_fallback(url) or _find_youtube_video_fallback(normalized)
                    if fallback_url and fallback_url != normalized:
                        try:
                            try:
                                with yt_dlp.YoutubeDL(ydl_options) as ydl:
                                    info = ydl.extract_info(fallback_url, download=False)
                            except Exception:
                                if used_cookies:
                                    no_cookie_opts = dict(ydl_options)
                                    no_cookie_opts.pop("cookiefile", None)
                                    no_cookie_opts.pop("cookiesfrombrowser", None)
                                    with yt_dlp.YoutubeDL(no_cookie_opts) as ydl_clean:
                                        info = ydl_clean.extract_info(fallback_url, download=False)
                                else:
                                    raise
                            normalized = fallback_url
                        except Exception:
                            raise RuntimeError(clean_error_message(exc, url=normalized)) from exc
                    else:
                        raise RuntimeError(clean_error_message(exc, url=normalized)) from exc
                else:
                    raise RuntimeError(clean_error_message(exc, url=normalized)) from exc

        if not info:
            raise RuntimeError("تعذر جلب معلومات الرابط. تحقق من الرابط ثم أعد المحاولة.")

        video_options, audio_options = build_download_options()
        entries = info.get("entries")
        is_playlist = info.get("_type") in {"playlist", "multi_video"} or isinstance(entries, (list, tuple))

        if not is_playlist and norm_list:
            mix_items = extract_youtube_mix(norm_vid, norm_list, proxy=proxy)
            if mix_items:
                return {
                    "is_playlist": True,
                    "title": info.get("title") or f"قائمة تشغيل ({len(mix_items)} مقطع)",
                    "uploader": info.get("uploader") or info.get("channel") or "YouTube",
                    "thumbnail": info.get("thumbnail") or (mix_items[0].get("thumbnail") if mix_items else ""),
                    "entry_count": len(mix_items),
                    "items": mix_items,
                    "video_options": video_options,
                    "audio_options": audio_options,
                    "cleaned_url": normalized,
                }

        if is_playlist:
            items: list[dict[str, Any]] = []
            for fallback_index, entry in enumerate(entries or [], 1):
                if not entry:
                    continue
                media_id = entry.get("id") or ""
                entry_url = entry.get("webpage_url") or entry.get("original_url") or entry.get("url") or ""
                if entry_url and not str(entry_url).startswith(("http://", "https://")) and media_id:
                    entry_url = f"https://www.youtube.com/watch?v={media_id}"
                index = entry.get("playlist_index") or fallback_index
                thumbnail = entry.get("thumbnail")
                if not thumbnail and media_id:
                    thumbnail = f"https://i.ytimg.com/vi/{media_id}/hqdefault.jpg"
                items.append(
                    {
                        "index": int(index),
                        "title": entry.get("title") or f"مقطع {fallback_index}",
                        "url": entry_url,
                        "duration": format_duration(entry.get("duration")),
                        "thumbnail": thumbnail or "",
                        "selected": True,
                    }
                )

            if not items:
                raise RuntimeError("القائمة فارغة أو خاصة ولا تحتوي عناصر قابلة للتنزيل.")

            return {
                "is_playlist": True,
                "title": info.get("title") or "قائمة تشغيل",
                "uploader": info.get("uploader") or info.get("channel") or info.get("extractor_key") or "منصة وسائط",
                "thumbnail": info.get("thumbnail") or items[0].get("thumbnail") or "",
                "entry_count": len(items),
                "items": items,
                "video_options": video_options,
                "audio_options": audio_options,
                "cleaned_url": normalized,
            }

        duration = info.get("duration")
        media_id = info.get("id") or ""
        thumbnail = info.get("thumbnail") or (
            f"https://i.ytimg.com/vi/{media_id}/hqdefault.jpg" if media_id else ""
        )
        return {
            "is_playlist": False,
            "title": info.get("title") or "وسائط بدون عنوان",
            "uploader": info.get("uploader") or info.get("channel") or "غير معروف",
            "duration": format_duration(duration),
            "thumbnail": thumbnail,
            "extractor": info.get("extractor_key") or info.get("extractor") or "منصة وسائط",
            "is_live": bool(info.get("is_live")),
            "live_status": info.get("live_status") or "",
            "video_options": video_options,
            "audio_options": audio_options,
            "cleaned_url": normalized,
        }

    def download(
        self,
        url: str,
        option: dict[str, Any],
        save_dir: str,
        progress_callback: ProgressCallback | None = None,
        status_callback: StatusCallback | None = None,
        browser_cookies: str = "none",
        item_complete_callback: Any = None,
    ) -> dict[str, Any]:
        normalized = clean_url(url, keep_mix_playlist=bool(option.get("is_playlist")))
        if not _is_web_url(normalized):
            raise ValueError("الرابط غير صالح.")
        if not os.path.isdir(save_dir):
            os.makedirs(save_dir, exist_ok=True)

        if not self._download_lock.acquire(blocking=False):
            raise RuntimeError("يوجد تنزيل آخر قيد التنفيذ. انتظر اكتماله أو ألغِه أولًا.")

        self._cancel_event.clear()
        try:
            return self._download_locked(
                normalized,
                option,
                save_dir,
                progress_callback,
                status_callback,
                browser_cookies,
                item_complete_callback,
            )
        finally:
            self._download_lock.release()
            self._cancel_event.clear()

    def _download_locked(
        self,
        url: str,
        option: dict[str, Any],
        save_dir: str,
        progress_callback: ProgressCallback | None,
        status_callback: StatusCallback | None,
        browser_cookies: str,
        item_complete_callback: Any = None,
    ) -> dict[str, Any]:
        is_audio = option.get("type") == "audio"
        is_playlist = bool(option.get("is_playlist"))
        format_id = option.get("format_id") or ("bestaudio/best" if is_audio else _video_selector(None))
        output_ext = str(option.get("ext") or ("mp3" if is_audio else "mp4")).lower()
        quality_tag = _safe_quality_tag(option)
        run_token = f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:-3]}-{uuid.uuid4().hex[:6]}"

        selected_indices: list[int] = []
        for value in option.get("playlist_items") or []:
            try:
                index = int(value)
                if 0 < index <= 100000 and index not in selected_indices:
                    selected_indices.append(index)
            except (TypeError, ValueError):
                continue
        selected_indices.sort()

        if is_playlist:
            template = os.path.join(
                save_dir,
                "%(playlist_title|Playlist).120B",
                f"%(playlist_index)03d - %(title).160B [%(id)s] [{quality_tag}].%(ext)s",
            )
        else:
            template = os.path.join(
                save_dir,
                f"%(title).180B [%(id)s] [{quality_tag}] [{run_token}].%(ext)s",
            )

        captured_files: list[str] = []
        captured_lock = threading.Lock()
        requested_count = len(selected_indices) if selected_indices else int(option.get("playlist_count") or 0)

        # Pre-scan existing files in save_dir and its subdirectories to prevent duplicate downloads
        allow_duplicate = bool(option.get("allow_duplicate"))
        target_exts = AUDIO_EXTENSIONS if is_audio else VIDEO_EXTENSIONS
        target_type_label = "صوت (Audio)" if is_audio else "فيديو (Video)"
        existing_disk_items: dict[str, str] = {}
        if not allow_duplicate and os.path.isdir(save_dir):
            try:
                for root, _, files in os.walk(save_dir):
                    for fname in files:
                        ext = os.path.splitext(fname)[1].lower()
                        if ext in target_exts:
                            full_p = os.path.join(root, fname)
                            try:
                                if os.path.getsize(full_p) > 1024:
                                    m = re.search(r'\[([a-zA-Z0-9_-]{11})\]', fname)
                                    if m:
                                        existing_disk_items[m.group(1)] = full_p
                            except OSError:
                                pass
            except Exception as e:
                _log.debug(f"Failed scanning existing disk items: {e}")

        def item_duplicate_filter(info_candidate: dict[str, Any], *, incomplete: bool = False) -> str | None:
            if allow_duplicate:
                return None
            vid = info_candidate.get("id")
            if vid and vid in existing_disk_items:
                it_title = info_candidate.get("title") or vid
                existing_path = existing_disk_items[vid]
                capture_path(existing_path)
                msg = f"⚠️ المقطع '{it_title[:35]}' موجود مسبقاً بنفس الصيغة ({target_type_label}) - تم تخطيه"
                if status_callback:
                    status_callback(msg)
                return msg
            return None

        def capture_path(candidate: str | None) -> None:
            if not candidate:
                return
            normalized_path = os.path.normpath(candidate)
            if Path(normalized_path).suffix.lower() not in MEDIA_EXTENSIONS:
                return
            with captured_lock:
                if normalized_path not in captured_files:
                    captured_files.append(normalized_path)

        def ydl_progress_hook(data: dict[str, Any]) -> None:
            if self._cancel_event.is_set():
                raise DownloadCancelled("Download cancelled by user")

            status = data.get("status")
            info_dict = data.get("info_dict") or {}
            playlist_index = int(info_dict.get("playlist_index") or 1)
            playlist_total = int(
                info_dict.get("n_entries")
                or info_dict.get("playlist_count")
                or requested_count
                or 1
            )
            if selected_indices:
                try:
                    playlist_position = selected_indices.index(playlist_index) + 1
                except ValueError:
                    playlist_position = min(playlist_index, len(selected_indices))
                playlist_total = len(selected_indices)
            else:
                playlist_position = min(playlist_index, playlist_total)

            raw_fn = str(data.get("filename") or info_dict.get("filepath") or info_dict.get("_filename") or "")
            ext = Path(raw_fn).suffix.lower()
            is_media = ext in MEDIA_EXTENSIONS

            if status == "finished":
                if is_media:
                    capture_path(raw_fn)
                    if status_callback:
                        status_callback("اكتمل تنزيل المسار، جاري تحضير المعالجة...")
                    if item_complete_callback and is_playlist and not postprocessors:
                        try:
                            item_complete_callback(playlist_position, info_dict.get("title") or "", raw_fn)
                        except Exception:
                            pass
                return

            if status != "downloading" or not progress_callback or not is_media:
                return

            downloaded = data.get("downloaded_bytes") or 0
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            item_percent = (float(downloaded) / float(total) * 100) if total else 0
            overall_percent = item_percent
            if is_playlist and playlist_total > 0:
                overall_percent = ((playlist_position - 1) + (item_percent / 100)) / playlist_total * 100

            speed = data.get("speed") or 0
            eta = data.get("eta")
            progress_callback(
                {
                    "status": "downloading",
                    "percent": max(0, min(overall_percent, 99.5)),
                    "item_percent": max(0, min(item_percent, 100)),
                    "downloaded_str": format_bytes(downloaded),
                    "total_str": format_bytes(total),
                    "speed_str": f"{format_bytes(speed)}/ثانية" if speed else "جاري الاتصال...",
                    "eta_str": f"{int(eta)} ثانية" if eta is not None else "",
                    "playlist_index": playlist_position if is_playlist else None,
                    "playlist_count": playlist_total if is_playlist else None,
                    "item_title": info_dict.get("title") or "",
                }
            )

        def postprocessor_hook(data: dict[str, Any]) -> None:
            if self._cancel_event.is_set():
                raise DownloadCancelled("Download cancelled by user")
            pp_status = data.get("status")
            pp_name = str(data.get("postprocessor") or "")
            if pp_status == "started" and status_callback:
                pp_lower = pp_name.lower()
                if "merg" in pp_lower:
                    status_callback("⚙️ جاري دمج مسارات الفيديو والصوت عبر FFmpeg...")
                elif "audio" in pp_lower:
                    status_callback("⚙️ جاري استخراج وتحويل مسار الصوت عبر FFmpeg...")
                elif "meta" in pp_lower:
                    status_callback("⚙️ جاري إضافة الغلاف والبيانات الوصفية...")
                elif "fixup" in pp_lower or "remux" in pp_lower:
                    status_callback("⚙️ جاري ضبط حاوية الوسائط (Remux)...")
                else:
                    status_callback("⚙️ جاري معالجة ودمج الملف عبر FFmpeg...")
            elif pp_status == "finished":
                info_dict = data.get("info_dict") or {}
                captured_fp = info_dict.get("filepath") or info_dict.get("_filename")
                capture_path(captured_fp)
                if status_callback:
                    status_callback("⚙️ اكتملت المعالجة، جاري حفظ وتجهيز الملف...")
                if item_complete_callback and is_playlist:
                    try:
                        p_idx = info_dict.get("playlist_index") or playlist_position
                        item_complete_callback(p_idx, info_dict.get("title") or "", captured_fp)
                    except Exception:
                        pass

        ydl_options = _common_ydl_options(option.get("proxy"))
        ydl_options.update(
            {
                "format": format_id,
                "outtmpl": template,
                "match_filter": item_duplicate_filter,
                "progress_hooks": [ydl_progress_hook],
                "postprocessor_hooks": [postprocessor_hook],
                "postprocessor_args": {"ffmpeg": ["-nostdin"]},
                "quiet": True,
                "no_warnings": True,
                "ffmpeg_location": self.ffmpeg_path,
                "noplaylist": not is_playlist,
                "ignoreerrors": is_playlist,
                "overwrites": False,
                "continuedl": True,
            }
        )
        if selected_indices:
            ydl_options["playlist_items"] = ",".join(str(index) for index in selected_indices)
        elif is_playlist:
            parsed_dl = urllib.parse.urlsplit(url)
            dl_query = urllib.parse.parse_qs(parsed_dl.query)
            dl_list = (dl_query.get("list") or [""])[0].upper()
            if dl_list.startswith(("RD", "UL", "PU")):
                ydl_options["playlistend"] = int(option.get("playlist_count") or 50)

        if option.get("download_subtitles"):
            ydl_options["writesubtitles"] = True
            ydl_options["writeautomaticsub"] = True
            ydl_options["subtitleslangs"] = ["ar", "en", "ar.*", "en.*"]
            ydl_options["subtitlesformat"] = "srt/best"
            # Subtitle download errors or 429 rate limits must never abort the video download
            ydl_options["ignoreerrors"] = True

        rate_limit = option.get("ratelimit")
        if rate_limit and isinstance(rate_limit, (int, float)) and rate_limit > 0:
            ydl_options["ratelimit"] = int(rate_limit)

        _apply_cookies(ydl_options, browser_cookies)

        if option.get("turbo"):
            ydl_options["concurrent_fragment_downloads"] = 4

        if not option.get("allow_live", True):
            def _reject_live(info_dict: dict, *, incomplete: bool = False):
                if info_dict.get("is_live"):
                    return "🔴 هذا المحتوى بث مباشر والتنزيل المباشر موقوف من الإعدادات"
                return None

            ydl_options["match_filter"] = _reject_live
        else:
            ydl_options["live_from_start"] = True

        postprocessors: list[dict[str, Any]] = []
        if is_audio:
            codec = output_ext if output_ext in {"mp3", "m4a", "flac", "wav", "opus"} else "mp3"
            extract_audio: dict[str, Any] = {
                "key": "FFmpegExtractAudio",
                "preferredcodec": codec,
            }
            if codec == "mp3":
                extract_audio["preferredquality"] = str(option.get("quality") or "320")
            postprocessors.append(extract_audio)
            postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})
        else:
            ydl_options["merge_output_format"] = "mp4"
            postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})
        ydl_options["postprocessors"] = postprocessors

        class _YDLDownloadLogger:
            def __init__(self):
                self.errors: list[str] = []
                self.warnings: list[str] = []

            def debug(self, msg):
                pass

            def info(self, msg):
                pass

            def warning(self, msg):
                self.warnings.append(str(msg))

            def error(self, msg):
                self.errors.append(str(msg))

        ydl_logger = _YDLDownloadLogger()
        ydl_options["logger"] = ydl_logger

        used_cookies = bool(ydl_options.get("cookiefile") or ydl_options.get("cookiesfrombrowser"))
        cookie_session_file = ydl_options.get("cookiefile")

        try:
            with yt_dlp.YoutubeDL(ydl_options) as ydl:
                info = ydl.extract_info(url, download=True)
        except DownloadCancelled:
            raise
        except Exception as exc:
            if self._cancel_event.is_set():
                raise DownloadCancelled("Download cancelled by user") from exc

            # If download failed with cookie rejection, automatically retry without cookies
            download_recovered = False
            if used_cookies:
                exc_str = str(exc).lower()
                is_cookie_block = any(p in exc_str for p in (
                    "the page needs to be reloaded",
                    "page needs to be reloaded",
                    "sign in to confirm",
                    "unplayable",
                    "playability",
                    "dpapi",
                    "cookie database",
                    "403",
                    "forbidden",
                )) or "youtube" in exc_str
                if is_cookie_block:
                    try:
                        no_cookie_opts = dict(ydl_options)
                        no_cookie_opts.pop("cookiefile", None)
                        no_cookie_opts.pop("cookiesfrombrowser", None)
                        with yt_dlp.YoutubeDL(no_cookie_opts) as ydl_clean:
                            info = ydl_clean.extract_info(url, download=True)
                        download_recovered = True
                        if "page needs to be reloaded" in exc_str and cookie_session_file == get_youtube_session_cookie_path():
                            try:
                                logout_youtube()
                            except Exception:
                                pass
                    except DownloadCancelled:
                        raise
                    except Exception:
                        download_recovered = False

            if not download_recovered:
                raise RuntimeError(clean_error_message(exc, url=url)) from exc

        # Resolve any Windows temporary merge files locked briefly by antivirus/indexing
        for temp_file in glob.glob(os.path.join(save_dir, "**", "*.temp.*"), recursive=True):
            target = temp_file.replace(".temp.", ".")
            for _ in range(5):
                try:
                    time.sleep(0.3)
                    if os.path.exists(temp_file):
                        if os.path.exists(target):
                            try:
                                os.remove(target)
                            except Exception:
                                pass
                        os.replace(temp_file, target)
                    if os.path.exists(target) and os.path.getsize(target) > 0:
                        capture_path(target)
                        break
                except Exception:
                    pass

        if not info and not captured_files:
            fatal_errors = [
                e for e in ydl_logger.errors
                if "subtitle" not in e.lower()
                and "timedtext" not in e.lower()
                and "thumbnail" not in e.lower()
            ]
            if fatal_errors:
                raise RuntimeError(clean_error_message(fatal_errors[-1]))
            raise RuntimeError("فشل التنزيل ولم تُنتج المنصة أي ملف.")

        # Post-processing hooks can omit the final path on some extractors.
        if not captured_files:
            info_entries = info.get("entries") if isinstance(info, dict) else None
            candidates = info_entries or [info]
            for entry in candidates:
                if not isinstance(entry, dict):
                    continue
                capture_path(entry.get("filepath") or entry.get("_filename"))
                for requested in entry.get("requested_downloads") or []:
                    capture_path(requested.get("filepath"))

        final_files = [path for path in captured_files if os.path.isfile(path)]
        if not final_files:
            # Last fallback: inspect the returned info structure.
            info_entries = info.get("entries") if isinstance(info, dict) else None
            candidates = info_entries or [info]
            for entry in candidates:
                if not isinstance(entry, dict):
                    continue
                capture_path(entry.get("filepath") or entry.get("_filename"))
                for requested in entry.get("requested_downloads") or []:
                    capture_path(requested.get("filepath"))
            final_files = [path for path in captured_files if os.path.isfile(path)]

        trim_start = option.get("trim_start")
        trim_end = option.get("trim_end")
        if final_files and (trim_start is not None or trim_end is not None):
            if status_callback:
                status_callback("جاري تطبيق وقت البداية والنهاية المحدد...")
            for file_path in list(final_files):
                self._trim_file(file_path, trim_start, trim_end)

        if not final_files:
            raise RuntimeError("اكتمل الاستخراج لكن تعذر العثور على الملف النهائي.")

        directory = os.path.dirname(final_files[0]) if is_playlist else save_dir
        file_items = [
            {
                "filepath": path,
                "playable_url": _path_to_uri(path) if Path(path).suffix.lower() in {
                    ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wav", ".wma"
                } else "",
                "title": Path(path).stem,
            }
            for path in final_files
        ]
        return {
            "filepath": final_files[0],
            "files": file_items,
            "count": len(final_files),
            "directory": directory,
            "is_playlist": is_playlist,
            "media_type": "audio" if is_audio else "video",
            "quality_tag": quality_tag,
        }

    def _trim_matching_subtitles(self, base_path: str, start_sec: float | None, end_sec: float | None) -> None:
        folder = os.path.dirname(base_path)
        prefix = os.path.basename(base_path)
        if not folder or not os.path.isdir(folder):
            return
        try:
            for item in os.listdir(folder):
                if item.startswith(prefix) and item.lower().endswith(('.srt', '.vtt')):
                    srt_path = os.path.join(folder, item)
                    _trim_srt_file(srt_path, start_sec, end_sec)
        except Exception as ex:
            _log.debug(f"Subtitle trimming error: {ex}")

    def _trim_file(self, file_path: str, trim_start: Any, trim_end: Any) -> None:
        start_sec = parse_time_to_seconds(trim_start)
        end_sec = parse_time_to_seconds(trim_end)
        if start_sec is None and end_sec is None:
            return

        base, ext = os.path.splitext(file_path)
        trimmed_path = f"{base}.trimmed{ext}"
        command = [self.ffmpeg_path, "-y", "-i", file_path]
        if start_sec is not None and start_sec > 0:
            command.extend(["-ss", str(start_sec)])
        if end_sec is not None and start_sec is not None:
            duration = end_sec - start_sec
            if duration > 0:
                command.extend(["-t", str(duration)])
        elif end_sec is not None:
            command.extend(["-to", str(end_sec)])

        command.extend(["-map", "0", "-c", "copy", trimmed_path])
        try:
            completed = subprocess.run(command, capture_output=True, timeout=120, creationflags=_NO_WINDOW)
            if completed.returncode == 0 and os.path.isfile(trimmed_path) and os.path.getsize(trimmed_path) > 0:
                os.replace(trimmed_path, file_path)
                self._trim_matching_subtitles(base, start_sec, end_sec)
                return
            elif os.path.exists(trimmed_path):
                os.remove(trimmed_path)
        except Exception:
            if os.path.exists(trimmed_path):
                try:
                    os.remove(trimmed_path)
                except Exception:
                    pass

        # Fallback to fast ultrafast re-encoding cut if stream copy fails
        command_reencode = [self.ffmpeg_path, "-y"]
        if start_sec is not None and start_sec > 0:
            command_reencode.extend(["-ss", str(start_sec)])
        command_reencode.extend(["-i", file_path])
        if end_sec is not None and start_sec is not None:
            duration = end_sec - start_sec
            if duration > 0:
                command_reencode.extend(["-t", str(duration)])
        elif end_sec is not None:
            command_reencode.extend(["-to", str(end_sec)])

        command_reencode.extend(["-map", "0", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-c:a", "copy", trimmed_path])
        try:
            res = subprocess.run(command_reencode, capture_output=True, timeout=300, creationflags=_NO_WINDOW)
            if res.returncode == 0 and os.path.isfile(trimmed_path) and os.path.getsize(trimmed_path) > 0:
                os.replace(trimmed_path, file_path)
                self._trim_matching_subtitles(base, start_sec, end_sec)
            elif os.path.exists(trimmed_path):
                os.remove(trimmed_path)
        except Exception:
            if os.path.exists(trimmed_path):
                try:
                    os.remove(trimmed_path)
                except Exception:
                    pass


def _trim_srt_file(srt_path: str, start_sec: float | None, end_sec: float | None) -> None:
    if not os.path.isfile(srt_path):
        return
    if start_sec is None and end_sec is None:
        return
    s_cut = start_sec if start_sec is not None else 0.0
    e_cut = end_sec if end_sec is not None else float("inf")

    def parse_srt_time(t_str: str) -> float:
        t_str = t_str.strip().replace(",", ".")
        parts = t_str.split(":")
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        try:
            return float(parts[0])
        except Exception:
            return 0.0

    def format_srt_time(sec: float) -> str:
        sec = max(0.0, sec)
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int(round((sec - int(sec)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    try:
        with open(srt_path, "r", encoding="utf-8-sig", errors="replace") as f:
            content = f.read()

        import re
        blocks = re.split(r'\n\s*\n', content.strip())
        new_blocks = []
        counter = 1
        for block in blocks:
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            if len(lines) < 2:
                continue
            time_idx = 1 if lines[0].isdigit() else 0
            if time_idx >= len(lines) or "-->" not in lines[time_idx]:
                continue
            t_parts = lines[time_idx].split("-->")
            if len(t_parts) != 2:
                continue
            t_start = parse_srt_time(t_parts[0])
            t_end = parse_srt_time(t_parts[1])

            if t_end < s_cut or t_start > e_cut:
                continue

            new_start = max(0.0, t_start - s_cut)
            new_end = max(0.0, t_end - s_cut)
            time_line = f"{format_srt_time(new_start)} --> {format_srt_time(new_end)}"
            text_lines = lines[time_idx + 1:]
            new_block = f"{counter}\n{time_line}\n" + "\n".join(text_lines)
            new_blocks.append(new_block)
            counter += 1

        trimmed_srt = "\n\n".join(new_blocks) + "\n"
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(trimmed_srt)
    except Exception as ex:
        _log.debug(f"Subtitle trimming exception: {ex}")


def parse_time_to_seconds(val: Any) -> float | None:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val) if val >= 0 else None
    val_str = str(val).strip()
    if not val_str:
        return None
    if val_str.replace(".", "", 1).isdigit():
        try:
            res = float(val_str)
            return res if res >= 0 else None
        except ValueError:
            return None
    parts = val_str.split(":")
    try:
        if len(parts) == 2:
            mins, secs = float(parts[0]), float(parts[1])
            return mins * 60 + secs
        elif len(parts) == 3:
            hrs, mins, secs = float(parts[0]), float(parts[1]), float(parts[2])
            return hrs * 3600 + mins * 60 + secs
    except ValueError:
        pass
    return None

