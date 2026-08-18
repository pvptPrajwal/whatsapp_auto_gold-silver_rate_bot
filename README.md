# GoldSilver Rate Bot V8

V8 converts the working V7.2 project into a desktop-style Windows application and adds configurable live rate sources.

## Main change

Open **Rate Sources** and click **Scan Website Rates**. The bot discovers the currently displayed commodity rows and BUY/SELL rates on Safari Bullions and Shree Navratna Bullions. Choose the exact Gold output source and Silver output source, then save. Scheduled and manual sends fetch those saved rows only.

The default selections remain:
- Gold: Safari Bullions, GOLD INDIAN-BIS 995 1KG T+0, SELL
- Silver: Shree Navratna Bullions, SILVER 999 (PETI CUT) + GST, SELL

## Desktop software

Run `run.bat`. V8 opens in a standalone Edge/Chrome app window without normal browser tabs/address bar. `run_web_dashboard.bat` is retained if you want the classic browser dashboard.

## Build EXE

After V8 is confirmed working, run `build_desktop_exe.bat`. Output: `dist\GoldSilverRateBot\GoldSilverRateBot.exe`.

## Upgrade from V7.2

Close V7.2, back it up, copy the V8 upgrade files over it, and **do not delete the existing `data` folder**. Your WhatsApp session/history/settings remain there.
