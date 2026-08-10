# GoldSilverBot V5 - Hidden Selenium WhatsApp

This build removes Puppeteer, whatsapp-web.js and WPPConnect completely.

## Important design
- `fetch_rates()` is unchanged from the user's supplied Selenium rate-fetching logic.
- First WhatsApp login is visible so the QR/device link can be completed.
- The WhatsApp session is stored in `data/whatsapp_profile_v5`.
- Later session checks and message sends use **normal non-headless Chromium**, but the browser is started off-screen and hidden using the Windows API.
- No PyWhatKit, PyAutoGUI, Puppeteer or Node.js is required.

## Install
1. Extract into a new folder.
2. Run `install.bat` once.
3. Run `run.bat`.
4. Click **Connect WhatsApp** and complete the first login.
5. Enter the WhatsApp group name exactly.
6. Click **Send Test / Send Now**.

## If WhatsApp logs out
Click **Connect WhatsApp** again. Do not delete the `data` folder unless you intentionally want to forget the session.

## Diagnostics
If a send fails, screenshots and HTML are saved under `data/whatsapp_debug`.
