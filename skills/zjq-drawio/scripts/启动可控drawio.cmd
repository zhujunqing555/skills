@echo off
chcp 65001 >nul
powershell.exe -NoProfile -File "%~dp0launcher.ps1" %*
pause
