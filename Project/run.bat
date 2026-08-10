@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run install.bat before starting the software.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python desktop_main.py
