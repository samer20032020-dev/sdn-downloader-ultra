@echo off
chcp 65001 > NUL
title SDN v1.0.2
echo جاري تشغيل SDN...
pythonw "%~dp0main.py"
if errorlevel 1 (
    python "%~dp0main.py"
)
exit
