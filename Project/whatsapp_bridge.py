import atexit
import json
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


class WhatsAppBridge:
    def __init__(self, base_dir: Path, log_callback=None, port=3001):
        self.base_dir = Path(base_dir)
        self.service_dir = self.base_dir / "whatsapp_service"
        self.port = int(port)
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.log = log_callback or (lambda _msg: None)
        self.process = None
        self._lock = threading.Lock()
        atexit.register(self.stop)

    def _request(self, method, endpoint, payload=None, timeout=30):
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            f"{self.base_url}{endpoint}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                return response.status, json.loads(body or "{}")
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read().decode("utf-8") or "{}")
            except Exception:
                body = {"error": str(exc)}
            return exc.code, body

    def _is_alive(self):
        try:
            status, data = self._request("GET", "/health", timeout=1.5)
            return status == 200 and data.get("ok") is True
        except Exception:
            return False

    def _pipe_logs(self, stream):
        if stream is None:
            return
        for raw in iter(stream.readline, ""):
            line = raw.strip()
            if line:
                self.log(f"[WhatsApp Service] {line}")

    def start(self, wait=True):
        if self._is_alive():
            return True, "WhatsApp background service is already running."

        with self._lock:
            if self._is_alive():
                return True, "WhatsApp background service is already running."

            node = shutil.which("node")
            if not node:
                return False, "Node.js was not found. Install Node.js 18 or newer, then run install.bat again."

            bridge_file = self.service_dir / "bridge.js"
            node_modules = self.service_dir / "node_modules"
            if not bridge_file.exists():
                return False, f"WhatsApp service file is missing: {bridge_file}"
            if not node_modules.exists():
                return False, "WhatsApp Node dependencies are not installed. Run install.bat first."

            creationflags = 0
            startupinfo = None
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags = subprocess.CREATE_NO_WINDOW
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            try:
                self.process = subprocess.Popen(
                    [node, str(bridge_file)],
                    cwd=str(self.service_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=creationflags,
                    startupinfo=startupinfo,
                )
            except Exception as exc:
                return False, f"Could not start WhatsApp service: {exc}"

            threading.Thread(target=self._pipe_logs, args=(self.process.stdout,), daemon=True).start()

        if not wait:
            return True, "WhatsApp background service is starting."

        deadline = time.time() + 25
        while time.time() < deadline:
            if self._is_alive():
                return True, "WhatsApp background service started."
            if self.process and self.process.poll() is not None:
                return False, f"WhatsApp service exited with code {self.process.returncode}. Check the logs above."
            time.sleep(0.4)
        return False, "WhatsApp service did not become ready within 25 seconds."

    def status(self):
        ok, message = self.start(wait=False)
        if not ok:
            return {"status": "service_error", "lastError": message, "qr": None}
        try:
            code, data = self._request("GET", "/status", timeout=6)
            if code == 200:
                return data
            return {"status": "service_error", "lastError": data.get("error", "Status check failed."), "qr": None}
        except Exception as exc:
            return {"status": "starting", "lastError": str(exc), "qr": None}

    def connect(self):
        ok, message = self.start(wait=True)
        if not ok:
            return False, message
        try:
            code, data = self._request("POST", "/connect", {}, timeout=10)
            return code == 200, data
        except Exception as exc:
            return False, str(exc)

    def groups(self):
        ok, message = self.start(wait=True)
        if not ok:
            return False, message
        try:
            code, data = self._request("GET", "/groups", timeout=60)
            if code == 200 and data.get("ok"):
                return True, data.get("groups", [])
            return False, data.get("error", "Could not load WhatsApp groups.")
        except Exception as exc:
            return False, str(exc)

    def send_message(self, group_id, message):
        ok, info = self.start(wait=True)
        if not ok:
            return False, info
        try:
            code, data = self._request(
                "POST",
                "/send",
                {"chatId": group_id, "message": message},
                timeout=90,
            )
            if code == 200 and data.get("ok"):
                return True, data
            return False, data.get("error", "WhatsApp send failed.")
        except Exception as exc:
            return False, str(exc)

    def restart(self):
        try:
            code, data = self._request("POST", "/restart", {}, timeout=10)
            return code == 200, data
        except Exception as exc:
            return False, str(exc)

    def logout(self):
        try:
            code, data = self._request("POST", "/logout", {}, timeout=30)
            return code == 200, data
        except Exception as exc:
            return False, str(exc)

    def stop(self):
        process = self.process
        if not process or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
