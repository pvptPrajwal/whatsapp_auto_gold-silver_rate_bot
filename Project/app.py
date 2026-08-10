from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import threading
import time
import datetime
import json
import re
import schedule
import webbrowser
import socket
import sqlite3
import secrets
import sys
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import StaleElementReferenceException

from whatsapp_manager import WhatsAppManager

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"
DB_FILE = DATA_DIR / "bot_history.sqlite3"
SECRET_FILE = DATA_DIR / "flask_secret.txt"
PIN_FILE = DATA_DIR / "mobile_pin.txt"


def _load_or_create_text(path, factory):
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value
    value = factory()
    path.write_text(value, encoding="utf-8")
    return value


app.secret_key = _load_or_create_text(SECRET_FILE, lambda: secrets.token_hex(32))
MOBILE_PIN = _load_or_create_text(PIN_FILE, lambda: f"{secrets.randbelow(1000000):06d}")


# --- Global State for Web Server ---
bot_state = {
    "is_running": False,
    "jobs_completed": 0,
    "jobs_date": datetime.date.today().isoformat(),
    "logs": ["[SYSTEM] Server started. Ready to launch."],
    "latest_rates": None,
    "last_send": None,
}
state_lock = threading.RLock()
scheduler_thread = None
scheduler_thread_lock = threading.Lock()


