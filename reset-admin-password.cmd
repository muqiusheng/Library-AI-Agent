@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\reset-admin-password.ps1" %*
set "bookpath_exit=%errorlevel%"
pause
exit /b %bookpath_exit%
