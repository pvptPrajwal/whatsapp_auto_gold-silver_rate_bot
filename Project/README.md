# GoldSilverBot V3

V3 keeps the supplied `fetch_rates()` Selenium logic unchanged and replaces the WhatsApp DOM automation layer with a local `whatsapp-web.js` background service.

## Architecture

```text
Flask UI / Scheduler
        |
        +--> Existing fetch_rates() (unchanged)
        |       +--> Shree Navratna Bullions
        |       +--> Safari Bullions
        |
        +--> WhatsAppBridge (Python, localhost)
                    |
                    +--> Node.js / whatsapp-web.js
                           +--> LocalAuth persistent session
                           +--> Group list + real group IDs
                           +--> Chat.sendMessage()
```

## Setup

1. Install Python 3.10+ and Node.js 18+.
2. Run `install.bat` once.
3. Run `run.bat`.
4. Scan the QR code shown inside the app on first login.
5. Select the destination WhatsApp group.
6. Use **Send Test / Send Now** before enabling the daily scheduler.

## Persistent WhatsApp session

Authentication data is stored under `data/wwebjs_auth/`. Do not delete that directory if you want the login to persist.

## Notes

- No PyWhatKit.
- No mouse/keyboard blocking.
- No Selenium WhatsApp search-box/message-box selectors.
- The service is bound to `127.0.0.1` only.
- The WhatsApp service uses port `3001`; Flask uses port `5000`.
- The browser used internally by the WhatsApp service remains headless.

## Disclaimer

`whatsapp-web.js` is an unofficial WhatsApp Web client automation library. Account/platform behavior may change and should be tested with the intended WhatsApp account before production use.
