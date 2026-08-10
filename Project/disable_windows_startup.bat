@echo off
set "LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\GoldSilverBot V6.lnk"
if exist "%LINK%" del /q "%LINK%"
echo GoldSilverBot Windows startup has been disabled.
pause
