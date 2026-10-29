@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title SDN Build All - إصدار تلقائي كامل

echo ============================================
echo   SDN Downloader Ultra - بناء تلقائي كامل
echo ============================================
echo.

REM ---------------------------------------------
REM 1. التحقق من الأدوات الأساسية
REM ---------------------------------------------
echo [1/6] التحقق من الأدوات الأساسية...

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python غير مثبت!
    pause
    exit /b 1
)

where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller غير مثبت، جاري التثبيت...
    pip install pyinstaller
)

echo [OK] الأدوات الأساسية موجودة.

REM ---------------------------------------------
REM 2. تحديث رقم الإصدار في جميع الملفات
REM ---------------------------------------------
echo.
echo [2/6] تحديث رقم الإصدار في جميع الملفات...

python bump_version.py --patch
if errorlevel 1 (
    echo [ERROR] فشل تحديث رقم الإصدار!
    pause
    exit /b 1
)

echo [OK] تم تحديث رقم الإصدار.

REM ---------------------------------------------
REM 3. بناء النسخة المحمولة (Standalone .exe)
REM ---------------------------------------------
echo.
echo [3/6] بناء النسخة المحمولة (SDN_Downloader_Standalone.exe)...

pyinstaller SDN_Downloader_Standalone.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] فشل بناء النسخة المحمولة!
    pause
    exit /b 1
)

echo [OK] تم بناء النسخة المحمولة.

REM ---------------------------------------------
REM 4. بناء المثبت GUI (.exe)
REM ---------------------------------------------
echo.
echo [4/6] بناء المثبت GUI (installer_gui)...

pyinstaller installer_gui.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] فشل بناء المثبت GUI!
    pause
    exit /b 1
)

echo [OK] تم بناء المثبت GUI.

REM ---------------------------------------------
REM 5. بناء تطبيق أندرويد (.apk) - إذا كانت الأدوات متوفرة
REM ---------------------------------------------
echo.
echo [5/6] بناء تطبيق أندرويد (SDN_Downloader_Ultra.apk)...

where node >nul 2>&1
where java >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Node.js أو Java غير موجود، سيتم تخطي بناء أندرويد.
    echo [INFO] لبناء أندرويد يحتاج: Node.js, Java JDK 21, Android SDK
) else (
    python build_and_upload_apk.py --no-upload
    if errorlevel 1 (
        echo [WARNING] فشل بناء أندرويد، قد تحتاج Android SDK.
    ) else (
        echo [OK] تم بناء تطبيق أندرويد.
    )
)

REM ---------------------------------------------
REM 6. نسخ الملفات المبنية إلى مجلد dist
REM ---------------------------------------------
echo.
echo [6/6] نسخ الملفات إلى مجلد dist...

if not exist dist mkdir dist

REM نسخ النسخة المحمولة
if exist dist\SDN_Downloader_Standalone.exe del dist\SDN_Downloader_Standalone.exe /q
if exist ".\dist\SDN_Downloader_Standalone.exe" copy ".\dist\SDN_Downloader_Standalone.exe" ".\dist\" /y

REM نسخ المثبت
if exist dist\SDN_Downloader_Setup.exe del dist\SDN_Downloader_Setup.exe /q

REM عرض الملفات المبنية
echo.
echo ============================================
echo   اكتمل البناء بنجاح!
echo ============================================
echo.
echo الملفات في مجلد dist:
dir dist\*.exe dist\*.apk /b 2>nul
echo.
echo رقم الإصدار الحالي:
type version.py | findstr APP_VERSION
echo.

REM ---------------------------------------------
REM 7. رفع إلى GitHub (اختياري)
REM ---------------------------------------------
set /p upload="هل تريد رفع التحديث إلى GitHub الآن؟ (نعم/لا): "
if /i "!upload!"=="نعم" (
    echo.
    echo [7/7] الرفع إلى GitHub...
    python git_push.py
    if errorlevel 1 (
        echo [WARNING] فشل الرفع إلى GitHub، لكن البناء اكتمل محلياً.
    ) else (
        echo [OK] تم الرفع إلى GitHub بنجاح.
    )
)

echo.
echo ============================================
echo   تم كل شيء!
echo ============================================
pause
