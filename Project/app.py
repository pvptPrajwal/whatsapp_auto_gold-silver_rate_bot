from flask import Flask, render_template, request, jsonify
import threading
import time
import datetime
import json
import re
import schedule
import webbrowser
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import StaleElementReferenceException

from whatsapp_bridge import WhatsAppBridge

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"

bot_state = {
    "is_running": False,
    "jobs_completed": 0,
    "jobs_date": datetime.date.today().isoformat(),
    "logs": ["[SYSTEM] Server started. Ready to launch."],
}

state_lock = threading.Lock()
scheduler_thread = None


def log_msg(message):
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    with state_lock:
        bot_state["logs"].append(f"[{current_time}] {message}")
        if len(bot_state["logs"]) > 150:
            bot_state["logs"].pop(0)
    print(f"[{current_time}] {message}")


whatsapp = WhatsAppBridge(BASE_DIR, log_callback=log_msg)


def load_settings():
    defaults = {
        "group_id": "",
        "group_name": "",
        "s_margin": 0,
        "g_margin": 0,
        "time1": "10:00",
        "time2": "14:00",
        "time3": "18:00",
    }
    if not SETTINGS_FILE.exists():
        return defaults
    try:
        loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        defaults.update({k: loaded[k] for k in defaults if k in loaded})
    except Exception as exc:
        log_msg(f"Settings file could not be read: {exc}")
    return defaults


def save_settings(data):
    previous = load_settings()
    clean = {
        "group_id": str(data.get("group_id", previous.get("group_id", ""))).strip(),
        "group_name": str(data.get("group_name", previous.get("group_name", ""))).strip(),
        "s_margin": int(data.get("s_margin", previous.get("s_margin", 0))),
        "g_margin": int(data.get("g_margin", previous.get("g_margin", 0))),
        "time1": str(data.get("time1", previous.get("time1", "10:00"))),
        "time2": str(data.get("time2", previous.get("time2", "14:00"))),
        "time3": str(data.get("time3", previous.get("time3", "18:00"))),
    }
    SETTINGS_FILE.write_text(json.dumps(clean, indent=2), encoding="utf-8")
    return clean


# ---------------------------------------------------------------------------
# EXISTING RATE FETCHING LOGIC
# Intentionally kept unchanged from the user's supplied code.
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
# Scheduler + WhatsApp background bridge
# ---------------------------------------------------------------------------
def reset_daily_counter_if_needed():
    today = datetime.date.today().isoformat()
    with state_lock:
        if bot_state["jobs_date"] != today:
            bot_state["jobs_date"] = today
            bot_state["jobs_completed"] = 0
            should_log = True
        else:
            should_log = False
    if should_log:
        log_msg("New day detected. Daily sent counter reset.")


def build_message(s_rate, g_rate, shift_name):
    gold_22 = g_rate * 0.92
    return (
        f"🎯 *{shift_name.upper()}* 🎯\n\n"
        f"🥈 *SILVER RATE* : ₹ {s_rate} /kg\n"
        f"🥇 *GOLD RATE (24kt)* : ₹ {g_rate} /10 gm\n"
        f"*GOLD RATE (22kt)* : ₹ {gold_22}/10gm \n\n"
        "_Generated by Bot 🤖_"
    )


def execute_job(group_id, group_name, s_margin, g_margin, shift_name):
    reset_daily_counter_if_needed()
    log_msg(f"⏰ SCHEDULE ALERT! Starting {shift_name} process...")

    s_rate, g_rate = fetch_rates(s_margin, g_margin)
    if s_rate == "Not Found" or g_rate == "Not Found":
        log_msg(f"❌ {shift_name} cancelled because one or more rates were not found.")
        return

    msg_text = build_message(s_rate, g_rate, shift_name)
    log_msg(f"📨 Sending WhatsApp message directly to group ID for '{group_name}'...")
    success, info = whatsapp.send_message(group_id, msg_text)

    if success:
        with state_lock:
            bot_state["jobs_completed"] += 1
            count = bot_state["jobs_completed"]
        log_msg(f"✅ Message sent successfully to '{group_name}'. Today's successful updates: {count}")
    else:
        log_msg(f"❌ WhatsApp send failed: {info}")


def run_schedule(data):
    schedule.clear("gold_silver_bot")

    group_id = data["group_id"]
    group_name = data["group_name"]
    s_m, g_m = int(data["s_margin"]), int(data["g_margin"])
    t1, t2, t3 = data["time1"], data["time2"], data["time3"]

    schedule.every().day.at(t1).do(execute_job, group_id, group_name, s_m, g_m, "Morning Update").tag("gold_silver_bot")
    schedule.every().day.at(t2).do(execute_job, group_id, group_name, s_m, g_m, "Afternoon Update").tag("gold_silver_bot")
    schedule.every().day.at(t3).do(execute_job, group_id, group_name, s_m, g_m, "Evening Update").tag("gold_silver_bot")

    log_msg(f"✅ Daily schedule set for {t1}, {t2}, {t3}.")
    log_msg(f"✅ Destination group: {group_name} ({group_id})")
    log_msg("⏳ Bot is waiting in the background. Schedule repeats every day until stopped.")

    while True:
        with state_lock:
            running = bot_state["is_running"]
        if not running:
            break
        reset_daily_counter_if_needed()
        try:
            schedule.run_pending()
        except Exception as exc:
            log_msg(f"❌ Scheduler error: {exc}")
        time.sleep(1)


