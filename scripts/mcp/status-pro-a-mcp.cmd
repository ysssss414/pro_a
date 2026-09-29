@echo off
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0status-pro-a-mcp.ps1"
exit /b %errorlevel%
