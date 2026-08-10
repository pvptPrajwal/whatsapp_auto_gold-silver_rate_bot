@echo off
cd /d "%~dp0"
title GoldSilverBot V3

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Installation not found.
    echo Run install.bat first.
    pause
    exit /b 1
)

if not exist "whatsapp_service\node_modules" (
    echo [ERROR] WhatsApp service packages are not installed.
    echo Run install.bat first.
    pause
    exit /b 1
)

echo Starting GoldSilverBot V3...
".venv\Scripts\python.exe" app.py

if errorlevel 1 (
    echo.
    echo The application stopped with an error.
    pause
)
