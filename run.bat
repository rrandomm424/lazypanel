@echo off
cd /d "%~dp0"
echo ==============================
echo   LazyPanel
echo   1 - 原版 (tkinter, 9MB)
echo   2 - Web版 (HTML/CSS, 35MB)
echo ==============================
choice /c 12 /n /m "选择版本 (1/2): "
if errorlevel 2 start "" lazypanel_web.exe
if errorlevel 1 start "" lazypanel.exe
