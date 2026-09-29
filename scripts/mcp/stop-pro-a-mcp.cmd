@echo off
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0stop-pro-a-mcp.ps1"
exit /b %errorlevel%
