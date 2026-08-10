@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run install.bat before starting the bot.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python app.py
pause
