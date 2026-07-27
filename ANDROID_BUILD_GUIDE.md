# دليل بناء تطبيق Android

لدى المشروع طريقتان لبناء تطبيق Android:

---

## الطريقة الأولى: Capacitor (مُوصى بها)

تستخدم إطار عمل Capacitor مع Gradle لتحويل محتوى الويب (`www/`) إلى تطبيق Android أصلي.

### المتطلبات
- **Node.js** و **npm**
- **Java JDK 17**
- **Android SDK** (API 34+, build-tools 34+)

### خطوات البناء

```bash
npm install
npx cap sync
cd android
./gradlew assembleDebug
```

**مخرج البناء:** `android/app/build/outputs/apk/debug/app-debug.apk`

### البناء التلقائي عبر GitHub Actions

يوجد سير عمل جاهز في `.github/workflows/build_apk.yml` لبناء التطبيق عند كل push أو release.

---

## الطريقة الثانية: Buildozer (Kivy)

تستخدم Buildozer مع Kivy لتغليف كود Python مباشرة إلى APK.

### المتطلبات
- **Buildozer** (`pip install buildozer`)
- بيئة Linux أو WSL

### خطوات البناء

```bash
cd android_app
buildozer android debug
```

---

## الطريقتان قيد التطوير

كلتا الطريقتين تعملان حالياً وموجودتان للمقارنة:
- `android/` → Capacitor (أكثر حداثة، يدعم CI/CD)
- `android_app/` → Buildozer (تطبيق Python أصلي)
