@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-windows.ps1"
set "blankbox_exit=%errorlevel%"
echo.
pause
exit /b %blankbox_exit%
