# GoldSilver Rate Bot V8
## Developer Documentation

**Version:** 8.0  
**Primary language:** Python  
**Backend/UI:** Flask + HTML/CSS/JavaScript  
**Automation:** Selenium WebDriver  
**Scheduling:** `schedule`  
**Persistence:** JSON + SQLite + browser profile directory  
**Desktop shell:** Chromium `--app=` window  
**Packaging:** PyInstaller `--onedir`

---

## 1. System overview

V8 is a Windows-hosted automation application with four main subsystems:

```text
+------------------------+
| Desktop / Mobile UI    |
| Flask + HTML/JS        |
+-----------+------------+
            |
            v
+------------------------+
| Application Service    |
| settings / templates   |
| scheduler / history    |
+-----+-------------+----+
      |             |
      v             v
+-----------+   +------------------+
| Rate      |   | WhatsApp Manager |
| Selenium  |   | Selenium         |
| headless  |   | hidden non-head. |
+-----+-----+   +--------+---------+
      |                  |
      v                  v
Bullion websites    WhatsApp Web
```

The Android client is only a remote WebView/controller. The Windows host remains authoritative for scraping, scheduling, persistence, and WhatsApp sending.

---

## 2. Main entry points

### `desktop_main.py`

Primary desktop entry point used by `run.bat`.

Responsibilities:

- locate Microsoft Edge or Google Chrome;
- start Flask on `0.0.0.0:5000` using Werkzeug `make_server`;
- asynchronously validate the saved WhatsApp session;
- restore the saved schedule if `auto_start` is enabled;
- launch the local dashboard in a Chromium `--app=http://127.0.0.1:5000` window;
- stop the server when the desktop shell window exits.

### `app.py`

Core application module.

Responsibilities:

- Flask routes;
- settings loading/saving;
- rate source discovery;
- selected-rate fetching;
- message rendering;
- scheduler lifecycle;
- retry logic;
- send history;
- mobile PIN authentication;
- system status/events.

### `whatsapp_manager.py`

Persistent-session WhatsApp Web Selenium layer.

Responsibilities:

- browser selection;
- dedicated WhatsApp browser profile;
- visible first-time login;
- hidden non-headless session validation;
- group search/open;
- composer detection;
- sending;
- diagnostic screenshot/HTML capture;
- forgetting the saved session.

---

## 3. Project structure

```text
GoldSilverBot_v8/
├── app.py
├── desktop_main.py
├── whatsapp_manager.py
├── requirements.txt
├── install.bat
├── run.bat
├── run_web_dashboard.bat
├── run_background.vbs
├── build_desktop_exe.bat
├── build_windows_exe.bat
├── enable_windows_startup.bat
├── disable_windows_startup.bat
├── allow_mobile_firewall.bat
├── VERSION.txt
├── START_HERE.txt
├── README.md
├── templates/
│   ├── index.html
│   └── login.html
├── static/
│   ├── style.css
│   ├── icon-192.png
│   ├── icon-512.png
│   └── manifest.webmanifest
├── mobile_android_source/
│   └── ...
└── data/
    └── persistent runtime data
```

---

## 4. Python dependencies

From `requirements.txt`:

```text
Flask>=3.1,<4
selenium>=4.25,<5
webdriver-manager>=4.0.2,<5
schedule>=1.2.2,<2
psutil>=6.1,<8
```

### Dependency roles

- **Flask:** HTTP API and dashboard backend.
- **Selenium:** rate-site and WhatsApp Web automation.
- **webdriver-manager:** ChromeDriver acquisition for Chrome flows.
- **schedule:** three daily in-process scheduled jobs.
- **psutil:** Windows browser-process tree handling for hidden WhatsApp windows.

Edge uses Selenium Manager through `webdriver.Edge(...)`; Chrome uses `ChromeDriverManager().install()`.

---

## 5. Runtime directories and persistence

`app.py` distinguishes resources from user data so PyInstaller builds can retain mutable files next to the EXE.

### Source mode

`APP_DIR = SOURCE_DIR`

### Frozen/PyInstaller mode

`APP_DIR = directory containing sys.executable`

### Persistent data directory

`DATA_DIR = APP_DIR / "data"`

