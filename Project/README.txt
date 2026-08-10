GoldSilverBot V7.2 - Silver SELL Rate Fix

Change:
- Silver now specifically uses the highlighted/right-side SELL rate from:
  SILVER 999 (PETI CUT) + GST
- The first/main number in the SELL cell is used. High/Low values are ignored.
- Silver margin is added after selecting the website SELL rate.
- Gold SELL-rate fix from V7.1 is retained.
- WhatsApp/session/scheduler/UI logic is unchanged.

Upgrade:
1. Close run.bat / the bot.
2. Back up your working project folder.
3. Copy app.py from this patch into your existing V7.1/V7 project folder.
4. Replace the existing app.py.
5. Do NOT delete the data folder.
6. Run run.bat and use Fetch & Send Now to test.
