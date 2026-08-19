import ctypes
import json
import os
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

import psutil
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


class WhatsAppManager:
    """Persistent-profile WhatsApp Web controller.

    First login is deliberately visible so the user can scan WhatsApp's QR code.
    Normal checks and sends use a *normal* Chromium browser (not headless) that is
    created far off-screen and then hidden with the Windows API. This keeps the
    page fully rendered while preventing WhatsApp/Chrome from taking over the
    user's desktop.

    The sender intentionally does not use PyWhatKit, PyAutoGUI, OS keyboard
    automation, Puppeteer, whatsapp-web.js, or WPPConnect.
    """

    def __init__(self, data_dir: Path, log_callback=None):
        self.data_dir = Path(data_dir)
        self.profile_dir = self.data_dir / "whatsapp_profile_v5"
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

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Browser creation / Windows background hiding
    # ------------------------------------------------------------------
    @staticmethod
    def _find_chrome_binary():
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
        ]
        for path in candidates:
            if str(path) and path.exists():
                return str(path)
        return None

    @staticmethod
    def _find_edge_binary():
        candidates = [
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/Application/msedge.exe",
        ]
        for path in candidates:
            if str(path) and path.exists():
                return str(path)
        return None

    def _saved_browser_name(self):
        if not self.marker_file.exists():
            return None
        try:
            return json.loads(self.marker_file.read_text(encoding="utf-8")).get("browser")
        except Exception:
            return None

    def _choose_browser(self):
        saved = self._saved_browser_name()
        chrome = self._find_chrome_binary()
        edge = self._find_edge_binary()
        if saved == "chrome" and chrome:
            return "chrome", chrome
        if saved == "edge" and edge:
            return "edge", edge
        if chrome:
            return "chrome", chrome
        if edge:
            return "edge", edge
        # Let Selenium/ChromeDriver try its normal discovery as a final fallback.
        return "chrome", None

    def _build_options(self, browser_name: str, binary: str | None, background: bool):
        if browser_name == "edge":
            options = webdriver.EdgeOptions()
        else:
            options = webdriver.ChromeOptions()

        if binary:
            options.binary_location = binary

        options.add_argument(f"--user-data-dir={self.profile_dir.resolve()}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--log-level=3")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-features=CalculateNativeWinOcclusion")
        options.add_argument("--window-size=1600,1000")
        if background:
            # Keep the window off-screen even before the Win32 hide call runs.
            options.add_argument("--window-position=-32000,-32000")
        else:
            options.add_argument("--window-position=80,80")
        return options

    @staticmethod
    def _descendant_pids(root_pid):
        pids = {int(root_pid)} if root_pid else set()
        if not root_pid:
            return pids
        try:
            proc = psutil.Process(int(root_pid))
            pids.update(child.pid for child in proc.children(recursive=True))
        except Exception:
            pass
        return pids

    @classmethod
    def _hide_windows_for_pids(cls, pids):
        """Hide top-level Windows belonging to browser/driver process tree."""
        if os.name != "nt" or not pids:
            return
        try:
            user32 = ctypes.windll.user32
            SW_HIDE = 0
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

            def enum_proc(hwnd, lparam):
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if int(pid.value) in pids:
                    user32.ShowWindow(hwnd, SW_HIDE)
                return True

            user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
        except Exception:
            pass

    def _hide_browser_window(self, driver, service_pid=None):
        if os.name != "nt":
            return
        for _ in range(8):
            pids = self._descendant_pids(service_pid)
            self._hide_windows_for_pids(pids)
            try:
                driver.set_window_position(-32000, -32000)
            except Exception:
                pass
            time.sleep(0.20)

    def _new_driver(self, background: bool):
        browser_name, binary = self._choose_browser()
        options = self._build_options(browser_name, binary, background)
        service_pid = None

        if browser_name == "edge":
            # Selenium Manager resolves a compatible EdgeDriver automatically.
            driver = webdriver.Edge(options=options)
            try:
                service_pid = driver.service.process.pid
            except Exception:
                pass
        else:
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            try:
                service_pid = service.process.pid
            except Exception:
                pass

        try:
            driver.set_window_size(1600, 1000)
        except Exception:
            pass

        if background:
            self._hide_browser_window(driver, service_pid)
            self.log(f"WhatsApp browser started hidden in background ({browser_name}).")
        else:
            self.log(f"WhatsApp login browser opened visibly ({browser_name}).")

        # Remember which browser created the authenticated profile.
        self._active_browser_name = browser_name
        return driver

    # ------------------------------------------------------------------
    # WhatsApp page helpers
    # ------------------------------------------------------------------
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
                elements = driver.find_elements(by, value)
                if elements:
                    return True
            except Exception:
                pass
        return False

    def _wait_until_logged_in(self, driver, timeout=60):
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
    def _find_first(cls, driver, selectors, timeout=20, require_visible=False):
        deadline = time.time() + timeout
        while time.time() < deadline:
            for by, value in selectors:
                try:
                    elements = driver.find_elements(by, value)
                    for element in elements:
                        if not require_visible or cls._visible(element):
                            return element
                except Exception:
                    pass
            time.sleep(0.30)
        return None

    def _find_search_box(self, driver, timeout=25):
        selectors = [
            (By.CSS_SELECTOR, "#side [contenteditable='true'][role='textbox']"),
            (By.CSS_SELECTOR, "#side [contenteditable='true']"),
            (By.CSS_SELECTOR, "[contenteditable='true'][aria-placeholder*='Search']"),
            (By.CSS_SELECTOR, "[contenteditable='true'][aria-label*='Search']"),
            (By.XPATH, "//*[@contenteditable='true' and contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'search')]"),
            (By.XPATH, "//*[@contenteditable='true' and contains(translate(@aria-placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'search')]"),
        ]
        element = self._find_first(driver, selectors, timeout=timeout)
        if element:
            return element

        # Keyboard shortcut fallback. Selenium sends this to the browser itself;
        # it does not use the user's physical keyboard.
        try:
            ActionChains(driver).key_down(Keys.CONTROL).key_down(Keys.ALT).send_keys("/").key_up(Keys.ALT).key_up(Keys.CONTROL).perform()
            time.sleep(1)
            active = driver.switch_to.active_element
            if active is not None:
                return active
        except Exception:
            pass
        return None

    def _find_group_result(self, driver, group_name, timeout=25):
        literal = self._xpath_literal(group_name.strip())
        selectors = [
            (By.XPATH, f"//*[@id='pane-side']//*[@title={literal}]"),
            (By.XPATH, f"//*[@id='pane-side']//*[@aria-label={literal}]"),
            (By.XPATH, f"//*[@id='pane-side']//*[normalize-space(text())={literal}]"),
            (By.XPATH, f"//*[@title={literal}]"),
            (By.XPATH, f"//*[normalize-space(text())={literal}]"),
        ]
        return self._find_first(driver, selectors, timeout=timeout)

    def _click_group_result(self, driver, result):
        attempts = [result]
        try:
            ancestors = driver.execute_script(r"""
                const out=[]; let p=arguments[0];
                for(let i=0;p && i<10;i++,p=p.parentElement){
                    if(p.getAttribute && (
                       p.getAttribute('role')==='row' ||
                       p.getAttribute('role')==='listitem' ||
                       p.hasAttribute('tabindex'))) out.push(p);
                }
                return out;
            """, result) or []
            attempts.extend(ancestors)
        except Exception:
            pass

        for element in attempts:
            for method in ("native", "action", "js"):
                try:
                    if method == "native":
                        element.click()
                    elif method == "action":
                        ActionChains(driver).move_to_element(element).click().perform()
                    else:
                        driver.execute_script("arguments[0].click();", element)
                    time.sleep(1.2)
                    if driver.find_elements(By.CSS_SELECTOR, "#main"):
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
        ]
        return self._find_first(driver, selectors, timeout=timeout) is not None

    @staticmethod
    def _is_composer_candidate(driver, element):
        if element is None:
            return False
        try:
            return bool(driver.execute_script(r"""
                const el=arguments[0];
                if(!el) return false;
                const ce=(el.getAttribute('contenteditable')||'').toLowerCase();
                const role=(el.getAttribute('role')||'').toLowerCase();
                const lexical=(el.getAttribute('data-lexical-editor')||'').toLowerCase();
                const main=document.querySelector('#main');
                const inMain=main ? main.contains(el) : true;
                const r=el.getBoundingClientRect();
                return inMain && r.width>40 && r.height>8 &&
                       (ce==='true' || role==='textbox' || lexical==='true');
            """, element))
        except Exception:
            return False

    def _find_message_box(self, driver, timeout=25):
        selectors = [
            (By.CSS_SELECTOR, "#main footer [contenteditable='true'][role='textbox']"),
            (By.CSS_SELECTOR, "#main footer [contenteditable='true']"),
            (By.CSS_SELECTOR, "#main [contenteditable='true'][role='textbox']"),
            (By.CSS_SELECTOR, "#main [data-lexical-editor='true']"),
            (By.CSS_SELECTOR, "#main div[data-tab='10'][contenteditable='true']"),
            (By.CSS_SELECTOR, "#main div[data-tab='10']"),
            (By.CSS_SELECTOR, "footer [contenteditable='true'][role='textbox']"),
            (By.CSS_SELECTOR, "footer [contenteditable='true']"),
            (By.CSS_SELECTOR, "[contenteditable='true'][aria-placeholder*='message']"),
            (By.CSS_SELECTOR, "[contenteditable='true'][aria-label*='message']"),
        ]
        deadline = time.time() + timeout
        while time.time() < deadline:
            for by, selector in selectors:
                try:
                    for element in driver.find_elements(by, selector):
                        if self._is_composer_candidate(driver, element):
                            return element
                except Exception:
                    pass

            # Layout fallback: choose the lowest wide editable element in #main.
            try:
                element = driver.execute_script(r"""
                    const main=document.querySelector('#main');
                    if(!main) return null;
                    const vh=window.innerHeight||1000;
                    const vw=window.innerWidth||1600;
                    const nodes=Array.from(main.querySelectorAll(
                      '[contenteditable="true"], [role="textbox"], [data-lexical-editor="true"]'
                    ));
                    const scored=[];
                    for(const el of nodes){
                      const r=el.getBoundingClientRect();
                      if(r.width<80 || r.height<8) continue;
                      if(r.top < vh*0.45 || r.left < vw*0.25) continue;
                      scored.push({el,score:r.top*10+r.width});
                    }
                    scored.sort((a,b)=>b.score-a.score);
                    return scored.length ? scored[0].el : null;
                """)
                if self._is_composer_candidate(driver, element):
                    return element
            except Exception:
                pass
            time.sleep(0.4)

        # Focus-walking fallback: TAB through page controls and inspect activeElement.
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            body.click()
            for _ in range(45):
                ActionChains(driver).send_keys(Keys.TAB).perform()
                active = driver.switch_to.active_element
                if self._is_composer_candidate(driver, active):
                    return active
        except Exception:
            pass

        # Coordinate fallback: normal (non-headless) Chromium has a fully rendered
        # layout, so hit-test several points in the bottom-right composer region.
        try:
            for x_frac, y_offset in ((0.70, 55), (0.62, 55), (0.76, 75), (0.58, 72)):
                element = driver.execute_script(r"""
                    const x=(window.innerWidth||1600)*arguments[0];
                    const y=(window.innerHeight||1000)-arguments[1];
                    let el=document.elementFromPoint(x,y);
                    if(!el) return null;
                    let candidate=el.closest('[contenteditable="true"],[role="textbox"],[data-lexical-editor="true"]');
                    if(!candidate && el.querySelector)
                      candidate=el.querySelector('[contenteditable="true"],[role="textbox"],[data-lexical-editor="true"]');
                    candidate=candidate||el;
                    try { candidate.focus(); candidate.click(); } catch(e) {}
                    return document.activeElement || candidate;
                """, x_frac, y_offset)
                if self._is_composer_candidate(driver, element):
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
        except Exception:
            pass

    @staticmethod
    def _send_keys_safely(driver, element, message):
        try:
            driver.execute_script("arguments[0].focus();", element)
        except Exception:
            pass
        try:
            element.click()
        except Exception:
            pass

        target = element
        try:
            active = driver.switch_to.active_element
            if active is not None:
                target = active
        except Exception:
            pass

        lines = message.splitlines() or [message]
        for index, line in enumerate(lines):
            if line:
                try:
                    # Naya JS Logic jo emojis (Non-BMP characters) ko support karta hai
                    driver.execute_script("document.execCommand('insertText', false, arguments[0]);", line)
                except Exception:
                    # Agar JS fail ho jaye toh emojis hata kar send karega
                    safe_line = "".join(c for c in line if ord(c) <= 0xFFFF)
                    target.send_keys(safe_line)
                    
            if index < len(lines) - 1:
                target.send_keys(Keys.SHIFT, Keys.ENTER)
        target.send_keys(Keys.ENTER)

    # ------------------------------------------------------------------
    # Public operations
    # ------------------------------------------------------------------
    def connect_visible(self, timeout=300):
        if not self._lock.acquire(blocking=False):
            return False, "WhatsApp is busy. Please try again in a moment."
        driver = None
        try:
            self._set_state("connecting", "Complete WhatsApp linking in the browser window that opened.")
            self.log("Opening WhatsApp Web for first-time/reconnect login...")
            driver = self._new_driver(background=False)
            driver.get("https://web.whatsapp.com/")

            if self._wait_until_logged_in(driver, timeout=timeout):
                time.sleep(6)
                browser_name = getattr(self, "_active_browser_name", "chrome")
                self.marker_file.write_text(
                    json.dumps({"linked_at": datetime.now().isoformat(), "browser": browser_name}, indent=2),
                    encoding="utf-8",
                )
                self._set_state("connected", "WhatsApp is connected. Future sends will run in a hidden browser.")
                self.log("WhatsApp login successful. Session saved for hidden background use.")
                return True, "WhatsApp connected successfully."

            self._set_state("not_connected", "WhatsApp login was not completed within the allowed time.")
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
        threading.Thread(target=self.connect_visible, daemon=True).start()
        return True

    def validate_session(self, timeout=45):
        if not self.marker_file.exists():
            self._set_state("not_connected", "WhatsApp has not been connected yet.")
            return False
        if not self._lock.acquire(blocking=False):
            return self.get_state().get("status") == "connected"

        driver = None
        try:
            self._set_state("checking", "Checking saved WhatsApp session in hidden background browser...")
            driver = self._new_driver(background=True)
            driver.get("https://web.whatsapp.com/")
            if self._wait_until_logged_in(driver, timeout=timeout):
                self._set_state("connected", "Saved WhatsApp session is valid.")
                self.log("WhatsApp hidden background session verified.")
                return True

            debug_base = self._save_diagnostics(driver, "session_not_logged_in")
            self._set_state("disconnected", "Saved session is no longer valid. Reconnect WhatsApp.")
            self.log(f"WhatsApp session expired/logged out. Diagnostics: {debug_base}")
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
        if self.marker_file.exists():
            threading.Thread(target=self.validate_session, daemon=True).start()

    def send_message(self, group_name: str, message: str, timeout=70):
        if not group_name or not group_name.strip():
            return False, "WhatsApp group name is blank."
        if not self.marker_file.exists():
            self._set_state("not_connected", "Connect WhatsApp before sending messages.")
            return False, "WhatsApp is not connected."

        group_name = group_name.strip()
        with self._lock:
            driver = None
            try:
                self._set_state("sending", f"Sending to '{group_name}' using hidden Selenium browser...")
                self.log("Starting hidden (non-headless) WhatsApp Web sender...")
                driver = self._new_driver(background=True)
                driver.get("https://web.whatsapp.com/")

                if not self._wait_until_logged_in(driver, timeout=45):
                    debug_base = self._save_diagnostics(driver, "send_session_invalid")
                    self._set_state("disconnected", "Saved session expired or was logged out. Reconnect WhatsApp.")
                    return False, f"WhatsApp session is not valid. Diagnostics: {debug_base}"

                time.sleep(3)
                search_box = self._find_search_box(driver, timeout=25)
                if search_box is None:
                    debug_base = self._save_diagnostics(driver, "search_box_not_found")
                    raise RuntimeError(f"WhatsApp search box could not be found. Diagnostics: {debug_base}")

                self._clear_editable(search_box)
                search_box.send_keys(group_name)
                time.sleep(2.5)

                result = self._find_group_result(driver, group_name, timeout=25)
                if result is None:
                    debug_base = self._save_diagnostics(driver, "group_not_found")
                    raise RuntimeError(
                        f"WhatsApp group '{group_name}' was not found. Check its exact name. Diagnostics: {debug_base}"
                    )

                if not self._click_group_result(driver, result):
                    debug_base = self._save_diagnostics(driver, "group_click_failed")
                    raise RuntimeError(f"Group was found but could not be opened. Diagnostics: {debug_base}")

                # Let the fully-rendered chat pane settle before composer search.
                self._chat_header_matches(driver, group_name, timeout=8)
                time.sleep(3)

                message_box = self._find_message_box(driver, timeout=30)
                if message_box is None:
                    body_text = ""
                    try:
                        body_text = (driver.find_element(By.TAG_NAME, "body").text or "").lower()
                    except Exception:
                        pass
                    debug_base = self._save_diagnostics(driver, "message_box_not_found")
                    read_only_hints = (
                        "only admins can send messages",
                        "you can't send messages",
                        "you cannot send messages",
                        "no longer a participant",
                        "not a participant",
                    )
                    if any(hint in body_text for hint in read_only_hints):
                        raise RuntimeError(
                            f"Chat '{group_name}' is open but this account cannot send to it. Diagnostics: {debug_base}"
                        )
                    raise RuntimeError(
                        f"Chat '{group_name}' opened but the composer could not be focused. Diagnostics: {debug_base}"
                    )

                self._send_keys_safely(driver, message_box, message)
                time.sleep(3)
                self._set_state("connected", f"Message sent to '{group_name}'.")
                self.log(f"WhatsApp message sent in hidden background browser to: {group_name}")
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