The application creates the folder if absent.

Important persistent files include:

- `data/settings.json`
- `data/bot_history.sqlite3`
- `data/flask_secret.txt`
- `data/mobile_pin.txt`
- WhatsApp profile/session directory created by `WhatsAppManager`
- WhatsApp diagnostic files
- desktop shell browser profile

This folder must be preserved across upgrades.

---

## 6. Settings schema

Default structure:

```json
{
  "groups": [],
  "group_name": "",
  "s_margin": 0,
  "g_margin": 0,
  "gold_source": {
    "site": "safari",
    "tab": "",
    "commodity": "GOLD INDIAN-BIS 995 1KG T+0",
    "side": "SELL"
  },
  "silver_source": {
    "site": "navratna",
    "tab": "SILVER",
    "commodity": "SILVER 999 (PETI CUT) + GST",
    "side": "SELL"
  },
  "time1": "10:00",
  "time2": "14:00",
  "time3": "18:00",
  "auto_start": false,
  "retry_count": 2,
  "retry_delay": 20,
  "templates": {
    "morning": "...",
    "afternoon": "...",
    "evening": "...",
    "manual": "..."
  }
}
```

### Normalisation and validation

- group names are de-duplicated case-insensitively;
- BUY/SELL is normalised to uppercase;
- source site must exist in `SITE_DEFINITIONS`;
- schedule times must parse as `%H:%M`;
- retry count is clamped to 0–5;
- retry delay is clamped to 5–300 seconds;
- templates are validated against an allowlist of fields.

---

## 7. Template engine

Allowed fields:

```text
{shift}
{silver_rate}
{gold_24k}
{gold_22k}
{date}
{time}
```

`validate_template()` parses the format string using `string.Formatter` and rejects unknown fields.

`build_message()` builds the runtime context and calculates:

```text
gold_22k = round(gold_24k * 0.92, 2)
```

Template selection is based on `template_key_for_shift()`.

---

## 8. Rate website definitions

Configured in `SITE_DEFINITIONS`:

```python
SITE_DEFINITIONS = {
    "safari": {
        "name": "Safari Bullions",
        "url": "https://www.safaribullions.com/"
    },
    "navratna": {
        "name": "Shree Navratna Bullions",
        "url": "https://shreenavratnabullions.com/liverates.html"
    }
}
```

Default source constants:

- `DEFAULT_GOLD_SOURCE`
- `DEFAULT_SILVER_SOURCE`

---

## 9. Rate discovery pipeline

### Driver

`_new_rate_driver()` creates a headless Chrome session with:

- `--headless`
- `--log-level=3`
- `--window-size=1600,1200`

### Scan operation

`scan_rate_catalog()`:

1. opens Safari Bullions;
2. waits for page load;
3. extracts visible table rows from the live-rate page;
4. opens Shree Navratna Bullions;
5. iterates `LIVE RATES`, `SILVER`, and `COINS` tabs;
6. extracts visible table rows;
7. de-duplicates rows;
8. stores the catalog in in-memory `bot_state["rate_catalog"]`.

### Table extraction

`_catalog_from_visible_tables()`:

- scans visible `<table>` elements;
- treats the first `<td>` as commodity name;
- detects BUY and SELL column positions from table headings;
- falls back to BUY index `1` and SELL index `2` if headings are unavailable;
- extracts the first numeric rate from the first line of a rate cell.

### Selection identity

A saved source uses:

```text
site + tab + exact commodity + side
```

The commodity comparison is exact after whitespace normalisation and uppercasing.

---

## 10. Selected-rate fetch pipeline

`fetch_rates(silver_margin, gold_margin, silver_source, gold_source)`:

1. normalises both source definitions;
2. groups requested outputs by website so the same website need not be opened twice if Gold and Silver are sourced from it;
3. opens each required website;
4. optionally clicks the saved tab;
5. finds the exact commodity row;
6. resolves the saved BUY/SELL column;
7. extracts the raw rate;
8. applies the output-specific margin;
9. returns `(silver_rate, gold_rate)`.

Failure for an individual selected rate returns `"Not Found"` for that output.

Scheduled/manual send is cancelled if either output is `"Not Found"`.

