# 🚀 دليل رفع المشروع على GitHub وتفعيل الموقع المجاني (GitHub Pages)

تم إنشاء موقع الويب الفاخر والمستقل لبرنامحك **SDN Downloader ⚡ Ultra** في الملف الأساسي `index.html`.

تستطيع رفع هذا المشروع بالكامل إلى **GitHub** ونشر الموقع مجاناً بقليلات من الخطوات البسيطة:

---

## 📌 الخطوة 1: إنشاء مستودع جديد على GitHub
1. افتح موقع [GitHub.com](https://github.com) وقم بتسجيل الدخول.
2. انقر على زر **New** (أو أيقونة `+` أعلى اليمين ثم **New repository**).
3. اكتب اسم المستودع (مثلاً: `sdn-downloader-ultra`).
4. اختر **Public** (عام) ليكون الموقع قادراً على الاستضافة المجانية.
5. انقر على **Create repository**.

---

## 📌 الخطوة 2: رفع ملفات المشروع إلى GitHub
يمكنك استخدام إما **GitHub Desktop** أو **سطر الأوامر Terminal** أو **رفع الملفات مباشرة**:

### 💡 الطريقة الأولى: الرفع المباشر عبر الموقع (بدون برامج):
1. في صفحة المستودع الجديد على GitHub، اضغط على رابط **uploading an existing file**.
2. قم بسحب وإسقاط كافة ملفات المجلد هنا (بما في ذلك `index.html` و مجلد `assets` و `ui` و `main.py`).
3. اضغط على **Commit changes**.

---

### 💻 الطريقة الثانية: باستخدام سطر الأوامر (لو كان Git مثبتاً لديكم):
فتح سطر الأوامر في مجلد المشروع وتنفيذ الأوامر التالية:

```bash
git init
git add .
git commit -m "الإصدار الأول لبرنامج SDN Downloader مع الموقع الرسمي"
git branch -M main
git remote add origin https://github.com/USERNAME/sdn-downloader-ultra.git
git push -u origin main
```
*(ملاحظة: استبدل `USERNAME` باسم حسابك على GitHub)*.

---

## 🌐 الخطوة 3: تفعيل موقع الويب المجاني (GitHub Pages)
1. ادخل إلى مستودعك على GitHub واضغط على **Settings** (الإعدادات).
2. من القائمة الجانبية اليسرى، اختر **Pages**.
3. تحت قسم **Build and deployment**:
   - **Source**: اختر `Deploy from a branch`.
   - **Branch**: اختر فرع `main` (أو `master`) والمجلد `/ (root)`.
4. اضغط على **Save**.

🎉 خلال 1-2 دقيقة، ستحصل على رابط موقعك المباشر مثل:
`https://USERNAME.github.io/sdn-downloader-ultra/`

---

## 📁 المكونات الجاهزة في المشروع الآن:
- 🌐 `index.html`: موقع الويب الرئيسي للإنزال والمؤثرات البصرية والمحاكاة الحية.
- 🖼️ `assets/hero-preview.png`: صورة معايرة بدقة عالية للواجهة المستقبلية للبرنامج.
- ⚙️ `.nojekyll`: لتسريع وتسهيل قراءة الملفات مباشرة على GitHub Pages.
- 📱 `ANDROID_BUILD_GUIDE.md`: دليل بناء التطبيق للهواتف الذكية.
