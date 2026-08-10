@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Please run install.bat first.
  pause
  exit /b 1
)
set "VBS=%CD%\run_background.vbs"
set "LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\GoldSilverBot V6.lnk"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%LINK%'); $s.TargetPath=$env:WINDIR+'\System32\wscript.exe'; $s.Arguments='""%VBS%""'; $s.WorkingDirectory='%CD%'; $s.Save()"
if errorlevel 1 goto :error
echo.
echo GoldSilverBot will now launch silently when you sign in to Windows.
echo Also enable 'Automatically start the saved daily schedule' in the dashboard.
pause
exit /b 0
:error
echo Could not create the Windows Startup shortcut.
pause
exit /b 1
