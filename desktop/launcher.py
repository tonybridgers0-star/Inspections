import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

try:
    import webview  # type: ignore
except Exception:
    webview = None

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"


class LauncherApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Inspection Order Manager Launcher")
        self.backend_proc: subprocess.Popen | None = None
        self.frontend_proc: subprocess.Popen | None = None

        self.status = tk.StringVar(value="Stopped")
        tk.Label(root, text="Inspection Order Manager", font=("Segoe UI", 14, "bold")).pack(pady=8)
        tk.Label(root, textvariable=self.status).pack(pady=4)

        btns = tk.Frame(root)
        btns.pack(pady=8)
        tk.Button(btns, text="Start App", command=self.start_all, width=18).grid(row=0, column=0, padx=6)
        tk.Button(btns, text="Open UI", command=self.open_ui, width=18).grid(row=0, column=1, padx=6)
        tk.Button(btns, text="Stop App", command=self.stop_all, width=18).grid(row=0, column=2, padx=6)

        tk.Label(root, text="Frontend: http://127.0.0.1:5173  |  API: http://127.0.0.1:8000", fg="#555").pack(pady=6)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _port_open(self, host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex((host, port)) == 0

    def _wait_for_port(self, port: int, timeout: float = 90.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if self._port_open("127.0.0.1", port):
                return True
            time.sleep(0.5)
        return False

    def start_all(self):
        try:
            if self.backend_proc is None or self.backend_proc.poll() is not None:
                self.backend_proc = subprocess.Popen(
                    [sys.executable, "-m", "uvicorn", "app.main:app", "--reload"],
                    cwd=str(BACKEND_DIR),
                )

            if self.frontend_proc is None or self.frontend_proc.poll() is not None:
                npm_cmd = "npm.cmd" if sys.platform.startswith("win") else "npm"
                self.frontend_proc = subprocess.Popen([npm_cmd, "run", "dev"], cwd=str(FRONTEND_DIR))

            self.status.set("Starting services...")

            def waiter():
                ok_api = self._wait_for_port(8000)
                ok_ui = self._wait_for_port(5173)
                if ok_api and ok_ui:
                    self.status.set("Running")
                else:
                    self.status.set("Partially started (check terminal logs)")

            threading.Thread(target=waiter, daemon=True).start()
        except Exception as exc:
            messagebox.showerror("Failed to start", str(exc))

    def open_ui(self):
        url = "http://127.0.0.1:5173"
        if webview:
            webview.create_window("Inspection Order Manager", url, width=1280, height=860)
            webview.start()
        else:
            import webbrowser

            webbrowser.open(url)

    def stop_all(self):
        if self.frontend_proc and self.frontend_proc.poll() is None:
            self.frontend_proc.terminate()
            self.frontend_proc = None
        if self.backend_proc and self.backend_proc.poll() is None:
            self.backend_proc.terminate()
            self.backend_proc = None
        self.status.set("Stopped")

    def on_close(self):
        self.stop_all()
        self.root.destroy()


if __name__ == "__main__":
    app_root = tk.Tk()
    app_root.geometry("760x180")
    LauncherApp(app_root)
    app_root.mainloop()