def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS send_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                shift_name TEXT NOT NULL,
                status TEXT NOT NULL,
                group_name TEXT NOT NULL,
                silver_rate TEXT,
                gold_rate TEXT,
                detail TEXT
            )
        """)
        conn.commit()


def history_add(shift_name, status, group_name, silver_rate=None, gold_rate=None, detail=""):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO send_history(created_at, shift_name, status, group_name, silver_rate, gold_rate, detail) VALUES(?,?,?,?,?,?,?)",
            (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                shift_name,
                status,
                group_name,
                None if silver_rate is None else str(silver_rate),
                None if gold_rate is None else str(gold_rate),
                str(detail or ""),
            ),
        )
        conn.commit()


def history_recent(limit=25):
    limit = max(1, min(int(limit), 100))
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, created_at, shift_name, status, group_name, silver_rate, gold_rate, detail FROM send_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def successful_count_today():
    today = datetime.date.today().isoformat() + "%"
    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM send_history WHERE status='success' AND created_at LIKE ?",
            (today,),
        ).fetchone()
    return int(row[0] if row else 0)


def log_msg(message):
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    with state_lock:
        bot_state["logs"].append(f"[{current_time}] {message}")
        if len(bot_state["logs"]) > 200:
            bot_state["logs"].pop(0)
    print(f"[{current_time}] {message}")


whatsapp = WhatsAppManager(DATA_DIR, log_callback=log_msg)


def load_settings():
    defaults = {
        "group_name": "",
        "s_margin": 0,
        "g_margin": 0,
        "time1": "10:00",
        "time2": "14:00",
        "time3": "18:00",
        "auto_start": False,
    }
    if not SETTINGS_FILE.exists():
        return defaults
    try:
        loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        defaults.update({k: loaded[k] for k in defaults if k in loaded})
    except Exception as exc:
        log_msg(f"Settings file could not be read: {exc}")
    return defaults


def _valid_hhmm(value):
    try:
        datetime.datetime.strptime(value, "%H:%M")
        return True
    except Exception:
        return False


def save_settings(data):
    clean = {
        "group_name": str(data.get("group_name", "")).strip(),
        "s_margin": int(data.get("s_margin", 0)),
        "g_margin": int(data.get("g_margin", 0)),
        "time1": str(data.get("time1", "10:00")),
        "time2": str(data.get("time2", "14:00")),
        "time3": str(data.get("time3", "18:00")),
        "auto_start": bool(data.get("auto_start", False)),
    }
    for key in ("time1", "time2", "time3"):
        if not _valid_hhmm(clean[key]):
            raise ValueError(f"Invalid time: {clean[key]}")
    SETTINGS_FILE.write_text(json.dumps(clean, indent=2), encoding="utf-8")
    return clean


def local_ip_address():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"
    finally:
        sock.close()


def _is_local_request():
    return request.remote_addr in ("127.0.0.1", "::1", None)


@app.before_request
def protect_remote_access():
    if _is_local_request():
        return None
    if request.path.startswith("/static/") or request.path in ("/login", "/health"):
        return None
    if session.get("mobile_authenticated"):
        return None
    if request.path.startswith("/api/") or request.path.startswith("/whatsapp/") or request.path in (
        "/start", "/stop", "/send-now", "/logs", "/history", "/settings/save"
    ):
        return jsonify({"status": "error", "message": "Mobile session is not authenticated."}), 401
    return redirect(url_for("login"))


init_db()
with state_lock:
    bot_state["jobs_completed"] = successful_count_today()


# ---------------------------------------------------------------------------
# EXISTING RATE FETCHING LOGIC
# Kept EXACTLY as in the working V5 build.
# ---------------------------------------------------------------------------
def fetch_rates(silver_margin, gold_margin):
    log_msg("🚀 Starting Chrome in background...")
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--log-level=3')
    driver = webdriver.Chrome(service=service, options=options)

    silver_rate, gold_rate = "Not Found", "Not Found"

    try:
        log_msg("⏳ Fetching Silver rates...")
        driver.get("https://shreenavratnabullions.com/liverates.html")
        time.sleep(6)
        try:
            for tab in driver.find_elements(By.XPATH, "//*[text()='SILVER']"):
                if tab.is_displayed():
                    tab.click()
                    time.sleep(2)
                    break
        except: pass

        for _ in range(3):
            try:
                for row in driver.find_element(By.ID, "gvData_Trending_Silverr").find_elements(By.TAG_NAME, "tr"):
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) >= 3 and "SILVER" in cols[0].text.upper():
                        nums = re.findall(r'\b\d{5,7}\b', cols[2].text.replace(',', ''))
                        if nums:
                            silver_rate = int(nums[0]) + silver_margin
                            break
                if silver_rate != "Not Found": break
            except StaleElementReferenceException:
                time.sleep(2)

        log_msg("⏳ Fetching Gold rates...")
        driver.get("https://www.safaribullions.com/")
        time.sleep(6)

        for _ in range(3):
            try:
                for row in driver.find_element(By.ID, "gvData_Trending").find_elements(By.TAG_NAME, "tr"):
                    row_text = row.text.upper()
                    if "GOLD" in row_text and "995" in row_text:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) >= 3:
                            nums = re.findall(r'\b\d{5,7}\b', cols[2].text.replace(',', ''))
                            if nums:
                                gold_rate = int(nums[0]) + gold_margin
                                break
                        else:
                            nums = re.findall(r'\b\d{5,7}\b', row_text.replace(',', ''))
                            if len(nums) >= 2:
                                gold_rate = int(nums[1]) + gold_margin
                                break
                if gold_rate != "Not Found": break
            except StaleElementReferenceException:
                time.sleep(2)
    except Exception as e:
        log_msg(f"⚠️ Scraping Error: {e}")
    finally:
        driver.quit()
        log_msg("🛑 Chrome browser closed.")

    return silver_rate, gold_rate


# ---------------------------------------------------------------------------
# Scheduling + WhatsApp layer
# ---------------------------------------------------------------------------
def reset_daily_counter_if_needed():
    today = datetime.date.today().isoformat()
    with state_lock:
        if bot_state["jobs_date"] != today:
            bot_state["jobs_date"] = today
            bot_state["jobs_completed"] = successful_count_today()
            log_msg("New day detected. Daily sent counter reset.")


def build_message(s_rate, g_rate, shift_name):
    gold_22 = round(g_rate * 0.92, 2)
    return (
        f"*{shift_name.upper()}*\n\n"
        f"*SILVER RATE* : ₹ {s_rate} /kg\n"
        f"*GOLD RATE (24kt)* : ₹ {g_rate} /10 gm\n"
        f"*GOLD RATE (22kt)* : ₹ {gold_22} /10 gm\n\n"
        "_Generated by Bot_"
    )


def execute_job(group_name, s_margin, g_margin, shift_name):
    reset_daily_counter_if_needed()
    log_msg(f"⏰ SCHEDULE ALERT! Starting {shift_name} process...")

    s_rate, g_rate = fetch_rates(s_margin, g_margin)
    with state_lock:
        bot_state["latest_rates"] = {
            "silver": s_rate,
            "gold": g_rate,
            "checked_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    if s_rate == "Not Found" or g_rate == "Not Found":
        detail = "One or more website rates were not found."
        history_add(shift_name, "failed", group_name, s_rate, g_rate, detail)
        log_msg(f"❌ {shift_name} cancelled because one or more rates were not found.")
        return

    msg_text = build_message(s_rate, g_rate, shift_name)
    log_msg("Sending WhatsApp message through hidden Selenium browser...")
    success, info = whatsapp.send_message(group_name, msg_text)

    if success:
        history_add(shift_name, "success", group_name, s_rate, g_rate, info)
        with state_lock:
            bot_state["jobs_completed"] = successful_count_today()
            bot_state["last_send"] = {
                "at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "shift": shift_name,
                "group": group_name,
                "silver": s_rate,
                "gold": g_rate,
            }
        log_msg(f"✅ Message sent successfully. Today's successful updates: {bot_state['jobs_completed']}")
    else:
        history_add(shift_name, "failed", group_name, s_rate, g_rate, info)
        log_msg(f"❌ WhatsApp send failed: {info}")


def configure_schedule(data):
    schedule.clear("gold_silver_bot")
    group_name = data["group_name"]
    s_m, g_m = int(data["s_margin"]), int(data["g_margin"])
    t1, t2, t3 = data["time1"], data["time2"], data["time3"]

    schedule.every().day.at(t1).do(execute_job, group_name, s_m, g_m, "Morning Update").tag("gold_silver_bot")
    schedule.every().day.at(t2).do(execute_job, group_name, s_m, g_m, "Afternoon Update").tag("gold_silver_bot")
    schedule.every().day.at(t3).do(execute_job, group_name, s_m, g_m, "Evening Update").tag("gold_silver_bot")
    log_msg(f"✅ Daily schedule set for {t1}, {t2}, {t3}.")


def scheduler_loop():
    log_msg("⏳ Scheduler thread is running in the background.")
    while True:
        with state_lock:
            running = bot_state["is_running"]
        if not running:
            break
        reset_daily_counter_if_needed()
        schedule.run_pending()
        time.sleep(1)
    log_msg("Scheduler thread stopped.")


def start_scheduler(data, source="manual"):
    global scheduler_thread
    if not data.get("group_name"):
        return False, "Enter the exact WhatsApp group name."

    with scheduler_thread_lock:
        with state_lock:
            if bot_state["is_running"]:
                configure_schedule(data)
                return True, "Scheduler was already running; schedule was refreshed."
            bot_state["is_running"] = True
            bot_state["jobs_date"] = datetime.date.today().isoformat()
            bot_state["jobs_completed"] = successful_count_today()

        configure_schedule(data)
        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True, name="GoldSilverScheduler")
        scheduler_thread.start()

    if source == "startup":
        log_msg("🚀 Scheduler auto-started from saved settings.")
    else:
        log_msg("🚀 Daily scheduler started.")
    return True, "Scheduler started."


def stop_scheduler():
    with state_lock:
        bot_state["is_running"] = False
    schedule.clear("gold_silver_bot")
    return True


def next_schedule_runs(settings=None):
    with state_lock:
        running = bot_state["is_running"]
    if not running:
        return []
    settings = settings or load_settings()
    now = datetime.datetime.now()
    output = []
    for key, label in (("time1", "Morning"), ("time2", "Afternoon"), ("time3", "Evening")):
        try:
            hh, mm = map(int, settings[key].split(":"))
            run_at = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if run_at <= now:
                run_at += datetime.timedelta(days=1)
            output.append({"label": label, "at": run_at.strftime("%Y-%m-%d %H:%M")})
        except Exception:
            pass
    return sorted(output, key=lambda item: item["at"])


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if _is_local_request():
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        if str(request.form.get("pin", "")).strip() == MOBILE_PIN:
            session["mobile_authenticated"] = True
            session.permanent = True
            return redirect(url_for("index"))
        error = "Incorrect access PIN."
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("mobile_authenticated", None)
    return redirect(url_for("login"))


@app.route("/")
def index():
    info = None
    if _is_local_request():
        info = {
            "url": f"http://{local_ip_address()}:5000",
            "pin": MOBILE_PIN,
        }
    return render_template("index.html", settings=load_settings(), mobile_info=info)


@app.route("/settings/save", methods=["POST"])
def settings_save():
    try:
        clean = save_settings(request.get_json(force=True))
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Invalid settings: {exc}"}), 400

    with state_lock:
        running = bot_state["is_running"]
    if running:
        configure_schedule(clean)
        log_msg("Saved settings applied to the running scheduler.")
    return jsonify({"status": "saved", "message": "Settings saved."}), 200


@app.route("/start", methods=["POST"])
def start_bot():
    try:
        data = save_settings(request.get_json(force=True))
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Invalid settings: {exc}"}), 400

    if not whatsapp.has_saved_session():
        return jsonify({"status": "error", "message": "Connect WhatsApp before starting the scheduler."}), 400

    ok, message = start_scheduler(data)
    return jsonify({"status": "started" if ok else "error", "message": message}), 200 if ok else 400


@app.route("/stop", methods=["POST"])
def stop_bot():
    stop_scheduler()
    log_msg("🛑 Bot Manually Stopped.")
    return jsonify({"status": "stopped", "message": "Scheduler stopped."}), 200


@app.route("/send-now", methods=["POST"])
def send_now():
    try:
        data = save_settings(request.get_json(force=True))
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Invalid settings: {exc}"}), 400

    if not data["group_name"]:
        return jsonify({"status": "error", "message": "Enter the exact WhatsApp group name."}), 400
    if not whatsapp.has_saved_session():
        return jsonify({"status": "error", "message": "WhatsApp has not been connected yet."}), 400

    def worker():
        execute_job(data["group_name"], data["s_margin"], data["g_margin"], "Manual Update")

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"status": "started", "message": "Manual update started in background."}), 200


@app.route("/logs", methods=["GET"])
def get_logs():
    with state_lock:
        snapshot = {
            "logs": list(bot_state["logs"]),
            "is_running": bot_state["is_running"],
            "jobs_completed": bot_state["jobs_completed"],
            "latest_rates": bot_state["latest_rates"],
            "last_send": bot_state["last_send"],
        }
    snapshot["next_runs"] = next_schedule_runs()
    return jsonify(snapshot), 200


@app.route("/history", methods=["GET"])
def get_history():
    return jsonify({"items": history_recent(request.args.get("limit", 25))}), 200


@app.route("/api/system-info", methods=["GET"])
def system_info():
    result = {
        "mobile_url": f"http://{local_ip_address()}:5000",
        "local_only_pin_visible": False,
    }
    if _is_local_request():
        result["mobile_pin"] = MOBILE_PIN
        result["local_only_pin_visible"] = True
    return jsonify(result), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/whatsapp/status", methods=["GET"])
def whatsapp_status():
    return jsonify(whatsapp.get_state()), 200


@app.route("/whatsapp/connect", methods=["POST"])
def whatsapp_connect():
    state = whatsapp.get_state().get("status")
    if state == "connecting":
        return jsonify({"status": "connecting", "message": "Login window is already open."}), 200
    whatsapp.connect_visible_async()
    return jsonify({"status": "connecting", "message": "A visible WhatsApp Web browser will open on the host PC for login."}), 200


@app.route("/whatsapp/validate", methods=["POST"])
def whatsapp_validate():
    whatsapp.validate_session_async()
    return jsonify({"status": "checking", "message": "Checking saved session in the hidden background browser."}), 200


@app.route("/whatsapp/forget", methods=["POST"])
def whatsapp_forget():
    success, message = whatsapp.forget_session()
    return jsonify({"status": "ok" if success else "busy", "message": message}), 200 if success else 409


def auto_start_saved_schedule():
    settings = load_settings()
    if settings.get("auto_start") and settings.get("group_name"):
        start_scheduler(settings, source="startup")


if __name__ == "__main__":
    no_browser = "--no-browser" in sys.argv
    ip = local_ip_address()
    print("\nGoldSilverBot V6")
    print("PC dashboard : http://127.0.0.1:5000")
    print(f"Mobile (same Wi-Fi): http://{ip}:5000")
    print(f"Mobile access PIN  : {MOBILE_PIN}\n")

    whatsapp.validate_session_async()
    threading.Timer(1.0, auto_start_saved_schedule).start()
    if not no_browser:
        threading.Timer(1.4, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)
