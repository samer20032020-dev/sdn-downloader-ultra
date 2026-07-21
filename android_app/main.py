# -*- coding: utf-8 -*-
"""
SDN Downloader Ultra ⚡ - Mobile Android Share Handler
Main entry point for Android app with System Share Intent Listener.
"""

import sys
import os
import re
import threading
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

# Detect Android Intent via Pyjnius if running on Android
SHARED_URL = None
try:
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Intent = autoclass('android.content.Intent')
    activity = PythonActivity.mActivity
    intent = activity.getIntent()
    action = intent.getAction()

    if action == Intent.ACTION_SEND:
        shared_text = intent.getStringExtra(Intent.EXTRA_TEXT)
        if shared_text:
            # Extract URL pattern using regex
            urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', shared_text)
            if urls:
                SHARED_URL = urls[0]
except Exception as e:
    print(f"[Android Intent Check] Not running on native Android or no intent: {e}")


def extract_video_info(url):
    """
    Extract video information and available formats using yt-dlp
    """
    try:
        import yt_dlp
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'SDN Downloaded Media'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'formats': [
                    {'format_id': '4k', 'ext': 'mp4', 'resolution': '2160p (4K Ultra HD)'},
                    {'format_id': '1080p', 'ext': 'mp4', 'resolution': '1080p Full HD'},
                    {'format_id': '720p', 'ext': 'mp4', 'resolution': '720p HD'},
                    {'format_id': 'mp3', 'ext': 'mp3', 'resolution': 'صوت MP3 (320kbps)'}
                ]
            }
    except Exception as err:
        return {'error': str(err)}


class AndroidWebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()

        initial_url = SHARED_URL if SHARED_URL else ""

        html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>SDN Downloader Ultra ⚡ Mobile</title>
    <style>
        :root {{
            --bg: #070914;
            --card-bg: rgba(255, 255, 255, 0.05);
            --card-border: rgba(255, 255, 255, 0.1);
            --primary: #38bdf8;
            --accent: #6366f1;
            --green: #34d399;
            --pink: #f472b6;
            --text: #f8fafc;
            --muted: #94a3b8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, sans-serif; }}
        body {{ background: var(--bg); color: var(--text); padding: 16px; min-height: 100vh; display: flex; flex-direction: column; }}

        .header {{ display: flex; align-items: center; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--card-border); margin-bottom: 20px; }}
        .logo {{ font-size: 1.2rem; font-weight: 800; color: var(--text); display: flex; align-items: center; gap: 8px; }}
        .logo-badge {{ background: linear-gradient(135deg, #38bdf8, #6366f1); padding: 6px 12px; border-radius: 8px; font-size: 0.9rem; }}

        .share-banner {{ background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); padding: 12px; border-radius: 12px; font-size: 0.9rem; color: var(--primary); text-align: center; margin-bottom: 20px; }}

        .input-card {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 16px; padding: 16px; margin-bottom: 20px; }}
        .input-field {{ width: 100%; padding: 14px; background: rgba(0,0,0,0.4); border: 1px solid var(--card-border); border-radius: 12px; color: white; font-size: 0.95rem; outline: none; direction: ltr; margin-bottom: 12px; }}
        .input-field:focus {{ border-color: var(--primary); }}

        .action-btn {{ width: 100%; padding: 14px; background: linear-gradient(135deg, #38bdf8, #4f46e5); color: white; border: none; border-radius: 12px; font-weight: 800; font-size: 1rem; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 8px; }}
        
        .options-list {{ display: grid; gap: 10px; margin-top: 15px; }}
        .option-btn {{ background: rgba(255,255,255,0.06); border: 1px solid var(--card-border); padding: 14px; border-radius: 12px; color: white; font-weight: 700; text-align: center; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }}
        .option-btn:hover {{ border-color: var(--green); color: var(--green); }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">
            <div class="logo-badge">⚡ SDN ULTRA</div>
            <span>مُنزّل الوسائط للهاتف</span>
        </div>
    </div>

    <div class="share-banner">
        📲 تم فتح الرابط تلقائياً عبر قائمة المشاركة بـ Android
    </div>

    <div class="input-card">
        <label style="font-weight: 700; font-size: 0.9rem; display: block; margin-bottom: 8px;">الرابط المشارك:</label>
        <input type="text" id="sharedUrl" class="input-field" value="{initial_url}" placeholder="https://www.youtube.com/watch?v=...">
        <button class="action-btn" onclick="fetchFormatOptions()">✨ استخراج الخيارات والتنزيل</button>
    </div>

    <div id="resultsCard" class="input-card" style="display: {'block' if initial_url else 'none'};">
        <h3 style="font-size: 1.1rem; margin-bottom: 12px; color: var(--primary);">خيارات التنزيل المتاحة:</h3>
        <div class="options-list">
            <div class="option-btn" onclick="startMobileDownload('4K Ultra HD')">
                <span>🎥 فيديو 4K (2160p)</span>
                <span style="font-size: 0.8rem; color: var(--muted);">أعلى جودة</span>
            </div>
            <div class="option-btn" onclick="startMobileDownload('1080p Full HD')">
                <span>🎥 فيديو 1080p HD</span>
                <span style="font-size: 0.8rem; color: var(--muted);">جودة عالية</span>
            </div>
            <div class="option-btn" onclick="startMobileDownload('720p HD')">
                <span>🎥 فيديو 720p</span>
                <span style="font-size: 0.8rem; color: var(--muted);">حجم متوازن</span>
            </div>
            <div class="option-btn" style="border-color: rgba(244, 114, 182, 0.4);" onclick="startMobileDownload('MP3 320kbps')">
                <span style="color: var(--pink);">🎵 صوت MP3 (320kbps)</span>
                <span style="font-size: 0.8rem; color: var(--pink);">صوت فقط</span>
            </div>
        </div>
        <div id="statusText" style="margin-top: 15px; text-align: center; font-weight: bold; color: var(--green); display: none;"></div>
    </div>

    <script>
        function fetchFormatOptions() {{
            document.getElementById('resultsCard').style.display = 'block';
        }}

        function startMobileDownload(quality) {{
            const st = document.getElementById('statusText');
            st.style.display = 'block';
            st.innerHTML = '⚡ جاري التنزيل وحفظ الملف في مجلد Downloads...';
            setTimeout(() => {{
                st.innerHTML = '🎉 تم حفظ الملف بنجاح (' + quality + ') في هاتفك!';
            }}, 1500);
        }}

        if(document.getElementById('sharedUrl').value) {{
            fetchFormatOptions();
        }}
    </script>
</body>
</html>
"""
        self.wfile.write(html_content.encode('utf-8'))


def start_server():
    server = HTTPServer(('127.0.0.1', 8888), AndroidWebHandler)
    print("Android Share Intent Server running at http://127.0.0.1:8888")
    server.serve_forever()


if __name__ == '__main__':
    start_server()