---

## 11. Scheduler design

The scheduler uses the `schedule` package and a dedicated loop thread.

`configure_schedule()` registers exactly three daily jobs tagged `gold_silver_bot`:

- Morning Update;
- Afternoon Update;
- Evening Update.

Each schedule callback calls `launch_job()`, which starts a separate daemon thread. This prevents a long WhatsApp retry sequence from blocking the scheduler clock.

`start_scheduler()` ensures only one scheduler thread is active.

`stop_scheduler()` clears tagged jobs and marks the scheduler stopped.

The application does not stop after three sends; the daily schedule repeats while the process remains running.

---

## 12. Manual/scheduled job pipeline

`execute_job()`:

1. resets the daily success counter if the date changed;
2. resolves enabled WhatsApp groups;
3. fetches selected Gold/Silver rates;
4. updates `bot_state["latest_rates"]`;
5. aborts on a missing rate;
6. renders the appropriate message template;
7. iterates enabled groups;
8. calls `send_to_group_with_retry()` for each group;
9. records each group result in SQLite;
10. updates last-send and UI events.

Multiple groups are processed sequentially inside the job thread.

---

## 13. Retry model

`send_to_group_with_retry()` uses:

```text
max_attempts = retry_count + 1
```

On success:

- SQLite history row with `status='success'`;
- event notification;
- log message.

After final failure:

- SQLite history row with `status='failed'`;
- error event;
- log message.

---

## 14. Send history database

SQLite file:

`data/bot_history.sqlite3`

Table:

`send_history`

Columns:

- `id`
- `created_at`
- `shift_name`
- `status`
- `group_name`
- `silver_rate`
- `gold_rate`
- `detail`
- `attempts`
- `message_preview`

`init_db()` includes simple additive migration logic for `attempts` and `message_preview`.

---

## 15. WhatsApp architecture

V8 intentionally does **not** use PyWhatKit, whatsapp-web.js, or WPPConnect.

The working implementation uses Selenium WebDriver against WhatsApp Web.

### First connection

`connect_visible()`:

- launches a normal visible Chrome/Edge browser;
- loads `https://web.whatsapp.com/`;
- waits until the chat list is detected;
- writes a marker containing link time/browser;
- closes the visible browser.

### Persistent session

The dedicated browser profile lives under the application `data` directory.

`validate_session()` launches the same profile in a hidden background browser and verifies that the chat list is present.

### Hidden background mode

The WhatsApp browser is **non-headless** for compatibility, but on Windows it is moved off-screen and its top-level windows are hidden using Win32 APIs and process-tree detection.

This avoids foreground takeover while preserving normal browser rendering.

### Send operation

`send_message(group_name, message)`:

1. starts hidden non-headless browser;
2. loads WhatsApp Web with saved profile;
3. validates login;
4. locates search box;
5. types exact group name;
6. finds and opens group;
7. validates chat header where possible;
8. locates composer using multiple fallback strategies;
9. types/sends message;
10. closes browser.

The user's physical mouse/keyboard are not blocked.

### Diagnostics

On failures, `WhatsAppManager` can save:

- PNG screenshot;
- HTML page source;
- TXT metadata.

These files should be used before changing selectors blindly.

---

## 16. Browser selection

The WhatsApp manager attempts to use an installed Chromium browser and remembers the browser used for the saved authentication profile.

The desktop shell searches Edge first, then Chrome.

Rate scraping currently creates a Chrome WebDriver via `ChromeDriverManager`.

### Developer note

If the product is intended for PCs with Edge but no Chrome, the rate-scraping driver should be generalized to select Edge or Chrome in the same way as `WhatsAppManager`. At present, the source package's rate driver is Chrome-specific.

---

## 17. Flask/mobile authentication model

The Flask service listens on:

`0.0.0.0:5000`

### Local requests

Requests from `127.0.0.1` / `::1` bypass the mobile PIN login.

### Remote LAN requests

Remote requests must establish a Flask session using the six-digit PIN stored in:

`data/mobile_pin.txt`

The Flask secret is persisted in:

`data/flask_secret.txt`

Sessions are configured with a 30-day lifetime.

