@echo off
setlocal
cd /d "%~dp0"
title GoldSilverBot V3 - Install

echo =====================================================
echo   GoldSilverBot V3 - One-time Installation
echo =====================================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py"
) else (
    where python >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python was not found.
        echo Install Python 3.10 or newer and select "Add Python to PATH".
        pause
        exit /b 1
    )
    set "PY=python"
)

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js was not found.
    echo Install Node.js 18 or newer from the official Node.js website, then run this file again.
    pause
    exit /b 1
)

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] npm was not found. Reinstall Node.js with npm included.
    pause
    exit /b 1
)

echo [1/4] Creating isolated Python environment...
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv
    if errorlevel 1 goto :fail
) else (
    echo       Existing .venv found. Reusing it.
)

echo.
echo [2/4] Updating pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo.
echo [3/4] Installing Python packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo.
echo [4/4] Installing WhatsApp background service...
pushd whatsapp_service
call npm install
if errorlevel 1 (
    popd
    goto :fail
)
popd

echo.
echo =====================================================
echo   INSTALLATION COMPLETE
echo =====================================================
echo Run: run.bat
echo.
pause
exit /b 0

:fail
echo.
echo [ERROR] Installation did not complete.
echo Copy the error shown above and send it for troubleshooting.
pause
exit /b 1
