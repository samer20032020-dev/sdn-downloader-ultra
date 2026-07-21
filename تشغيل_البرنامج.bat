@echo off
chcp 65001 > NUL
title برنامج SDN دوانلودر - SDN Downloader Pro
echo جاري تشغيل برنامج SDN...
start "" pythonw "%~dp0main.py"
exit