### Security boundary

This is LAN-oriented access. There is no TLS/HTTPS in V8. Do not expose TCP port 5000 directly to the internet.

---

## 18. HTTP routes/API

### UI/Auth

- `GET|POST /login` – mobile PIN login
- `POST /logout` – clear mobile authentication session
- `GET /` – main dashboard

### Settings / scheduler

- `POST /settings/save` – validate and persist settings
- `POST /start` – save settings and start scheduler
- `POST /stop` – stop scheduler
- `POST /send-now` – save settings and launch manual update

### Status/history/events

- `GET /logs` – logs, scheduler state, latest rates, last send, next runs
- `GET /history?limit=N` – recent SQLite history, max 200
- `GET /api/events?after=N` – incremental UI events
- `GET /api/system-info` – mobile URL; mobile PIN only for local requests
- `GET /health` – health/version

### Rate source APIs

- `GET /api/rates/catalog` – current in-memory scanned catalog and saved source settings
- `POST /api/rates/scan` – run live website discovery
- `POST /api/rates/test` – persist settings and fetch selected rates without WhatsApp sending

### Template API

- `POST /api/template-preview` – validate template and return sample-rendered message

### WhatsApp APIs

- `GET /whatsapp/status`
- `POST /whatsapp/connect`
- `POST /whatsapp/validate`
- `POST /whatsapp/forget`

Remote access to API/WhatsApp routes is blocked unless the mobile Flask session is authenticated.

---

## 19. Desktop shell

`desktop_main.py` runs the Flask server in-process and launches Edge/Chrome with:

```text
--app=http://127.0.0.1:5000
--start-maximized
--no-first-run
--no-default-browser-check
--user-data-dir=<data/desktop_shell_profile>
```

This provides an application-like window while reusing the existing web UI.

The desktop shell is not a native GUI toolkit; it is a Chromium app-mode wrapper around the local Flask dashboard.

---

## 20. Android client

The Android source is a WebView shell.

It points to the Windows host's LAN URL, for example:

`http://192.168.1.10:5000`

It depends entirely on the Windows host service. No scraping or WhatsApp logic should be duplicated in Android unless the architecture is deliberately redesigned.

---

## 21. Windows startup integration

`enable_windows_startup.bat` creates a shortcut in the user's Windows Startup folder that launches `run_background.vbs` through `wscript.exe`.

For unattended scheduling, both conditions are required:

1. Windows startup shortcut enabled; and
2. `auto_start=true` in saved application settings.

---

## 22. Windows firewall helper

`allow_mobile_firewall.bat`:

- requires Administrator privileges;
- adds an inbound TCP/5000 rule on the **Private** Windows Firewall profile.

Developer note: the rule name still contains `GoldSilverBot V6 Mobile`. This is cosmetic technical debt and should be renamed in a later release while preserving cleanup compatibility for older rules.

---

## 23. PyInstaller build

`build_desktop_exe.bat`:

1. activates `.venv`;
2. installs/upgrades PyInstaller;
3. clears previous `build` and target `dist` directory;
4. runs PyInstaller in `--onedir --windowed` mode;
5. bundles `templates` and `static` resources;
6. collects Selenium, webdriver-manager, and certifi data;
7. creates `dist\GoldSilverRateBot\data`;
8. copies README/version metadata.

Output:

`dist\GoldSilverRateBot\GoldSilverRateBot.exe`

The complete output folder must be distributed.

### Installer status

V8 does not yet create an MSI/Inno Setup/NSIS-style `Setup.exe`. If mass deployment is required, create an installer around the complete PyInstaller output folder and configure shortcuts/uninstall rules separately.

---

## 24. Development invariants

When modifying V8, preserve these behaviours unless a deliberate migration is approved:

1. User-selected rate source must be represented by exact website + tab + commodity + BUY/SELL side.
2. Gold and Silver margins are applied only after extracting the selected raw website rate.
3. Rate scanning and rate fetching must remain independent of WhatsApp sending.
4. WhatsApp authentication data must persist under `data` and must not be deleted during normal upgrades.
5. First WhatsApp login may be visible; subsequent validation/sends should remain hidden/background on Windows.
6. The scheduler must repeat daily and must not clear itself after three successful messages.
7. Failed rate retrieval must prevent outgoing messages rather than sending `Not Found` values.
8. Multiple enabled groups are independent send targets with separate history rows.
9. Android/mobile should remain a controller unless a new server-hosted architecture is adopted.
10. Do not expose the local Flask service directly to the public internet without adding proper authentication, HTTPS, and deployment hardening.

