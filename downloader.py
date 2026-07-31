# -*- coding: utf-8 -*-
"""Reliable yt-dlp based media engine used by the desktop application."""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import yt_dlp


ProgressCallback = Callable[[dict[str, Any]], None]
StatusCallback = Callable[[str], None]

MEDIA_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".mov", ".avi",
    ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wav", ".wma",
}


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


def clean_url(url: str) -> str:
    """Normalize common YouTube links without discarding playlist parameters."""
    value = (url or "").strip()
    if not value:
        return ""

    try:
        parsed = urllib.parse.urlsplit(value)
        host = (parsed.hostname or "").lower()
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        playlist_id = (query.get("list") or [""])[0].strip()

        if playlist_id and (
            host in {"youtu.be", "www.youtu.be"}
            or host.endswith("youtube.com")
        ):
            # A watch/share link copied while browsing a playlist should expose
            # the complete list in the UI. Individual items remain selectable.
            return urllib.parse.urlunsplit(
                (
                    "https",
                    "www.youtube.com",
                    "/playlist",
                    urllib.parse.urlencode({"list": playlist_id}),
                    "",
                )
            )

        if host in {"youtu.be", "www.youtu.be"}:
            video_id = parsed.path.strip("/").split("/", 1)[0]
            if video_id:
                query["v"] = [video_id]
                return urllib.parse.urlunsplit(
                    ("https", "www.youtube.com", "/watch", urllib.parse.urlencode(query, doseq=True), "")
                )

        if host.endswith("youtube.com") and parsed.path.startswith("/shorts/"):
            video_id = parsed.path.split("/shorts/", 1)[1].split("/", 1)[0]
            if video_id:
                query["v"] = [video_id]
                return urllib.parse.urlunsplit(
                    ("https", "www.youtube.com", "/watch", urllib.parse.urlencode(query, doseq=True), "")
                )
    except Exception:
        return value

    return value


def _is_web_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url)
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def clean_error_message(err: Exception | str) -> str:
    text = str(err or "").strip()
    lowered = text.lower()

    if isinstance(err, DownloadCancelled) or "download cancelled by user" in lowered:
        return "تم إلغاء التنزيل."
    if "video unavailable" in lowered or "is unavailable" in lowered:
        return "❌ هذا المقطع غير متوفر أو حُذف من المنصة."
    if "private video" in lowered or "sign in if you've been granted access" in lowered:
        return "🔒 هذا المحتوى خاص. اختر ملف Cookies أو سجّل الدخول في المتصفح."
    if "members-only" in lowered or "login required" in lowered or "sign in to confirm" in lowered:
        return "🔐 يتطلب هذا المحتوى تسجيل الدخول. استخدم Cookies من المتصفح."
    if "unsupported url" in lowered:
        return "❌ الرابط غير مدعوم حاليًا أو ليس رابط وسائط صالحًا."
    if "429" in text or "too many requests" in lowered:
        return "⏳ المنصة حدّت عدد الطلبات مؤقتًا. انتظر قليلًا أو استخدم Cookies/Proxy."
    if "geo" in lowered or "not available in your country" in lowered:
        return "🌍 هذا المحتوى غير متاح في منطقتك الجغرافية."
    if "404" in text or "not found" in lowered:
        return "❌ الرابط غير موجود أو القائمة خاصة."
    if any(part in lowered for part in ("network", "connection", "timed out", "temporary failure")):
        return "🌐 تعذر الاتصال بالشبكة. تحقق من الإنترنت ثم أعد المحاولة."
    if "ffmpeg" in lowered and ("not found" in lowered or "not installed" in lowered):
        return "⚙️ ملف FFmpeg المطلوب لدمج الفيديو والصوت غير موجود."

    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    text = re.sub(r"(?i)ERROR:\s*(?:\[.*?\]\s*)?", "", text)
    return text.strip() or "حدث خطأ غير متوقع أثناء معالجة الرابط."


def _common_ydl_options(proxy: str | None = None) -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "socket_timeout": 20,
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 3,
        "file_access_retries": 3,
        "concurrent_fragment_downloads": 4,
        "continuedl": True,
        "windowsfilenames": True,
    }
    if proxy and proxy.strip():
        options["proxy"] = proxy.strip()
    return options


def _apply_cookies(options: dict[str, Any], browser_cookies: str | None) -> None:
    cookie_source = (browser_cookies or "").strip()
    if not cookie_source or cookie_source == "none":
        return
    if os.path.isfile(cookie_source):
        options["cookiefile"] = cookie_source
    else:
        options["cookiesfrombrowser"] = (cookie_source,)


def validate_link(url: str, proxy: str | None = None) -> dict[str, Any]:
    normalized = clean_url(url)
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
        return {"valid": False, "reason": clean_error_message(exc)}


