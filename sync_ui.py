# -*- coding: utf-8 -*-
"""
SDN Downloader Ultra - UI Sync Tool
ينسخ واجهة المستخدم من ui/ إلى www/ مع استبدال المتغيرات الخاصة بكل منصة
"""
import os
import sys
import shutil
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def sync_ui_to_www():
    """نسخ ui/index.html إلى www/index.html مع تعديلات منصة Capacitor"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(base_dir, 'ui', 'index.html')
    dst = os.path.join(base_dir, 'www', 'index.html')
    
    if not os.path.exists(src):
        print(f"❌ Source not found: {src}")
        return False
    
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    
    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add Capacitor-specific meta tags if not present
    if 'capacitor' not in content.lower():
        cap_meta = '\n    <meta name="capacitor" content="true">'
        if '<meta charset="UTF-8">' in content:
            content = content.replace('<meta charset="UTF-8">', '<meta charset="UTF-8">' + cap_meta)
    
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Synced: {src} → {dst}")
    return True

if __name__ == '__main__':
    sync_ui_to_www()
