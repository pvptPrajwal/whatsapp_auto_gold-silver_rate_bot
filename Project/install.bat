@echo off
cd /d "%~dp0"
echo Creating Python virtual environment...
python -m venv .venv
if errorlevel 1 goto :error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto :error
echo.
echo Installation complete.
echo Run the bot using run.bat
pause
exit /b 0
:error
echo.
echo Installation failed. Confirm Python 3 is installed and available in PATH.
pause
exit /b 1
