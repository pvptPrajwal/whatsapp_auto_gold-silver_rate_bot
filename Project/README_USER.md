# GoldSilver Rate Bot V8
## User Guide

**Version:** 8.0  
**Platform:** Windows 10/11, 64-bit  
**Purpose:** Fetch user-selected bullion rates from supported websites, apply margins, and send scheduled or manual WhatsApp group updates from a Windows PC.

---

## 1. What the software does

GoldSilver Rate Bot V8 allows a user to:

- scan the supported bullion websites and view available BUY/SELL rate rows;
- select the exact Gold rate and Silver rate to be used;
- apply separate Gold and Silver margins;
- connect WhatsApp once and reuse the saved WhatsApp Web session;
- send messages to one or more enabled WhatsApp groups;
- define separate Morning, Afternoon, Evening, and Manual message templates;
- run three daily scheduled updates;
- retry failed WhatsApp sends automatically;
- review live logs, latest rates, send history, and send status;
- use the same dashboard from an Android phone on the same Wi-Fi network;
- optionally start the software automatically when signing in to Windows.

The Windows PC remains the host. Rate fetching, scheduling, and WhatsApp automation run on the PC, not on the Android phone.

---

## 2. Supported rate websites

V8 currently supports:

1. **Safari Bullions**  
   `https://www.safaribullions.com/`

2. **Shree Navratna Bullions**  
   `https://shreenavratnabullions.com/liverates.html`

The software scans visible rate tables and lets the user select an exact commodity row and either the BUY or SELL side.

Default selections are:

- Gold: **Safari Bullions → GOLD INDIAN-BIS 995 1KG T+0 → SELL**
- Silver: **Shree Navratna Bullions → SILVER 999 (PETI CUT) + GST → SELL**

These defaults can be changed from the Rate Sources section without editing code.

---

## 3. Requirements

### For the current source/development package

The PC should have:

- Windows 10 or Windows 11, 64-bit;
- Python 3 installed and available in PATH;
- Google Chrome or Microsoft Edge;
- internet access;
- a WhatsApp account that can use WhatsApp Web.

### For a packaged EXE build

The generated `GoldSilverRateBot.exe` contains the Python application runtime produced by PyInstaller, but the PC still requires Google Chrome or Microsoft Edge for browser automation.

> **Important:** V8 currently includes an EXE builder. It does not yet include a full `Setup.exe` installer wizard. A separate installer can be created later around the built `dist\GoldSilverRateBot` folder.

---

## 4. First installation

For a fresh source installation:

