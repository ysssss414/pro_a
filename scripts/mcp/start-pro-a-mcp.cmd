@echo off
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0start-pro-a-mcp.ps1"
exit /b %errorlevel%