# --- FLASK WEB ROUTES ---
@app.route('/')
def index():
    return render_template('index.html', settings=load_settings())


@app.route('/whatsapp/status', methods=['GET'])
def whatsapp_status():
    return jsonify(whatsapp.status())


@app.route('/whatsapp/connect', methods=['POST'])
def whatsapp_connect():
    success, info = whatsapp.connect()
    if success:
        return jsonify({"status": "starting", "message": "WhatsApp connection process started."})
    return jsonify({"status": "error", "message": str(info)}), 500


@app.route('/whatsapp/groups', methods=['GET'])
def whatsapp_groups():
    success, info = whatsapp.groups()
    if success:
        return jsonify({"status": "ok", "groups": info})
    return jsonify({"status": "error", "message": str(info)}), 409


@app.route('/whatsapp/restart', methods=['POST'])
def whatsapp_restart():
    success, info = whatsapp.restart()
    if success:
        return jsonify({"status": "restarting"})
    return jsonify({"status": "error", "message": str(info)}), 500


@app.route('/whatsapp/logout', methods=['POST'])
def whatsapp_logout():
    success, info = whatsapp.logout()
    if success:
        settings = load_settings()
        settings["group_id"] = ""
        settings["group_name"] = ""
        save_settings(settings)
        return jsonify({"status": "logged_out"})
    return jsonify({"status": "error", "message": str(info)}), 500


@app.route('/settings', methods=['POST'])
def update_settings():
    data = request.get_json(force=True)
    try:
        clean = save_settings(data)
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Invalid settings: {exc}"}), 400
    return jsonify({"status": "saved", "settings": clean})


@app.route('/start', methods=['POST'])
def start_bot():
    global scheduler_thread
    with state_lock:
        if bot_state["is_running"]:
            return jsonify({"status": "already running"}), 400

    data = request.get_json(force=True)
    try:
        data = save_settings(data)
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Invalid settings: {exc}"}), 400

    if not data["group_id"] or not data["group_name"]:
        return jsonify({"status": "error", "message": "Select a WhatsApp group first."}), 400

    wa_state = whatsapp.status().get("status")
    if wa_state != "connected":
        return jsonify({"status": "error", "message": "WhatsApp is not connected. Scan the QR code first if requested."}), 400

    with state_lock:
        bot_state["is_running"] = True
        bot_state["jobs_completed"] = 0
        bot_state["jobs_date"] = datetime.date.today().isoformat()
        bot_state["logs"] = []
    log_msg("🚀 Starting Web Bot Engine...")

    scheduler_thread = threading.Thread(target=run_schedule, args=(data,), daemon=True)
    scheduler_thread.start()
    return jsonify({"status": "started"}), 200


@app.route('/stop', methods=['POST'])
def stop_bot():
    with state_lock:
        bot_state["is_running"] = False
    schedule.clear("gold_silver_bot")
    log_msg("🛑 Bot Manually Stopped.")
    return jsonify({"status": "stopped"}), 200


@app.route('/send-now', methods=['POST'])
def send_now():
    data = request.get_json(force=True)
    try:
        data = save_settings(data)
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Invalid settings: {exc}"}), 400

    if not data["group_id"] or not data["group_name"]:
        return jsonify({"status": "error", "message": "Select a WhatsApp group first."}), 400

    if whatsapp.status().get("status") != "connected":
        return jsonify({"status": "error", "message": "WhatsApp is not connected."}), 400

    threading.Thread(
        target=execute_job,
        args=(data["group_id"], data["group_name"], int(data["s_margin"]), int(data["g_margin"]), "Manual Update"),
        daemon=True,
    ).start()
    return jsonify({"status": "started"}), 200


@app.route('/logs', methods=['GET'])
def get_logs():
    reset_daily_counter_if_needed()
    with state_lock:
        result = {
            "logs": list(bot_state["logs"]),
            "is_running": bot_state["is_running"],
            "jobs_completed": bot_state["jobs_completed"],
        }
    return jsonify(result), 200


if __name__ == "__main__":
    success, info = whatsapp.start(wait=False)
    log_msg(info)
    url = "http://127.0.0.1:5000"
    print(f"🌐 WEB SERVER RUNNING! Open {url} in your browser.")
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False, threaded=True)
