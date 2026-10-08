# إضافة المتصفح - SDN Downloader Ultra

إضافة خفيفة ترسل الرابط الحالي (أو أي رابط) مباشرة إلى برنامج **SDN Downloader Ultra** على الجهاز عبر جسر محلي آمن على المنفذ `127.0.0.1:4567`.

## آلية العمل

- ترسل الإضافة طلب `POST` إلى `http://127.0.0.1:4567/` بصيغة `{"url": "..."}`.
- البرنامج يقبل الطلبات فقط إذا كان `Origin` تابعًا لإضافة حقيقية (`chrome-extension://`, `moz-extension://`...).
- مجلد الإضافة هذا يُحزَّم تلقائيًا داخل نسخ Windows عبر `build_onefile.spec` و`build_onedir.spec`.

## التثبيت

### Chrome / Edge / Brave / Opera (Chromium)

1. افتح `chrome://extensions` (أو `edge://extensions`).
2. فعّل **وضع المطوّر** (Developer mode).
3. اضغط **Load unpacked** واختر مجلد `extension/`.

> إذا رغبت بنسخة Firefox، أعد تسمية `manifest.firefox.json` إلى `manifest.json` قبل التحميل.

### Firefox

1. افتح `about:debugging#/runtime/this-firefox`.
2. اضغط **Load Temporary Add-on** واختر `extension/manifest.firefox.json`.

## الاستخدام

- اضغط أيقونة الإضافة لفتح النافذة، ثم **إرسال إلى التطبيق**.
- أو انقر بالزر الأيمن على رابط/صفحة واختر **Send ... to SDN Downloader**.
- أو استخدم الاختصار `Alt+Shift+S` لإرسال الصفحة الحالية.

يجب أن يكون تطبيق SDN Downloader مشغّلًا على نفس الجهاز حتى تصل الروابط.
