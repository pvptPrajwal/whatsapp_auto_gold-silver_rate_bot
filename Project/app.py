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

from whatsapp_manager import WhatsAppManager

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"

# --- Global State for Web Server ---
bot_state = {
    "is_running": False,
    "jobs_completed": 0,
    "jobs_date": datetime.date.today().isoformat(),
    "logs": ["[SYSTEM] Server started. Ready to launch."],
}


def log_msg(message):
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    bot_state["logs"].append(f"[{current_time}] {message}")
    if len(bot_state["logs"]) > 100:
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
    clean = {
        "group_name": str(data.get("group_name", "")).strip(),
        "s_margin": int(data.get("s_margin", 0)),
        "g_margin": int(data.get("g_margin", 0)),
        "time1": str(data.get("time1", "10:00")),
        "time2": str(data.get("time2", "14:00")),
        "time3": str(data.get("time3", "18:00")),
    }
    SETTINGS_FILE.write_text(json.dumps(clean, indent=2), encoding="utf-8")
    return clean


# ---------------------------------------------------------------------------
# EXISTING RATE FETCHING LOGIC
# Kept functionally unchanged from the code supplied by the user.
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
    if bot_state["jobs_date"] != today:
        bot_state["jobs_date"] = today
        bot_state["jobs_completed"] = 0
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

    if s_rate == "Not Found" or g_rate == "Not Found":
        log_msg(f"❌ {shift_name} cancelled because one or more rates were not found.")
        return

    msg_text = build_message(s_rate, g_rate, shift_name)
    log_msg("Sending WhatsApp message through headless Selenium...")
    success, info = whatsapp.send_message(group_name, msg_text)

    if success:
        bot_state["jobs_completed"] += 1
        log_msg(f"✅ Message sent successfully. Today's successful updates: {bot_state['jobs_completed']}")
    else:
        log_msg(f"❌ WhatsApp send failed: {info}")


def run_schedule(data):
    schedule.clear("gold_silver_bot")

    group_name = data['group_name']
    s_m, g_m = int(data['s_margin']), int(data['g_margin'])
    t1, t2, t3 = data['time1'], data['time2'], data['time3']

    schedule.every().day.at(t1).do(execute_job, group_name, s_m, g_m, "Morning Update").tag("gold_silver_bot")
    schedule.every().day.at(t2).do(execute_job, group_name, s_m, g_m, "Afternoon Update").tag("gold_silver_bot")
    schedule.every().day.at(t3).do(execute_job, group_name, s_m, g_m, "Evening Update").tag("gold_silver_bot")

    log_msg(f"✅ Daily schedule set for {t1}, {t2}, {t3}.")
    log_msg("⏳ Bot is waiting in the background. Schedule will continue every day until stopped.")

    while bot_state["is_running"]:
        reset_daily_counter_if_needed()
        schedule.run_pending()
        time.sleep(1)


# --- FLASK WEB ROUTES ---
@app.route('/')
def index():
    return render_template('index.html', settings=load_settings())


@app.route('/start', methods=['POST'])
def start_bot():
    if bot_state["is_running"]:
        return jsonify({"status": "already running"}), 400

    data = request.get_json(force=True)
    try:
        data = save_settings(data)
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Invalid settings: {exc}"}), 400

    if not data["group_name"]:
        return jsonify({"status": "error", "message": "Enter the exact WhatsApp group name."}), 400

    wa_state = whatsapp.get_state().get("status")
    if wa_state not in ("connected",):
        return jsonify({"status": "error", "message": "Connect and verify WhatsApp before starting the bot."}), 400

    bot_state["is_running"] = True
    bot_state["jobs_completed"] = 0
    bot_state["jobs_date"] = datetime.date.today().isoformat()
    bot_state["logs"] = []
    log_msg("🚀 Starting Web Bot Engine...")

    threading.Thread(target=run_schedule, args=(data,), daemon=True).start()
    return jsonify({"status": "started"}), 200


@app.route('/stop', methods=['POST'])
def stop_bot():
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

    if not data["group_name"]:
        return jsonify({"status": "error", "message": "Enter the exact WhatsApp group name."}), 400
    if whatsapp.get_state().get("status") != "connected":
        return jsonify({"status": "error", "message": "WhatsApp is not connected."}), 400

    def worker():
        execute_job(data["group_name"], data["s_margin"], data["g_margin"], "Manual Update")

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"status": "started", "message": "Manual update started in background."}), 200


@app.route('/logs', methods=['GET'])
def get_logs():
    return jsonify({
        "logs": bot_state["logs"],
        "is_running": bot_state["is_running"],
        "jobs_completed": bot_state["jobs_completed"],
    }), 200


@app.route('/whatsapp/status', methods=['GET'])
def whatsapp_status():
    return jsonify(whatsapp.get_state()), 200


@app.route('/whatsapp/connect', methods=['POST'])
def whatsapp_connect():
    state = whatsapp.get_state().get("status")
    if state == "connecting":
        return jsonify({"status": "connecting", "message": "Login window is already open."}), 200
    whatsapp.connect_visible_async()
    return jsonify({"status": "connecting", "message": "Chrome will open for WhatsApp login. Complete the QR/device linking there."}), 200


@app.route('/whatsapp/validate', methods=['POST'])
def whatsapp_validate():
    whatsapp.validate_session_async()
    return jsonify({"status": "checking", "message": "Checking saved session in background."}), 200


@app.route('/whatsapp/forget', methods=['POST'])
def whatsapp_forget():
    success, message = whatsapp.forget_session()
    return jsonify({"status": "ok" if success else "busy", "message": message}), 200 if success else 409


if __name__ == "__main__":
    print("🌐 WEB SERVER RUNNING! Open http://127.0.0.1:5000 in your browser.")
    whatsapp.validate_session_async()
    threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(debug=False, port=5000, use_reloader=False)
