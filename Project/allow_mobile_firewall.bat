@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo This file must be run as Administrator.
  echo Right-click allow_mobile_firewall.bat and choose "Run as administrator".
  pause
  exit /b 1
)
netsh advfirewall firewall delete rule name="GoldSilverBot V6 Mobile" >nul 2>&1
netsh advfirewall firewall add rule name="GoldSilverBot V6 Mobile" dir=in action=allow protocol=TCP localport=5000 profile=private
if errorlevel 1 goto :error
echo.
echo Windows Firewall now allows GoldSilverBot on TCP port 5000 for PRIVATE networks.
pause
exit /b 0
:error
echo Could not create the firewall rule.
pause
exit /b 1