def auto_update_ytdlp(force: bool = False) -> dict[str, Any]:
    """Update yt-dlp in development; packaged apps update it with the app release."""
    if getattr(sys, "frozen", False):
        return {
            "updated": False,
            "reason": "bundled",
            "version": getattr(yt_dlp.version, "__version__", "unknown"),
        }

    state_path = os.path.join(os.path.expanduser("~"), ".sdn_ytdlp_update.json")
    now = time.time()
    if not force:
        try:
            with open(state_path, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            if now - float(state.get("checked_at", 0)) < 24 * 60 * 60:
                return {
                    "updated": False,
                    "reason": "recently_checked",
                    "version": getattr(yt_dlp.version, "__version__", "unknown"),
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
        )
        try:
            with open(state_path, "w", encoding="utf-8") as handle:
                json.dump({"checked_at": now, "returncode": result.returncode}, handle)
        except Exception:
            pass
        return {
            "updated": result.returncode == 0,
            "reason": "checked",
            "version": getattr(yt_dlp.version, "__version__", "unknown"),
        }
    except Exception as exc:
        return {"updated": False, "reason": clean_error_message(exc)}


def parse_time_to_seconds(time_text: str | None) -> int | None:
    if not time_text:
        return None
    try:
        parts = [int(part) for part in time_text.strip().split(":")]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 1:
            return parts[0]
    except Exception:
        pass
    return None


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
        normalized = clean_url(url)
        if not _is_web_url(normalized):
            raise ValueError("أدخل رابطًا صالحًا يبدأ بـ http:// أو https://")

        ydl_options = _common_ydl_options(proxy)
        ydl_options.update(
            {
                "extract_flat": "in_playlist",
                "ffmpeg_location": self.ffmpeg_path,
            }
        )
        _apply_cookies(ydl_options, browser_cookies)

        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(normalized, download=False)

        if not info:
            raise RuntimeError("تعذر جلب معلومات الرابط. تحقق من الرابط ثم أعد المحاولة.")

        video_options, audio_options = build_download_options()
        entries = info.get("entries")
        is_playlist = info.get("_type") in {"playlist", "multi_video"} or isinstance(entries, (list, tuple))

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
    ) -> dict[str, Any]:
        normalized = clean_url(url)
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
                f"%(playlist_index)03d - %(title).160B [%(id)s] [{quality_tag}] [{run_token}].%(ext)s",
            )
        else:
            template = os.path.join(
                save_dir,
                f"%(title).180B [%(id)s] [{quality_tag}] [{run_token}].%(ext)s",
            )

        captured_files: list[str] = []
        captured_lock = threading.Lock()
        requested_count = len(selected_indices) if selected_indices else int(option.get("playlist_count") or 0)

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

            if status == "finished":
                capture_path(data.get("filename") or info_dict.get("filepath") or info_dict.get("_filename"))
                if status_callback:
                    status_callback("جاري معالجة ودمج الملف عبر FFmpeg...")
                return

            if status != "downloading" or not progress_callback:
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
            if data.get("status") == "finished":
                info_dict = data.get("info_dict") or {}
                capture_path(info_dict.get("filepath") or info_dict.get("_filename"))

        ydl_options = _common_ydl_options(option.get("proxy"))
        ydl_options.update(
            {
                "format": format_id,
                "outtmpl": template,
                "progress_hooks": [ydl_progress_hook],
                "postprocessor_hooks": [postprocessor_hook],
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

        _apply_cookies(ydl_options, browser_cookies)

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

        try:
            with yt_dlp.YoutubeDL(ydl_options) as ydl:
                info = ydl.extract_info(url, download=True)
        except DownloadCancelled:
            raise
        except Exception as exc:
            if self._cancel_event.is_set():
                raise DownloadCancelled("Download cancelled by user") from exc
            raise RuntimeError(clean_error_message(exc)) from exc

        if not info and not captured_files:
            raise RuntimeError("فشل التنزيل ولم تُنتج المنصة أي ملف.")

        # Post-processing hooks can omit the final path on some extractors. The
        # unique run token makes this fallback deterministic and safe.
        if not captured_files:
            for candidate in glob.glob(os.path.join(save_dir, "**", f"*{run_token}*"), recursive=True):
                capture_path(candidate)

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
        if final_files and (trim_start or trim_end):
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

    def _trim_file(self, file_path: str, trim_start: str | None, trim_end: str | None) -> None:
        base, ext = os.path.splitext(file_path)
        trimmed_path = f"{base}.trimmed{ext}"
        command = [self.ffmpeg_path, "-y"]
        if trim_start:
            command.extend(["-ss", str(trim_start)])
        command.extend(["-i", file_path])
        if trim_end:
            command.extend(["-to", str(trim_end)])
        command.extend(["-map", "0", "-c", "copy", trimmed_path])
        try:
            completed = subprocess.run(command, capture_output=True, timeout=600)
            if completed.returncode == 0 and os.path.isfile(trimmed_path) and os.path.getsize(trimmed_path) > 0:
                os.replace(trimmed_path, file_path)
            elif os.path.exists(trimmed_path):
                os.remove(trimmed_path)
        except Exception:
            try:
                if os.path.exists(trimmed_path):
                    os.remove(trimmed_path)
            except Exception:
                pass
