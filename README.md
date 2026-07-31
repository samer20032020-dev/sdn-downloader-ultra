# ⚡ SDN Downloader Ultra

تطبيق عربي متكامل لتنزيل الفيديو والصوت وقوائم التشغيل على Windows وAndroid، مبني على `yt-dlp` و`FFmpeg`.

[![GitHub release](https://img.shields.io/github/v/release/samer20032020-dev/sdn-downloader-ultra?color=38bdf8&style=for-the-badge)](https://github.com/samer20032020-dev/sdn-downloader-ultra/releases/latest)
[![Platform](https://img.shields.io/badge/Platform-Android%20%7C%20Windows-6366f1?style=for-the-badge)](https://github.com/samer20032020-dev/sdn-downloader-ultra/releases/latest)

## التنزيل

| المنصة | الملف | رابط مباشر لأحدث إصدار |
|---|---|---|
| Android | `SDN_Downloader_Ultra.apk` | [تنزيل APK](https://github.com/samer20032020-dev/sdn-downloader-ultra/releases/latest/download/SDN_Downloader_Ultra.apk) |
| Windows Setup | `SDN_Downloader_Setup.exe` | [تنزيل المثبت](https://github.com/samer20032020-dev/sdn-downloader-ultra/releases/latest/download/SDN_Downloader_Setup.exe) |
| Windows Portable | `SDN_Downloader_Standalone.exe` | [تنزيل النسخة المحمولة](https://github.com/samer20032020-dev/sdn-downloader-ultra/releases/latest/download/SDN_Downloader_Standalone.exe) |

## أهم الميزات

- تنزيل فيديو واحد أكثر من مرة بجودات مختلفة أو بالجودة نفسها من دون استبدال الملفات السابقة.
- تنزيل قائمة تشغيل كاملة أو تحديد عناصر معيّنة منها.
- جودات فيديو من 144p حتى 4K وأفضل جودة متاحة، مع دمج الفيديو والصوت تلقائيًا.
- صيغ صوت MP3 بعدة معدلات، وM4A وFLAC.
- مشغل أغاني مدمج يدعم MP3 وM4A وAAC وFLAC وOGG وOPUS وWAV وWMA، مع إنشاء نسخة تشغيل MP3 مخبأة تلقائيًا عند اختلاف دعم ترميزات WebView2 من جهاز لآخر من دون تعديل الملف الأصلي.
- فحص مجلد التنزيل بكل مجلداته الفرعية، وهذا يشمل مجلدات قوائم التشغيل.
- تقدم تفصيلي، سرعة، وقت متبقٍ، تقدم كل عنصر في القائمة، وإلغاء التنزيل.
- استكمال التنزيل المتقطع وإعادة المحاولة تلقائيًا عند أخطاء الشبكة المؤقتة.
- دعم Cookies من المتصفح أو ملف Cookies للمحتوى الذي يسمح حساب المستخدم بالوصول إليه.
- فحص تحديثات تلقائي من GitHub، وتنزيل آمن لمثبت Windows مع التحقق من الملف وبصمته عند توفرها.
- محرك `yt-dlp + FFmpeg` مدمج في تطبيق Android، مع تحديث دوري لمحرك الاستخراج.
- استقبال الروابط من قائمة المشاركة في Android.

يدعم `yt-dlp` عددًا كبيرًا من المنصات. قد تتغير آليات بعض المواقع دون إشعار، لذلك يُنصح دائمًا باستخدام أحدث إصدار من التطبيق.

## التشغيل والتطوير

يتطلب إصدار Windows بيئة Python حديثة:

```powershell
python -m pip install -r requirements.txt
python main.py
```

فحص المصدر:

```powershell
python -m unittest discover -s tests -v
python -m py_compile main.py downloader.py installer_gui.py
```

بناء Windows:

```powershell
python -m PyInstaller --noconfirm --clean build_onefile.spec
python -m PyInstaller --noconfirm --clean installer_gui.spec
```

بناء Android داخل `dist/`:

```powershell
python build_and_upload_apk.py --no-upload
```

## ملاحظات

- استخدم التطبيق فقط لتنزيل محتوى تملكه أو لديك إذن بتنزيله، والتزم بشروط المنصة والقوانين المحلية.
- مكتبة Android `youtubedl-android` مرخصة بـ GPL-3.0. راجع [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- ملفات الإصدار الكبيرة لا تُحفظ في Git، بل تُرفع كأصول داخل GitHub Releases.
