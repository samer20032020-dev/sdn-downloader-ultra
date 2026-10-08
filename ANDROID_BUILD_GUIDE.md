# دليل بناء تطبيق Android

النسخة الرسمية تستخدم Capacitor مع محرك تنزيل Android الأصلي.

## المتطلبات

- Node.js 22 أو أحدث مع npm.
- Java JDK 21 أو أحدث.
- Android SDK مع API وBuild Tools 35.

## البناء المحلي

من جذر المشروع:

```bash
npm ci
python build_and_upload_apk.py --no-upload
```

تقوم الأداة تلقائيًا بما يلي:

1. مزامنة رقم الإصدار من `version.py` مع `android/app/build.gradle` و`ui/index.html`.
2. مزامنة `ui/index.html` مع نسختي الويب وأندرويد.
3. بناء APK ونسخه إلى `dist/SDN_Downloader_Ultra.apk`.

لحفظ APK مباشرة في إصدار GitHub الحالي بعد البناء، احذف الخيار `--no-upload`.

## ملاحظة التوقيع

- بدون ملف `android/keystore.properties` يُبنى APK بتوقيع debug (يحافظ على ترقية التثبيت السابق على نفس الجهاز).
- للتوقيع الرسمي الثابت، أنشئ مفتاحًا واحفظه خارج المستودع، ثم أضف `android/keystore.properties` بالشكل التالي وسيُستخدم تلقائيًا:

```properties
storeFile=C:/secure/sdn-release.keystore
storePassword=********
keyAlias=sdn
keyPassword=********
```

عند تغيير مفتاح التوقيع يجب على المستخدمين إزالة تثبيت النسخة القديمة مرة واحدة ثم تثبيت النسخة الجديدة.

## ميزات أندرويد المدمجة

- حفظ التنزيلات في `Download/SDN Downloader` عبر MediaStore (متوافق مع Android 10 وأحدث) بدون مشاكل الصلاحيات.
- عند اختيار مجلد عبر SAF يتم نسخ الملفات النهائية إليه فعليًا.
- خدمة أمامية (Foreground Service) مع إشعار تقدم وإبقاء التنزيل حيًا عند إغلاق الواجهة.
- دعم الكوكيز من ملف cookies.txt، والترجمة، وحد السرعة، والقص، والبروكسي، ووضع Turbo.
- تحديث التطبيق: تنزيل APK مع التحقق من SHA-256 ثم فتح مثبّت الحزمة تلقائيًا.