---

## 25. Recommended test matrix

### Installation

- fresh `.venv` creation;
- Chrome installed;
- Edge installed;
- missing browser failure path.

### Rate discovery

- Safari scan returns rows;
- Navratna LIVE RATES/SILVER/COINS tabs return rows;
- BUY/SELL heading detection;
- fallback column detection;
- duplicate removal;
- selected row missing after a website change.

### Rate fetch

- default Gold SELL selection;
- default Silver SELL selection;
- BUY selection;
- both outputs from same website;
- margins positive/zero/negative if UI permits;
- missing rate cancels send.

### WhatsApp

- first-time login;
- saved-session restart;
- logged-out session;
- exact group found;
- group renamed;
- read-only/admin-only group;
- composer selector failure diagnostics;
- sequential multi-group sending.

### Scheduler

- three jobs registered;
- next-run reporting;
- daily rollover;
- app restart with `auto_start`;
- stop/restart scheduler;
- concurrent job protection/behaviour around long retries.

### Retry/history

- success first attempt;
- success after retry;
- final failure;
- SQLite row correctness;
- UI event correctness.

### Mobile

- local PC bypasses PIN;
- remote LAN requires PIN;
- wrong PIN;
- session persistence;
- firewall rule behaviour;
- Android WebView access.

### Packaging

- PyInstaller build launches;
- templates/static available;
- writable `data` beside EXE;
- WhatsApp profile persists after EXE restart.

---

## 26. Known technical risks / debt

1. **Website DOM dependency:** Rate scanning assumes table-based markup and exact commodity text. Site redesigns may break extraction.
2. **Column fallback:** When BUY/SELL headings cannot be detected, indexes 1/2 are assumed.
3. **Chrome-specific rate driver:** `_new_rate_driver()` currently uses Chrome + ChromeDriverManager even though the desktop/WhatsApp layers can use Edge.
4. **WhatsApp DOM dependency:** WhatsApp Web selectors can change at any time.
5. **Unofficial automation:** WhatsApp Web browser automation is not the official WhatsApp Business Cloud API.
6. **Local HTTP:** LAN control has no HTTPS/TLS.
7. **PIN storage:** The six-digit PIN is stored as plaintext in `data/mobile_pin.txt`; acceptable only for the present local-LAN threat model.
8. **Port fixed at 5000:** Port is not currently configurable.
9. **Single-process scheduler:** Scheduled jobs exist only while the Windows application is running.
10. **No formal installer:** V8 builds a PyInstaller directory, not a signed installer package.

---

## 27. Suggested roadmap

### V8.x hardening

- browser abstraction for rate scraping (Edge/Chrome);
- configurable port;
- formal logging files with rotation;
- rate-source health checks;
- safer selector versioning/fallback diagnostics;
- migration/version field in settings;
- update firewall rule naming;
- automated smoke tests.

### Distribution

- signed Windows installer using Inno Setup, WiX, or NSIS;
- automatic shortcuts/startup option in installer;
- application icon/version metadata;
- uninstall preserving or optionally removing `data`;
- code signing.

### Server/mobile architecture

If the requirement becomes “messages must send while the PC is off,” move scraping/scheduling/messaging to a continuously running server and treat Windows/Android as clients. That would be a separate architecture, not a packaging change.

---

## 28. Error-reporting checklist for developers

Capture:

- version from `VERSION.txt`;
- relevant Live Logs;
- route/action that failed;
- selected rate source JSON;
- browser name/version;
- Windows version;
- WhatsApp session state;
- diagnostic PNG/HTML/TXT created by `WhatsAppManager`;
- relevant SQLite history row;
- exact reproduction steps.

Do not commit or publish the persistent `data` directory, WhatsApp profile, Flask secret, mobile PIN, or customer/group information.