1. Extract the V8 folder to a permanent location, for example:
   `C:\GoldSilverRateBot\`
2. Double-click `install.bat`.
3. Wait until Python packages finish installing.
4. Double-click `run.bat`.
5. The software opens as a desktop-style Edge/Chrome app window.

If you prefer the normal browser dashboard, run:

`run_web_dashboard.bat`

---

## 5. Upgrade from an older working version

When upgrading from a working V7.2/V8 installation:

1. Close the bot completely.
2. Back up the complete project folder.
3. Copy the new program files over the existing installation.
4. **Do not delete or replace the existing `data` folder unless specifically instructed.**
5. Start the software again.

The `data` folder contains persistent information such as:

- WhatsApp authentication profile;
- settings;
- message history database;
- mobile access PIN;
- Flask secret;
- diagnostic files.

---

## 6. First-time WhatsApp connection

1. Start GoldSilver Rate Bot.
2. Open the WhatsApp section.
3. Click **Connect WhatsApp**.
4. A visible WhatsApp Web browser opens on the PC.
5. On the phone, open WhatsApp → **Linked devices** → **Link a device**.
6. Scan the QR code if WhatsApp asks for it.
7. Wait until the WhatsApp chat list loads.
8. The bot saves the browser profile.
9. The visible login browser closes.

Future session checks and message sending use the saved browser profile in a hidden background browser.

If WhatsApp logs out or the linked-device session becomes invalid, reconnect from the WhatsApp section.

---

## 7. Configure rate sources

### Scan available website rates

1. Open **Rate Sources**.
2. Click **Scan Website Rates**.
3. Wait while the software opens the supported websites in a background browser.
4. Review the discovered commodity rows and BUY/SELL values.

### Select Gold rate

Choose:

- website;
- section/tab, if applicable;
- exact commodity name;
- BUY or SELL.

### Select Silver rate

Choose the same four fields for Silver.

### Save and test

1. Click **Save Rate Selection**.
2. Click **Test Selected Rates**.
3. Verify that the displayed Gold and Silver rates match the intended website values.

At send time, the software loads the selected website, finds the saved exact commodity row, extracts the saved BUY/SELL side, and then applies the configured margin.

---

## 8. Margins

The software supports separate margins for:

- Gold; and
- Silver.

The final outgoing rate is:

`Selected website rate + configured margin`

Example:

- Website Gold SELL rate: ₹150,100
- Gold margin: ₹500
- Outgoing Gold rate: ₹150,600

The default 22K Gold message value is calculated as:

`24K final Gold rate × 0.92`

---

## 9. WhatsApp groups

V8 supports multiple saved group names.

For each group:

- enter the group name exactly as it appears in WhatsApp;
- enable or disable the group;
- only enabled groups receive scheduled/manual messages.

Messages are sent to enabled groups sequentially.

If a group is renamed in WhatsApp, update the saved group name in GoldSilver Rate Bot.

---

## 10. Message templates

Separate templates are available for:

- Morning;
- Afternoon;
- Evening;
- Manual Send.

Allowed template fields are:

- `{shift}`
- `{silver_rate}`
- `{gold_24k}`
- `{gold_22k}`
- `{date}`
- `{time}`

Example:

```text
*{shift}*

*SILVER RATE* : ₹ {silver_rate} /kg
*GOLD RATE (24kt)* : ₹ {gold_24k} /10 gm
*GOLD RATE (22kt)* : ₹ {gold_22k} /10 gm

_Generated by Bot_
```

Do not use fields other than those listed above. The software validates templates before saving or sending.

---

## 11. Scheduling

The software provides three daily schedule times:

- Morning;
- Afternoon;
- Evening.

Times must be entered in 24-hour `HH:MM` format, for example:

- `10:00`
- `14:00`
- `18:00`

To activate:

1. configure the three times;
2. confirm at least one WhatsApp group is enabled;
3. connect WhatsApp;
4. click **Start Scheduler**.

The scheduler continues every day while the application is running.

Use **Stop Scheduler** to stop future scheduled sends.

---

## 12. Manual Send

Use **Fetch & Send Now** to run an immediate update.

The software will:

1. fetch the selected Gold and Silver website rates;
2. apply margins;
3. build the Manual template;
4. send to all enabled WhatsApp groups;
5. record success/failure in history.

---

## 13. Retry behaviour

The user can configure:

- retry count: 0 to 5 retries;
- retry delay: 5 to 300 seconds.

A retry count of `2` means up to 3 total attempts:

- first attempt;
- retry 1;
- retry 2.

Each group is handled separately, and the final result is stored in history.

---

## 14. History and logs

### Live Logs

Live Logs show current activity such as:

- rate website loading;
- rate selection;
- WhatsApp status;
- scheduled job start;
- retry attempts;
- success/failure information.

### History

History is stored in:

`data\bot_history.sqlite3`

It records, among other fields:

- date/time;
- shift;
- status;
- group name;
- Silver rate;
- Gold rate;
- attempts;
- detail/error text;
- message preview.

---

## 15. Mobile access on the same Wi-Fi

The Windows PC must be running the bot.

The local PC dashboard displays a mobile address similar to:

`http://192.168.1.10:5000`

It also displays a six-digit mobile PIN.

On the phone:

1. connect the phone to the same Wi-Fi/network as the PC;
2. open the mobile address in the Android app or a browser;
3. enter the six-digit PIN when prompted.

If Windows blocks access, right-click:

`allow_mobile_firewall.bat`

and choose **Run as administrator**.

The firewall rule opens TCP port 5000 on Windows Private networks.

