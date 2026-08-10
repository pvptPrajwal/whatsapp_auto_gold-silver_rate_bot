@echo off
setlocal
cd /d "%~dp0"

echo =====================================================
echo   GoldSilverBot V7 - Windows EXE Builder
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
if exist "dist\GoldSilverBot" rmdir /s /q "dist\GoldSilverBot"

pyinstaller --noconfirm --clean --onedir --windowed ^
  --name GoldSilverBot ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --collect-all selenium ^
  --collect-all webdriver_manager ^
  --collect-all certifi ^
  app.py
if errorlevel 1 goto :error

if not exist "dist\GoldSilverBot\data" mkdir "dist\GoldSilverBot\data"
copy /y "README.md" "dist\GoldSilverBot\README.md" >nul
copy /y "VERSION.txt" "dist\GoldSilverBot\VERSION.txt" >nul

echo.
echo =====================================================
echo   EXE BUILD COMPLETE
echo =====================================================
echo.
echo Output:
echo   %CD%\dist\GoldSilverBot\GoldSilverBot.exe
echo.
echo IMPORTANT:
echo - To preserve an existing WhatsApp login, copy your working data folder
  echo   into dist\GoldSilverBot\data before using the EXE.
echo - Keep the whole dist\GoldSilverBot folder together.
pause
exit /b 0

:error
echo.
echo [ERROR] EXE build failed. Copy the error above for troubleshooting.
pause
exit /b 1
