@echo off
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"

if errorlevel 1 (
  echo.
  echo Failed to start the project.
  pause
)
