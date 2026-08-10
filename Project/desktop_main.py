import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from werkzeug.serving import make_server

from app import app, whatsapp, auto_start_saved_schedule, DATA_DIR, local_ip_address, MOBILE_PIN


def find_browser():
    candidates = [
        os.environ.get('PROGRAMFILES', '') + r'\Microsoft\Edge\Application\msedge.exe',
        os.environ.get('PROGRAMFILES(X86)', '') + r'\Microsoft\Edge\Application\msedge.exe',
        os.environ.get('LOCALAPPDATA', '') + r'\Microsoft\Edge\Application\msedge.exe',
        os.environ.get('PROGRAMFILES', '') + r'\Google\Chrome\Application\chrome.exe',
        os.environ.get('PROGRAMFILES(X86)', '') + r'\Google\Chrome\Application\chrome.exe',
        os.environ.get('LOCALAPPDATA', '') + r'\Google\Chrome\Application\chrome.exe',
    ]
    for p in candidates:
        if p and Path(p).exists():
            return str(Path(p))
    for name in ('msedge.exe', 'chrome.exe'):
        found = shutil.which(name)
        if found:
            return found
    return None


def main():
    browser = find_browser()
    if not browser:
        raise SystemExit('Microsoft Edge or Google Chrome is required for the desktop window.')

    server = make_server('0.0.0.0', 5000, app, threaded=True)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True, name='RateBotServer')
    server_thread.start()

    whatsapp.validate_session_async()
    threading.Timer(1.0, auto_start_saved_schedule).start()
    time.sleep(1.3)

    shell_profile = DATA_DIR / 'desktop_shell_profile'
    shell_profile.mkdir(parents=True, exist_ok=True)
    cmd = [
        browser,
        '--app=http://127.0.0.1:5000',
        '--start-maximized',
        '--no-first-run',
        '--no-default-browser-check',
        f'--user-data-dir={shell_profile}',
    ]
    process = subprocess.Popen(cmd)
    try:
        process.wait()
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
