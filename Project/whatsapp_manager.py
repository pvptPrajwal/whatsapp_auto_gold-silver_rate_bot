import json
import os
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


class WhatsAppManager:
    """Persistent-profile Selenium controller for WhatsApp Web.

    First-time authentication is performed in a visible Chrome window. Later
    validation and message sending use the same Chrome profile in headless mode.
    """

    def __init__(self, data_dir: Path, log_callback=None):
        self.data_dir = Path(data_dir)
        self.profile_dir = self.data_dir / "whatsapp_profile"
        self.marker_file = self.data_dir / "whatsapp_linked.json"
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.log = log_callback or (lambda msg: None)
        self._lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._state = {
            "status": "unknown" if self.marker_file.exists() else "not_connected",
            "message": "Session not checked yet." if self.marker_file.exists() else "WhatsApp has not been connected yet.",
            "last_checked": None,
        }

    def _set_state(self, status, message):
        with self._state_lock:
            self._state = {
                "status": status,
                "message": message,
                "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

    def get_state(self):
        with self._state_lock:
            return dict(self._state)

    def has_saved_session(self):
        return self.marker_file.exists()

    def _options(self, headless: bool):
        options = webdriver.ChromeOptions()
        options.add_argument(f"--user-data-dir={self.profile_dir.resolve()}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--log-level=3")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--window-size=1440,1000")
        if headless:
            options.add_argument("--headless=new")
        return options

    def _new_driver(self, headless: bool):
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=self._options(headless))

    @staticmethod
    def _logged_in(driver):
        selectors = [
            (By.ID, "pane-side"),
            (By.CSS_SELECTOR, "div[aria-label='Chat list']"),
            (By.CSS_SELECTOR, "div[data-testid='chat-list']"),
        ]
        for by, value in selectors:
            try:
                if driver.find_elements(by, value):
                    return True
            except Exception:
                pass
        return False

    def _wait_until_logged_in(self, driver, timeout=45):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._logged_in(driver):
                return True
            time.sleep(1)
        return False

    @staticmethod
    def _xpath_literal(text):
        if "'" not in text:
            return f"'{text}'"
        if '"' not in text:
            return f'"{text}"'
        parts = text.split("'")
        return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"

    @staticmethod
    def _find_first_visible(driver, selectors, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            for by, value in selectors:
                try:
                    for element in driver.find_elements(by, value):
                        if element.is_displayed():
                            return element
                except Exception:
                    pass
            time.sleep(0.5)
        raise RuntimeError("Required WhatsApp Web control could not be found.")

    def connect_visible(self, timeout=300):
        """Open visible WhatsApp Web once and retain its login in our profile."""
        if not self._lock.acquire(blocking=False):
            return False, "WhatsApp is busy. Please try again in a moment."

        driver = None
        try:
            self._set_state("connecting", "Complete WhatsApp linking in the Chrome window that opened.")
            self.log("Opening WhatsApp Web for first-time/reconnect login...")
            driver = self._new_driver(headless=False)
            driver.get("https://web.whatsapp.com/")

            if self._wait_until_logged_in(driver, timeout=timeout):
                self.marker_file.write_text(
                    json.dumps({"linked_at": datetime.now().isoformat()}, indent=2),
                    encoding="utf-8",
                )
                self._set_state("connected", "WhatsApp is connected and the session has been saved.")
                self.log("WhatsApp login successful. Session saved for background use.")
                time.sleep(2)
                return True, "WhatsApp connected successfully."

            self._set_state("not_connected", "WhatsApp login was not completed within the allowed time.")
            self.log("WhatsApp login was not completed.")
            return False, "Login was not completed."
        except Exception as exc:
            self._set_state("error", f"WhatsApp login error: {exc}")
            self.log(f"WhatsApp login error: {exc}")
            return False, str(exc)
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            self._lock.release()

    def connect_visible_async(self):
        thread = threading.Thread(target=self.connect_visible, daemon=True)
        thread.start()
        return True

    def validate_session(self, timeout=30):
        if not self.marker_file.exists():
            self._set_state("not_connected", "WhatsApp has not been connected yet.")
            return False

        if not self._lock.acquire(blocking=False):
            return self.get_state().get("status") == "connected"

        driver = None
        try:
            self._set_state("checking", "Checking saved WhatsApp session in the background...")
            driver = self._new_driver(headless=True)
            driver.get("https://web.whatsapp.com/")
            if self._wait_until_logged_in(driver, timeout=timeout):
                self._set_state("connected", "Saved WhatsApp session is valid.")
                self.log("WhatsApp background session verified.")
                return True

            self._set_state("disconnected", "Saved session is no longer valid. Reconnect WhatsApp.")
            self.log("WhatsApp session expired/logged out. Reconnection required.")
            return False
        except Exception as exc:
            self._set_state("error", f"Session check failed: {exc}")
            self.log(f"WhatsApp session check failed: {exc}")
            return False
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            self._lock.release()

    def validate_session_async(self):
        if not self.marker_file.exists():
            return
        threading.Thread(target=self.validate_session, daemon=True).start()

    def send_message(self, group_name: str, message: str, timeout=60):
        if not group_name or not group_name.strip():
            return False, "WhatsApp group name is blank."
        if not self.marker_file.exists():
            self._set_state("not_connected", "Connect WhatsApp before sending messages.")
            return False, "WhatsApp is not connected."

        with self._lock:
            driver = None
            try:
                self._set_state("sending", f"Sending a message to '{group_name}' in the background...")
                self.log("Starting headless WhatsApp Web sender...")
                driver = self._new_driver(headless=True)
                driver.get("https://web.whatsapp.com/")

                if not self._wait_until_logged_in(driver, timeout=45):
                    self._set_state("disconnected", "Saved session expired or was logged out. Reconnect WhatsApp.")
                    return False, "WhatsApp session is not valid. Please reconnect."

                search_box = self._find_first_visible(
                    driver,
                    [
                        (By.XPATH, "//div[@id='side']//div[@contenteditable='true' and @role='textbox']"),
                        (By.XPATH, "//div[@contenteditable='true' and @role='textbox' and contains(@aria-label,'Search')]"),
                        (By.XPATH, "(//div[@contenteditable='true' and @role='textbox'])[1]"),
                    ],
                    timeout=20,
                )
                search_box.click()
                search_box.send_keys(Keys.CONTROL, "a")
                search_box.send_keys(Keys.BACKSPACE)
                search_box.send_keys(group_name.strip())
                time.sleep(2)

                title_literal = self._xpath_literal(group_name.strip())
                result = self._find_first_visible(
                    driver,
                    [
                        (By.XPATH, f"//span[@title={title_literal}]"),
                        (By.XPATH, f"//*[@id='pane-side']//span[normalize-space(.)={title_literal}]"),
                    ],
                    timeout=20,
                )
                driver.execute_script("arguments[0].click();", result)
                time.sleep(1.5)

                message_box = self._find_first_visible(
                    driver,
                    [
                        (By.XPATH, "//footer//div[@contenteditable='true' and @role='textbox']"),
                        (By.XPATH, "//footer//*[@contenteditable='true']"),
                    ],
                    timeout=20,
                )
                message_box.click()

                lines = message.splitlines() or [message]
                for index, line in enumerate(lines):
                    if line:
                        message_box.send_keys(line)
                    if index < len(lines) - 1:
                        message_box.send_keys(Keys.SHIFT, Keys.ENTER)
                message_box.send_keys(Keys.ENTER)
                time.sleep(2)

                self._set_state("connected", f"Message sent to '{group_name}'.")
                self.log(f"WhatsApp message sent in background to: {group_name}")
                return True, "Message sent successfully."
            except WebDriverException as exc:
                self._set_state("error", f"WhatsApp browser error: {exc.msg if hasattr(exc, 'msg') else exc}")
                return False, f"WhatsApp browser error: {exc}"
            except Exception as exc:
                self._set_state("error", f"WhatsApp send error: {exc}")
                return False, str(exc)
            finally:
                if driver is not None:
                    try:
                        driver.quit()
                    except Exception:
                        pass

    def forget_session(self):
        if not self._lock.acquire(blocking=False):
            return False, "WhatsApp is currently busy."
        try:
            if self.profile_dir.exists():
                shutil.rmtree(self.profile_dir, ignore_errors=True)
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            if self.marker_file.exists():
                self.marker_file.unlink()
            self._set_state("not_connected", "Saved WhatsApp session has been removed.")
            self.log("Saved WhatsApp session removed.")
            return True, "Saved WhatsApp session removed."
        finally:
            self._lock.release()
