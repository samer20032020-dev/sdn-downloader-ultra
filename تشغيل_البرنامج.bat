@echo off
chcp 65001 > NUL
title SDN Downloader Ultra v2.9.0
echo جاري تشغيل SDN Downloader Ultra...
pythonw "%~dp0main.py"
if errorlevel 1 (
    python "%~dp0main.py"
)
exit
