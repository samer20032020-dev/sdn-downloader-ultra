import os
import sys
import shutil
import subprocess
import re
import urllib.parse
import yt_dlp

def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(base, 'ffmpeg.exe')
    if os.path.exists(candidate):
        return candidate

    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if ffmpeg_exe and os.path.exists(ffmpeg_exe):
            return ffmpeg_exe
    except Exception:
        pass

    return shutil.which('ffmpeg') or 'ffmpeg'

def clean_url(url):
    url = (url or '').strip()
    if 'youtu.be/' in url:
        part = url.split('youtu.be/')[1].split('?')[0].split('/')[0]
        return f'https://www.youtube.com/watch?v={part}'
    if 'youtube.com/shorts/' in url:
        part = url.split('/shorts/')[1].split('?')[0].split('/')[0]
        return f'https://www.youtube.com/watch?v={part}'
    return url

def clean_error_message(err):
    err_str = str(err)
    if 'video unavailable' in err_str.lower() or 'is unavailable' in err_str.lower():
        return '❌ هذا المقطع لم يعد متوفر في يوتيوب.'
    if 'private video' in err_str.lower() or "sign in if you've been granted access" in err_str.lower():
        return '🔒 هذا المقطع خاص.'
    if '404' in err_str or 'not found' in err_str.lower():
        return '🔒 هذه القائمة خاصة بك في يوتيوب أو غير موجودة.'
    if 'network' in err_str.lower() or 'connection' in err_str.lower() or 'timed out' in err_str.lower():
        return '🌐 تعذر الاتصال بالشبكة. يرجى التحقق من اتصال الإنترنت.'
    err_str = re.sub(r'ERROR:\s*\[.*?\]\s*', '', err_str)
    return err_str.strip()

def validate_link(url, proxy=None):
    url = clean_url(url)
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'nocheckcertificate': True,
        'socket_timeout': 10,
    }
    if proxy:
        ydl_opts['proxy'] = proxy
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return {'valid': False, 'reason': 'تعذر الوصول للرابط أو المنصة غير مدعومة'}
            title = info.get('title') or 'مقطع فيديو'
            platform = info.get('extractor_key') or 'منصة غير معروفة'
            return {
                'valid': True,
                'title': title,
                'platform': platform,
                'cleaned_url': url
            }
    except Exception as e:
        err = str(e)
        if 'Private video' in err or 'خاص' in err:
            reason = 'الفيديو خاص (Private)'
        elif 'unavailable' in err or 'محذوف' in err:
            reason = 'الفيديو غير متاح أو محذوف'
        elif 'Geo' in err or 'country' in err:
            reason = 'الفيديو محظور في منطقتك الجغرافية'
        else:
            reason = clean_error_message(err) or 'فشل فحص الرابط'
        return {'valid': False, 'reason': reason}

def auto_update_ytdlp():
    try:
        if not getattr(sys, 'frozen', False):
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-U', 'yt-dlp'], capture_output=True)
    except Exception:
        pass

def parse_time_to_seconds(t_str):
    if not t_str:
        return None
    try:
        parts = list(map(int, t_str.strip().split(':')))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 1:
            return parts[0]
    except Exception:
        pass
    return None

def format_duration(seconds):
    if not seconds:
        return 'غير معروف'
    try:
        sec = int(seconds)
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f'{h:02d}:{m:02d}:{s:02d}'
        return f'{m:02d}:{s:02d}'
    except Exception:
        return 'غير معروف'

def format_bytes(bytes_num):
    if not bytes_num:
        return ''
    try:
        b = float(bytes_num)
        if b < 1024:
            return f'{b:.0f} B'
        elif b < 1024 * 1024:
            return f'{b / 1024:.1f} KB'
        elif b < 1024 * 1024 * 1024:
            return f'{b / (1024 * 1024):.1f} MB'
        else:
            return f'{b / (1024 * 1024 * 1024):.2f} GB'
    except Exception:
        return ''

