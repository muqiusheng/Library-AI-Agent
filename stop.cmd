@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launcher.ps1" -Action Stop %*
set "bookpath_exit=%errorlevel%"
if not "%bookpath_exit%"=="0" pause
exit /b %bookpath_exit%
