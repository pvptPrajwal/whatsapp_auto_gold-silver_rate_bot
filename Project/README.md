# GoldSilverBot V7

V7 builds on the stable V5/V6 hidden-Selenium WhatsApp sender. The existing `fetch_rates()` block is unchanged.

## New in V7

- Multiple saved WhatsApp groups with enable/disable controls.
- Separate editable Morning, Afternoon, Evening and Manual message templates.
- Template placeholders: `{shift}`, `{silver_rate}`, `{gold_24k}`, `{gold_22k}`, `{date}`, `{time}`.
- Automatic WhatsApp retries after a failed send, with configurable retry count and delay.
- Browser/dashboard notifications for successful, partial and failed sends.
- Redesigned responsive desktop/mobile dashboard.
- Message history now records the target group and number of attempts.
- One-click `build_windows_exe.bat` for creating a Windows EXE on the Windows PC.
- `mobile_android_source` containing a native Android WebView client for the same backend.

## Upgrade from working V6

The safest method is to use the V7 upgrade ZIP supplied separately. Close V6, copy the V7 upgrade files over the V6 project, and **keep the existing `data` folder**. This preserves the WhatsApp browser profile/session and history.

After upgrading, run `run.bat`.

## Multiple groups

Open **Groups**, enter the exact WhatsApp Web group name, and click **Add Group**. Disable a group with its switch without deleting it. Every enabled group receives scheduled and manual updates.

## Message templates

Open **Templates**. There are four independent templates. Use **Preview** before saving. Unknown placeholders are rejected when settings are saved.

## Retries

Open **Automation**. `Retries after failure = 2` means a maximum of 3 total attempts for each group. The retry delay is configurable from 5 to 300 seconds.

## Notifications

Click **Enable notifications** in the dashboard. Browser notifications work while the dashboard/browser is running and permission is granted. Send status also remains visible in History and Live Logs.

## Windows EXE

1. Run `install.bat` once.
2. Run `build_windows_exe.bat`.
3. The result is `dist\GoldSilverBot\GoldSilverBot.exe`.
4. Keep the complete `dist\GoldSilverBot` folder together.
5. To carry over the current WhatsApp login, copy the existing project `data` folder into `dist\GoldSilverBot\data` before first EXE use.

The EXE is built on the user's Windows machine because Windows PyInstaller binaries must be produced in a Windows Python environment.

## Android client

The `mobile_android_source` folder is a small native Android client around the same backend. Build it using Android Studio. The Windows host continues to perform rate fetching, scheduling and WhatsApp sending. The Android phone connects to the Mobile URL shown on the PC dashboard and then uses the existing 6-digit mobile PIN.

## Important architectural point

V7 mobile control still depends on the host Windows PC being on and reachable. Moving the automation backend to an always-on cloud/server machine is a separate deployment phase. The current hidden Selenium WhatsApp mechanism is intentionally preserved because it is the version that has been proven to work on the user's PC.