def get_format_size(f, duration=None):
    fs = f.get('filesize') or f.get('filesize_approx')
    if fs:
        return format_bytes(fs)
    tbr = f.get('tbr')
    if tbr and duration:
        est = (tbr * 1000 / 8) * duration
        return format_bytes(est)
    return ''

class MediaDownloader:
    def __init__(self):
        self.ffmpeg_path = get_ffmpeg_path()

    def fetch_info(self, url, browser_cookies='none', proxy=None):
        url = clean_url(url)
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'nocheckcertificate': True,
            'ffmpeg_location': self.ffmpeg_path,
        }
        if proxy:
            ydl_opts['proxy'] = proxy
        if browser_cookies and browser_cookies != 'none':
            if os.path.exists(browser_cookies):
                ydl_opts['cookiefile'] = browser_cookies
            else:
                ydl_opts['cookiesfrombrowser'] = (browser_cookies,)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise Exception('تعذر جلب معلومات الرابط. يُرجى التحقق من الرابط.')

            is_pl = info.get('_type') == 'playlist' or ('entries' in info and len(info['entries']) > 1)
            
            if is_pl:
                entries = info.get('entries', [])
                items = []
                for idx, entry in enumerate(entries, 1):
                    if not entry:
                        continue
                    entry_url = entry.get('url') or entry.get('webpage_url') or f'https://www.youtube.com/watch?v={entry.get("id")}'
                    items.append({
                        'index': idx,
                        'title': entry.get('title') or f'فيديو {idx}',
                        'url': entry_url,
                        'duration': format_duration(entry.get('duration')),
                        'thumbnail': entry.get('thumbnail') or f'https://i.ytimg.com/vi/{entry.get("id")}/hqdefault.jpg',
                        'selected': True,
                    })

                v_opts = [
                    {'label': '🎬 أفضل جودة فائقة مدعومة (8K / 4K / 2K / 1080p)', 'format_id': 'bestvideo+bestaudio/best', 'ext': 'mp4', 'type': 'video', 'size_str': 'أعلى جودة'},
                    {'label': '🎥 جودة 4K Ultra HD (2160p MP4)', 'format_id': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]/best', 'ext': 'mp4', 'type': 'video', 'size_str': '2160p'},
                    {'label': '📺 جودة 2K Quad HD (1440p MP4)', 'format_id': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]/best', 'ext': 'mp4', 'type': 'video', 'size_str': '1440p'},
                    {'label': '💻 جودة عالية جداً Full HD (1080p MP4)', 'format_id': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best', 'ext': 'mp4', 'type': 'video', 'size_str': '1080p'},
                    {'label': '📱 جودة عالية HD (720p MP4)', 'format_id': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best', 'ext': 'mp4', 'type': 'video', 'size_str': '720p'},
                    {'label': '⚙️ جودة متوسطة SD (480p MP4)', 'format_id': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best', 'ext': 'mp4', 'type': 'video', 'size_str': '480p'},
                    {'label': '⚡ جودة منخفضة (360p MP4)', 'format_id': 'bestvideo[height<=360]+bestaudio/best[height<=360]/best', 'ext': 'mp4', 'type': 'video', 'size_str': '360p'},
                    {'label': '📉 جودة اقتصادية جداً (240p / 144p MP4)', 'format_id': 'bestvideo[height<=240]+bestaudio/best[height<=240]/best', 'ext': 'mp4', 'type': 'video', 'size_str': '240p'},
                ]
                a_opts = [
                    {'label': '🎵 صوت نقي عالي الجودة (320 kbps MP3)', 'format_id': 'bestaudio/best', 'ext': 'mp3', 'type': 'audio', 'quality': '320', 'size_str': '320k'},
                    {'label': '🎧 صوت متوازن ممتازة (256 kbps MP3)', 'format_id': 'bestaudio/best', 'ext': 'mp3', 'type': 'audio', 'quality': '256', 'size_str': '256k'},
                    {'label': '🎼 صوت قياسي ممتاز (192 kbps MP3)', 'format_id': 'bestaudio/best', 'ext': 'mp3', 'type': 'audio', 'quality': '192', 'size_str': '192k'},
                    {'label': '🔊 صوت متوسط الجودة (128 kbps MP3)', 'format_id': 'bestaudio/best', 'ext': 'mp3', 'type': 'audio', 'quality': '128', 'size_str': '128k'},
                    {'label': '💾 صوت اقتصادي صغير (64 kbps MP3)', 'format_id': 'bestaudio/best', 'ext': 'mp3', 'type': 'audio', 'quality': '64', 'size_str': '64k'},
                    {'label': '🎶 صوت M4A/AAC الأصلي من السيرفر', 'format_id': 'bestaudio[ext=m4a]/bestaudio/best', 'ext': 'm4a', 'type': 'audio', 'quality': '256', 'size_str': 'M4A'},
                ]
                return {
                    'is_playlist': True,
                    'title': info.get('title') or 'قائمة تشغيل',
                    'uploader': info.get('uploader') or info.get('channel') or info.get('extractor_key') or 'قناة',
                    'entry_count': len(items),
                    'items': items,
                    'video_options': v_opts,
                    'audio_options': a_opts,
                    'cleaned_url': url,
                }
            else:
                duration_sec = info.get('duration')
                duration_str = format_duration(duration_sec)
                thumb = info.get('thumbnail') or f'https://i.ytimg.com/vi/{info.get("id")}/hqdefault.jpg'

                v_opts = [
                    {'label': '🎬 أفضل جودة فائقة مدعومة (8K / 4K / 2K / 1080p)', 'format_id': 'bestvideo+bestaudio/best', 'ext': 'mp4', 'type': 'video', 'size_str': 'أعلى جودة'},
                    {'label': '🎥 جودة 4K Ultra HD (2160p MP4)', 'format_id': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]/best', 'ext': 'mp4', 'type': 'video', 'size_str': '2160p'},
                    {'label': '📺 جودة 2K Quad HD (1440p MP4)', 'format_id': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]/best', 'ext': 'mp4', 'type': 'video', 'size_str': '1440p'},
                    {'label': '💻 جودة عالية جداً Full HD (1080p MP4)', 'format_id': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best', 'ext': 'mp4', 'type': 'video', 'size_str': '1080p'},
                    {'label': '📱 جودة عالية HD (720p MP4)', 'format_id': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best', 'ext': 'mp4', 'type': 'video', 'size_str': '720p'},
                    {'label': '⚙️ جودة متوسطة SD (480p MP4)', 'format_id': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best', 'ext': 'mp4', 'type': 'video', 'size_str': '480p'},
                    {'label': '⚡ جودة منخفضة (360p MP4)', 'format_id': 'bestvideo[height<=360]+bestaudio/best[height<=360]/best', 'ext': 'mp4', 'type': 'video', 'size_str': '360p'},
                    {'label': '📉 جودة اقتصادية جداً (240p / 144p MP4)', 'format_id': 'bestvideo[height<=240]+bestaudio/best[height<=240]/best', 'ext': 'mp4', 'type': 'video', 'size_str': '240p'},
                ]
                a_opts = [
                    {'label': '🎵 صوت نقي عالي الجودة (320 kbps MP3)', 'format_id': 'bestaudio/best', 'ext': 'mp3', 'type': 'audio', 'quality': '320', 'size_str': '320k'},
                    {'label': '🎧 صوت متوازن ممتازة (256 kbps MP3)', 'format_id': 'bestaudio/best', 'ext': 'mp3', 'type': 'audio', 'quality': '256', 'size_str': '256k'},
                    {'label': '🎼 صوت قياسي ممتاز (192 kbps MP3)', 'format_id': 'bestaudio/best', 'ext': 'mp3', 'type': 'audio', 'quality': '192', 'size_str': '192k'},
                    {'label': '🔊 صوت متوسط الجودة (128 kbps MP3)', 'format_id': 'bestaudio/best', 'ext': 'mp3', 'type': 'audio', 'quality': '128', 'size_str': '128k'},
                    {'label': '💾 صوت اقتصادي صغير (64 kbps MP3)', 'format_id': 'bestaudio/best', 'ext': 'mp3', 'type': 'audio', 'quality': '64', 'size_str': '64k'},
                    {'label': '🎶 صوت M4A/AAC الأصلي من السيرفر', 'format_id': 'bestaudio[ext=m4a]/bestaudio/best', 'ext': 'm4a', 'type': 'audio', 'quality': '256', 'size_str': 'M4A'},
                ]
                return {
                    'is_playlist': False,
                    'title': info.get('title') or 'فيديو بدون عنوان',
                    'uploader': info.get('uploader') or info.get('channel') or 'غير معروف',
                    'duration': duration_str,
                    'thumbnail': thumb,
                    'extractor': info.get('extractor_key') or 'منصة غير معروفة',
                    'video_options': v_opts,
                    'audio_options': a_opts,
                    'cleaned_url': url,
                }

    def download(self, url, option, save_dir, progress_callback=None, status_callback=None, browser_cookies='none'):
        url = clean_url(url)
        os.makedirs(save_dir, exist_ok=True)

        is_audio = option.get('type') == 'audio'
        format_id = option.get('format_id', 'best')

        out_tmpl = os.path.join(save_dir, '%(title)s.%(ext)s')

        def ydl_progress_hook(d):
            if not progress_callback:
                return
            status = d.get('status')
            if status == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                pct = (downloaded / total * 100) if total > 0 else 0
                spd = d.get('speed', 0)
                eta = d.get('eta', 0)

                progress_callback({
                    'status': 'downloading',
                    'percent': pct,
                    'downloaded_str': format_bytes(downloaded),
                    'total_str': format_bytes(total),
                    'speed_str': f'{format_bytes(spd)}/ثانية' if spd else 'جاري البدء...',
                    'eta_str': f'{eta} ثانية' if eta else ''
                })
            elif status == 'finished':
                if status_callback:
                    status_callback('جاري المعالجة والدمج عبر ffmpeg...')

        ydl_opts = {
            'format': format_id,
            'outtmpl': out_tmpl,
            'progress_hooks': [ydl_progress_hook],
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': self.ffmpeg_path,
        }
        if not is_audio:
            ydl_opts['merge_output_format'] = 'mp4'

        if option.get('proxy'):
            ydl_opts['proxy'] = option['proxy']

        if browser_cookies and browser_cookies != 'none':
            if os.path.exists(browser_cookies):
                ydl_opts['cookiefile'] = browser_cookies
            else:
                ydl_opts['cookiesfrombrowser'] = (browser_cookies,)

        if is_audio:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': option.get('quality', '320'),
            }]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            saved_file = ydl.prepare_filename(info) if info else None
            if is_audio and saved_file:
                saved_file = os.path.splitext(saved_file)[0] + '.mp3'

        trim_start = option.get('trim_start')
        trim_end = option.get('trim_end')
        if saved_file and os.path.exists(saved_file) and (trim_start or trim_end):
            if status_callback:
                status_callback('جاري اقتطاع الفيديو بالزمن المحدد عبر FFmpeg...')
            base_dir_path = os.path.dirname(saved_file)
            base_name = os.path.basename(saved_file)
            trimmed_file = os.path.join(base_dir_path, 'trimmed_' + base_name)

            cmd = [self.ffmpeg_path, '-y']
            if trim_start:
                cmd.extend(['-ss', trim_start])
            if trim_end:
                cmd.extend(['-to', trim_end])
            cmd.extend(['-i', saved_file, '-c', 'copy', trimmed_file])
            try:
                subprocess.run(cmd, capture_output=True)
                if os.path.exists(trimmed_file):
                    os.replace(trimmed_file, saved_file)
            except Exception:
                pass

        return saved_file
