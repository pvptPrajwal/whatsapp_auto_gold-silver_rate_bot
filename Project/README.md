# Gold & Silver Rate Bot V2

This build preserves the supplied `fetch_rates()` Selenium scraping logic and replaces PyWhatKit/MouseBlocker with a separate Selenium-based WhatsApp Web sender.

## Main changes

- First-time WhatsApp login in visible Chrome.
- Dedicated persistent Chrome profile stored under `data/whatsapp_profile`.
- Later WhatsApp session checks and scheduled sends run with `--headless=new`.
- Reconnect is requested only when the saved WhatsApp Web session is no longer valid.
- No PyWhatKit and no mouse blocking.
- Schedule continues daily until manually stopped; it no longer clears itself after three messages.
- Failed sends do not count as completed updates.
- Manual **Send Now** test is included.
- Settings are stored in `data/settings.json`.

## Windows setup

1. Install Python 3 and Google Chrome.
2. Run `install.bat` once.
3. Run `run.bat`.
4. Use **Connect WhatsApp** for the initial login.
5. Enter the exact WhatsApp group name.
6. Send a test message before starting the schedule.

## Note

The WhatsApp sender depends on WhatsApp Web's DOM. WhatsApp can change that interface without notice, in which case the selector list in `whatsapp_manager.py` may need to be updated.
