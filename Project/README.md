# GoldSilverBot V6

V6 builds on the working V5 architecture. It intentionally retains the V5 hidden, non-headless Selenium WhatsApp sender and preserves the existing `fetch_rates()` block exactly.

## New in V6

- Responsive dashboard for PC and phone browsers.
- Same-Wi-Fi mobile access protected by a generated 6-digit PIN.
- Persistent settings, including an optional auto-start schedule flag.
- SQLite send history with success/failure records and the rates used.
- Live current/last rates, sent-today count and next scheduled runs.
- Windows Startup helper for silent launch.
- Optional Windows Firewall helper for mobile access on private networks.

## Installation

1. Extract to a new folder.
2. Run `install.bat` once.
3. Run `run.bat`.
4. Complete WhatsApp linking if required.
5. Configure and save the group, margins and three daily times.

## Mobile use

Keep the host PC running. The dashboard displays a LAN URL such as `http://192.168.1.10:5000` and a six-digit PIN. Open the URL from a phone connected to the same Wi-Fi and enter that PIN.

If Windows Firewall blocks access, right-click `allow_mobile_firewall.bat` and select **Run as administrator**. The helper opens TCP port 5000 only on the Windows **Private** network profile.

## Windows auto-start

Enable **Automatically start the saved daily schedule when the app starts**, save settings, and then run `enable_windows_startup.bat` once. `disable_windows_startup.bat` removes the Startup shortcut.

## Important architecture note

The phone is currently a controller for the bot running on the Windows PC. WhatsApp Web automation and website scraping still execute on the PC. A later server/mobile-native version can remove the requirement for the PC to remain on.
