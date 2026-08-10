import json
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


class WhatsAppManager:
    """Persistent-profile Selenium controller for WhatsApp Web.

    First-time authentication is performed in a visible Chrome window. Later
    validation and message sending use the same Chrome profile in headless mode.

    IMPORTANT: WhatsApp Web is not a stable public DOM API. The sender therefore
    uses multiple selectors plus layout-based fallbacks and saves diagnostics
    whenever a control cannot be found.
    """

    def __init__(self, data_dir: Path, log_callback=None):
        self.data_dir = Path(data_dir)
        self.profile_dir = self.data_dir / "whatsapp_profile"
        self.debug_dir = self.data_dir / "whatsapp_debug"
        self.marker_file = self.data_dir / "whatsapp_linked.json"
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.debug_dir.mkdir(parents=True, exist_ok=True)
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
        options.add_argument("--window-size=1600,1000")
        if headless:
            options.add_argument("--headless=new")
        return options

    def _new_driver(self, headless: bool):
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=self._options(headless))
        try:
            driver.set_window_size(1600, 1000)
        except Exception:
            pass
        return driver

    @staticmethod
    def _visible(element):
        try:
            return element.is_displayed() and element.is_enabled()
        except Exception:
            return False

    @classmethod
    def _logged_in(cls, driver):
        selectors = [
            (By.ID, "pane-side"),
            (By.CSS_SELECTOR, "#pane-side"),
            (By.CSS_SELECTOR, "div[aria-label='Chat list']"),
            (By.CSS_SELECTOR, "div[data-testid='chat-list']"),
        ]
        for by, value in selectors:
            try:
                if any(cls._visible(e) for e in driver.find_elements(by, value)):
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

    def _save_diagnostics(self, driver, stage):
        """Save screenshot + HTML so a future WhatsApp DOM change is debuggable."""
        safe_stage = "".join(c if c.isalnum() or c in "-_" else "_" for c in stage)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = self.debug_dir / f"{stamp}_{safe_stage}"
        try:
            driver.save_screenshot(str(base) + ".png")
        except Exception:
            pass
        try:
            Path(str(base) + ".html").write_text(driver.page_source, encoding="utf-8", errors="ignore")
        except Exception:
            pass
        try:
            Path(str(base) + ".txt").write_text(
                f"URL: {driver.current_url}\nTitle: {driver.title}\nStage: {stage}\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        return str(base)

    @classmethod
    def _find_first_visible(cls, driver, selectors, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            for by, value in selectors:
                try:
                    for element in driver.find_elements(by, value):
                        if cls._visible(element):
                            return element
                except Exception:
                    pass
            time.sleep(0.35)
        return None

    @classmethod
    def _visible_editables(cls, driver):
        result = []
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true']")
        except Exception:
            return result
        for element in elements:
            if not cls._visible(element):
                continue
            try:
                rect = element.rect
                result.append((element, rect))
            except Exception:
                pass
        return result

    def _find_search_box(self, driver, timeout=25):
        selectors = [
            (By.CSS_SELECTOR, "#side [contenteditable='true'][role='textbox']"),
            (By.XPATH, "//*[@id='side']//*[@contenteditable='true' and @role='textbox']"),
            (By.CSS_SELECTOR, "[contenteditable='true'][aria-placeholder*='Search']"),
            (By.CSS_SELECTOR, "[contenteditable='true'][aria-label*='Search']"),
            (By.XPATH, "//*[@contenteditable='true' and contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'search')]"),
            (By.XPATH, "//*[@contenteditable='true' and contains(translate(@aria-placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'search')]"),
        ]
        element = self._find_first_visible(driver, selectors, timeout=timeout)
        if element:
            return element

        # Fallback 1: use WhatsApp Web's search shortcut, then inspect active element.
        try:
            ActionChains(driver).key_down(Keys.CONTROL).key_down(Keys.ALT).send_keys("/").key_up(Keys.ALT).key_up(Keys.CONTROL).perform()
            time.sleep(1)
            active = driver.switch_to.active_element
            if active is not None and self._visible(active):
                editable = (active.get_attribute("contenteditable") or "").lower()
                role = (active.get_attribute("role") or "").lower()
                if editable == "true" or role == "textbox":
                    return active
        except Exception:
            pass

        # Fallback 2: search boxes are normally in the left/top part of the UI.
        try:
            width = driver.execute_script("return window.innerWidth") or 1600
            height = driver.execute_script("return window.innerHeight") or 1000
        except Exception:
            width, height = 1600, 1000
        candidates = []
        for element, rect in self._visible_editables(driver):
            x, y = rect.get("x", 0), rect.get("y", 0)
            w, h = rect.get("width", 0), rect.get("height", 0)
            if x < width * 0.45 and y < height * 0.40 and w > 80 and h > 15:
                candidates.append((y, x, -w, element))
        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1], item[2]))
            return candidates[0][3]
        return None

    def _find_group_result(self, driver, group_name, timeout=25):
        literal = self._xpath_literal(group_name.strip())
        selectors = [
            (By.XPATH, f"//*[@id='pane-side']//*[@title={literal}]"),
            (By.XPATH, f"//*[@id='pane-side']//*[@aria-label={literal}]"),
            (By.XPATH, f"//*[@id='pane-side']//*[normalize-space(text())={literal}]"),
            (By.XPATH, f"//*[@title={literal}]"),
            (By.XPATH, f"//*[@aria-label={literal}]"),
            (By.XPATH, f"//*[normalize-space(text())={literal}]"),
        ]
        return self._find_first_visible(driver, selectors, timeout=timeout)

    def _click_group_result(self, driver, result):
        """Click a search result using native and ancestor fallbacks."""
        attempts = [result]
        try:
            ancestors = driver.execute_script(r"""
                const el = arguments[0];
                const out = [];
                let p = el;
                for (let i = 0; p && i < 8; i++, p = p.parentElement) {
                    if (p.getAttribute && (
                        p.getAttribute('role') === 'row' ||
                        p.getAttribute('role') === 'listitem' ||
                        p.hasAttribute('data-testid') ||
                        p.hasAttribute('tabindex')
                    )) out.push(p);
                }
                return out;
            """, result) or []
            attempts.extend(ancestors)
        except Exception:
            pass

        for el in attempts:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            except Exception:
                pass
            try:
                el.click()
                time.sleep(1.2)
                return True
            except Exception:
                pass
            try:
                ActionChains(driver).move_to_element(el).click().perform()
                time.sleep(1.2)
                return True
            except Exception:
                pass
            try:
                driver.execute_script("arguments[0].click();", el)
                time.sleep(1.2)
                return True
            except Exception:
                pass
        return False

    def _chat_header_matches(self, driver, group_name, timeout=12):
        literal = self._xpath_literal(group_name.strip())
        selectors = [
            (By.XPATH, f"//*[@id='main']//header//*[@title={literal}]"),
            (By.XPATH, f"//*[@id='main']//header//*[@aria-label={literal}]"),
            (By.XPATH, f"//*[@id='main']//header//*[normalize-space(text())={literal}]"),
            (By.XPATH, f"//*[@id='main']//*[@title={literal}]"),
        ]
        return self._find_first_visible(driver, selectors, timeout=timeout) is not None

    @staticmethod
    def _send_keys_safely(driver, element, message):
        """Focus the composer and type multiline text without OS-level input."""
        try:
            driver.execute_script("arguments[0].focus();", element)
        except Exception:
            pass
        try:
            element.click()
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", element)
            except Exception:
                pass

        active = None
        try:
            active = driver.switch_to.active_element
        except Exception:
            pass
        target = active if active is not None else element

        lines = message.splitlines() or [message]
        for index, line in enumerate(lines):
            if line:
                target.send_keys(line)
            if index < len(lines) - 1:
                target.send_keys(Keys.SHIFT, Keys.ENTER)
        target.send_keys(Keys.ENTER)

    def _find_message_box(self, driver, timeout=35):
        # WhatsApp Web changes attributes frequently. Keep this intentionally
        # broad, but restrict matches to the active chat / lower-right area.
        selectors = [
            (By.CSS_SELECTOR, "#main footer div[contenteditable='true'][role='textbox']"),
            (By.CSS_SELECTOR, "#main footer [contenteditable='true']"),
            (By.CSS_SELECTOR, "#main [contenteditable='true'][role='textbox']"),
            (By.CSS_SELECTOR, "#main [role='textbox'][contenteditable='true']"),
            (By.CSS_SELECTOR, "#main [data-lexical-editor='true']"),
            (By.CSS_SELECTOR, "#main div[data-tab='10'][contenteditable='true']"),
            (By.CSS_SELECTOR, "#main div[data-tab='10']"),
            (By.CSS_SELECTOR, "footer [contenteditable='true'][role='textbox']"),
            (By.CSS_SELECTOR, "footer [contenteditable='true']"),
            (By.CSS_SELECTOR, "[contenteditable='true'][aria-placeholder*='Type a message']"),
            (By.CSS_SELECTOR, "[contenteditable='true'][aria-label*='Type a message']"),
            (By.XPATH, "//*[@contenteditable='true' and contains(translate(@aria-placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'message')]"),
            (By.XPATH, "//*[@contenteditable='true' and contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'message')]"),
        ]
        element = self._find_first_visible(driver, selectors, timeout=timeout)
        if element:
            return element

        # JavaScript fallback. This is deliberately independent of WhatsApp's
        # generated class names and scores editable/textbox elements by their
        # position. The composer is normally the lowest wide textbox in the
        # right-hand chat pane.
        try:
            element = driver.execute_script(r"""
                const vw = window.innerWidth || 1600;
                const vh = window.innerHeight || 1000;
                const nodes = Array.from(document.querySelectorAll(
                    '#main [contenteditable], #main [role="textbox"], footer [contenteditable], footer [role="textbox"], [data-lexical-editor="true"]'
                ));
                const candidates = [];
                for (const el of nodes) {
                    const ce = (el.getAttribute('contenteditable') || '').toLowerCase();
                    const role = (el.getAttribute('role') || '').toLowerCase();
                    const lexical = (el.getAttribute('data-lexical-editor') || '').toLowerCase();
                    if (!(ce && ce !== 'false') && role !== 'textbox' && lexical !== 'true') continue;
                    const r = el.getBoundingClientRect();
                    const cs = getComputedStyle(el);
                    const visible = r.width > 0 && r.height > 0 &&
                        cs.display !== 'none' && cs.visibility !== 'hidden' &&
                        Number(cs.opacity || '1') > 0;
                    if (!visible) continue;
                    if (r.left < vw * 0.25 || r.top < vh * 0.45) continue;
                    if (r.width < 100 || r.height < 10) continue;
                    const score = (r.top * 2) + r.width + r.left;
                    candidates.push({el, score});
                }
                candidates.sort((a,b) => b.score - a.score);
                return candidates.length ? candidates[0].el : null;
            """)
            if element is not None:
                try:
                    if element.is_displayed():
                        return element
                except Exception:
                    return element
        except Exception:
            pass

        # Last-resort focus fallback: click the lower-right composer area and
        # inspect the active element. This remains fully headless and does not
        # use the user's physical mouse or keyboard.
        try:
            element = driver.execute_script(r"""
                const vw = window.innerWidth || 1600;
                const vh = window.innerHeight || 1000;
                const points = [
                    [vw * 0.72, vh - 52],
                    [vw * 0.68, vh - 70],
                    [vw * 0.60, vh - 55]
                ];
                for (const [x,y] of points) {
                    let el = document.elementFromPoint(x,y);
                    if (!el) continue;
                    let editable = el.closest('[contenteditable]:not([contenteditable="false"]), [role="textbox"], [data-lexical-editor="true"]');
                    if (!editable) {
                        editable = el.querySelector && el.querySelector('[contenteditable]:not([contenteditable="false"]), [role="textbox"], [data-lexical-editor="true"]');
                    }
                    if (editable) {
                        editable.focus();
                        editable.click();
                        return editable;
                    }
                    try { el.click(); } catch(e) {}
                }
                return document.activeElement;
            """)
            if element is not None:
                ce = (element.get_attribute('contenteditable') or '').lower()
                role = (element.get_attribute('role') or '').lower()
                lexical = (element.get_attribute('data-lexical-editor') or '').lower()
                if ce not in ('', 'false') or role == 'textbox' or lexical == 'true':
                    return element
        except Exception:
            pass
        return None

    @staticmethod
    def _clear_editable(element):
        try:
            element.click()
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.BACKSPACE)
            return
        except Exception:
            pass
        try:
            element.send_keys(Keys.CONTROL, "a", Keys.BACKSPACE)
        except Exception:
            pass

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
                # Give IndexedDB/local profile state time to settle before closing Chrome.
                time.sleep(5)
                self.marker_file.write_text(
                    json.dumps({"linked_at": datetime.now().isoformat()}, indent=2),
                    encoding="utf-8",
                )
                self._set_state("connected", "WhatsApp is connected and the session has been saved.")
                self.log("WhatsApp login successful. Session saved for background use.")
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

            self._save_diagnostics(driver, "session_not_logged_in")
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

        group_name = group_name.strip()

        with self._lock:
            driver = None
            try:
                self._set_state("sending", f"Sending a message to '{group_name}' in the background...")
                self.log("Starting headless WhatsApp Web sender...")
                driver = self._new_driver(headless=True)
                driver.get("https://web.whatsapp.com/")

                if not self._wait_until_logged_in(driver, timeout=45):
                    debug_base = self._save_diagnostics(driver, "send_session_invalid")
                    self._set_state("disconnected", "Saved session expired or was logged out. Reconnect WhatsApp.")
                    self.log(f"WhatsApp session invalid. Diagnostics: {debug_base}")
                    return False, "WhatsApp session is not valid. Please reconnect."

                # WhatsApp can finish drawing controls shortly after the chat list appears.
                time.sleep(2)

                search_box = self._find_search_box(driver, timeout=25)
                if search_box is None:
                    debug_base = self._save_diagnostics(driver, "search_box_not_found")
                    raise RuntimeError(
                        "WhatsApp search box could not be found. "
                        f"Diagnostic files saved under: {debug_base}"
                    )

                self._clear_editable(search_box)
                search_box.send_keys(group_name)
                time.sleep(2.5)

                result = self._find_group_result(driver, group_name, timeout=25)
                if result is None:
                    debug_base = self._save_diagnostics(driver, "group_not_found")
                    raise RuntimeError(
                        f"WhatsApp group '{group_name}' was not found after searching. "
                        "Check the group name exactly as shown in WhatsApp Web. "
                        f"Diagnostic files saved under: {debug_base}"
                    )

                if not self._click_group_result(driver, result):
                    debug_base = self._save_diagnostics(driver, "group_click_failed")
                    raise RuntimeError(
                        f"WhatsApp group '{group_name}' was found but could not be opened. "
                        f"Diagnostic files saved under: {debug_base}"
                    )

                # Wait until the right-side chat pane is actually loaded. We do
                # not treat a clicked search result as proof that the chat opened.
                if not self._chat_header_matches(driver, group_name, timeout=12):
                    # Some builds do not expose the title in the header. If #main
                    # exists, allow the composer check to decide after a short wait.
                    time.sleep(2)
                else:
                    time.sleep(1)

                message_box = self._find_message_box(driver, timeout=35)
                if message_box is None:
                    # Give a useful explanation for common read-only states.
                    body_text = ""
                    try:
                        body_text = (driver.find_element(By.TAG_NAME, "body").text or "").lower()
                    except Exception:
                        pass
                    read_only_hints = [
                        "only admins can send messages",
                        "you can't send messages",
                        "you cannot send messages",
                        "no longer a participant",
                        "not a participant",
                    ]
                    debug_base = self._save_diagnostics(driver, "message_box_not_found")
                    if any(hint in body_text for hint in read_only_hints):
                        raise RuntimeError(
                            f"Chat '{group_name}' is open, but WhatsApp currently does not allow this account to send messages in that chat. "
                            f"Diagnostic files saved under: {debug_base}"
                        )
                    raise RuntimeError(
                        f"Chat '{group_name}' opened, but the message box could not be found. "
                        f"Diagnostic files saved under: {debug_base}"
                    )

                self._send_keys_safely(driver, message_box, message)
                time.sleep(3)

                self._set_state("connected", f"Message sent to '{group_name}'.")
                self.log(f"WhatsApp message sent in background to: {group_name}")
                return True, "Message sent successfully."
            except WebDriverException as exc:
                if driver is not None:
                    self._save_diagnostics(driver, "webdriver_error")
                detail = exc.msg if hasattr(exc, "msg") else str(exc)
                self._set_state("error", f"WhatsApp browser error: {detail}")
                return False, f"WhatsApp browser error: {detail}"
            except Exception as exc:
                if driver is not None:
                    self._save_diagnostics(driver, "send_error")
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
