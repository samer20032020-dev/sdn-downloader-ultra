@echo off
chcp 65001 >nul
title SDN Release Helper

echo.
echo ============================================
echo   SDN Downloader Ultra - Release Helper
echo ============================================
echo.

REM التحقق من وجود Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python غير مثبت على هذا الجهاز!
    echo.
    pause
    exit /b 1
)

REM اختيار نوع التحديث
echo اختر نوع التحديث:
echo   1. Patch (إصلاحات صغيرة) - التحديث الافتراضي
echo   2. Minor (ميزات جديدة)
echo   3. Major (تحديث كبير)
echo   4. إصدار محدد يدوياً
echo.
set /p choice="اختر رقم الخيار (1-4): "

if "%choice%"=="1" (
    python bump_version.py --patch
) else if "%choice%"=="2" (
    python bump_version.py --minor
) else if "%choice%"=="3" (
    python bump_version.py --major
) else if "%choice%"=="4" (
    set /p explicit="أدخل رقم الإصدار (مثال: 1.0.61): "
    python bump_version.py --to %explicit%
) else (
    python bump_version.py --patch
)

echo.
echo ============================================
echo   تم تحديث الإصدار في جميع الملفات
echo ============================================
echo.

REM رفع إلى GitHub
echo جاري الرفع إلى GitHub...
python git_push.py

echo.
echo ============================================
echo   اكتمل العملية بنجاح!
echo ============================================
echo.
pause
