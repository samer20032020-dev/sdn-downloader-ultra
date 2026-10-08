@echo off
chcp 65001 > NUL
title SDN Downloader Ultra
echo Starting SDN Downloader Ultra...
pythonw "%~dp0main.py"
if errorlevel 1 (
    python "%~dp0main.py"
)
exit
