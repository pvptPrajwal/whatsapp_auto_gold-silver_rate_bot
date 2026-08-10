@echo off
setlocal
cd /d "%~dp0"

echo =====================================================
echo   GoldSilver Rate Bot V8 - Desktop EXE Builder
echo =====================================================

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Run install.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :error

if exist "build" rmdir /s /q "build"
if exist "dist\GoldSilverRateBot" rmdir /s /q "dist\GoldSilverRateBot"

pyinstaller --noconfirm --clean --onedir --windowed ^
  --name GoldSilverRateBot ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --collect-all selenium ^
  --collect-all webdriver_manager ^
  --collect-all certifi ^
  desktop_main.py
if errorlevel 1 goto :error

if not exist "dist\GoldSilverRateBot\data" mkdir "dist\GoldSilverRateBot\data"
copy /y "README.md" "dist\GoldSilverRateBot\README.md" >nul
copy /y "VERSION.txt" "dist\GoldSilverRateBot\VERSION.txt" >nul

echo.
echo =====================================================
echo   DESKTOP EXE BUILD COMPLETE
echo =====================================================
echo Output:
echo   %CD%\dist\GoldSilverRateBot\GoldSilverRateBot.exe
echo.
echo To preserve your WhatsApp login/settings, copy your existing data folder
  echo into dist\GoldSilverRateBot\data before first EXE use.
pause
exit /b 0

:error
echo.
echo [ERROR] EXE build failed. Copy the error above for troubleshooting.
pause
exit /b 1