> Mobile access in V8 uses local HTTP, not HTTPS. It is intended for a trusted private LAN, not direct exposure to the public internet.

---

## 16. Android app

The Android app is a WebView/controller for the Windows backend.

It does **not** perform:

- Selenium scraping;
- WhatsApp automation;
- scheduling independently of the PC.

The PC must therefore remain powered on and GoldSilver Rate Bot must be running.

---

## 17. Start automatically with Windows

To enable automatic launch:

1. in the dashboard, enable **Automatically start the saved daily schedule when the app starts**;
2. save settings;
3. run `enable_windows_startup.bat`.

To remove automatic Windows startup, run:

`disable_windows_startup.bat`

---

## 18. Build the Windows EXE

For the developer/source package:

1. first run `install.bat`;
2. confirm V8 is working;
3. run `build_desktop_exe.bat`.

The build output is:

`dist\GoldSilverRateBot\GoldSilverRateBot.exe`

The EXE is produced as an **onedir** PyInstaller application, so distribute the complete `dist\GoldSilverRateBot` folder, not only the `.exe` file.

If existing settings and WhatsApp login are intentionally being migrated to that build, copy the appropriate existing `data` folder into:

`dist\GoldSilverRateBot\data`

before first use.

---

## 19. Backup

Back up the complete `data` folder periodically.

Recommended backup before every upgrade:

`GoldSilverRateBot\data\`

Never publish or casually share this folder because it may contain a persistent WhatsApp Web profile and local authentication information.

---

## 20. Common troubleshooting

| Problem | Action |
|---|---|
| Software says `install.bat` must be run | Run `install.bat` once in the project folder. |
| Desktop window does not open | Confirm Chrome or Edge is installed, then try `run_web_dashboard.bat`. |
| WhatsApp says not connected | Click Connect WhatsApp and complete Linked Devices login again. |
| Group not found | Check that the saved group name exactly matches WhatsApp. |
| Message composer cannot be found | Check whether the account can send to that group. Review diagnostics under the `data` directory. |
| Gold/Silver rate not found | Re-run Rate Sources → Scan Website Rates, then save the currently available exact row. |
| Website rate is wrong | Confirm the selected commodity and BUY/SELL side, then use Test Selected Rates. |
| Phone cannot open PC dashboard | Same Wi-Fi, Windows Private network, PC running, correct IP, then run `allow_mobile_firewall.bat` as Administrator. |
| Schedule did not send | Confirm scheduler is Running, WhatsApp is connected, at least one group is enabled, and PC was on at the scheduled time. |
| Send failed repeatedly | Check Live Logs and History; verify internet, WhatsApp session, and group permissions. |

---

## 21. Operational limitations

1. The host Windows PC must remain powered on and connected to the internet for scheduled sending.
2. WhatsApp sending is browser automation of WhatsApp Web, not the official WhatsApp Business Cloud API.
3. WhatsApp Web interface changes can require selector maintenance.
4. Bullion website HTML/table changes can require rate-scanner maintenance.
5. Mobile control is designed for the same trusted LAN/Wi-Fi unless a secure server architecture is added later.
6. The Android app is not a standalone bot; it controls the PC backend.

---

## 22. Recommended daily operating procedure

1. Start GoldSilver Rate Bot.
2. Confirm **WhatsApp: Connected**.
3. Confirm the selected Gold and Silver rate sources.
4. Use **Test Selected Rates** if the website format or commodity list has changed.
5. Confirm enabled groups and margins.
6. Start the scheduler.
7. Review Live Logs/History after scheduled sends.

---

## 23. Support information to capture when reporting an error

When reporting a problem, provide:

- GoldSilver Rate Bot version;
- Windows version;
- whether Chrome or Edge is being used;
- screenshot of the dashboard error;
- relevant Live Log lines;
- whether the problem occurs during rate scan, rate fetch, WhatsApp connection, manual send, or scheduled send;
- diagnostic screenshot/HTML path if the WhatsApp manager created one.

Do not send the entire persistent WhatsApp profile unless specifically required and securely handled.
