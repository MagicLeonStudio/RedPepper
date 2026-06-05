"""RedPepper GUI entry point."""

import atexit
import os
import signal
import sys
import subprocess
import time
from pathlib import Path
import urllib.error
import urllib.request


def _bootstrap_qt_plugin_paths() -> None:
    """Best-effort Qt plugin path bootstrap for Windows environments.

    Some conda/pip mixed setups may leave Qt looking at a non-existing plugin
    path (e.g. site-packages/PyQt6/Qt6/plugins). This guard points Qt to a
    valid plugins directory before QApplication is created.
    """
    if os.name != "nt":
        return

    plugin_roots = [
        Path(sys.prefix) / "Library" / "lib" / "qt6" / "plugins",
        Path(sys.prefix) / "Library" / "plugins",
        Path(sys.prefix) / "Lib" / "site-packages" / "PyQt6" / "Qt6" / "plugins",
    ]
    plugin_root = next((p for p in plugin_roots if (p / "platforms").exists()), None)
    if plugin_root is None:
        return

    qpa_dir = plugin_root / "platforms"

    curr_qpa = os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH", "")
    if not curr_qpa or not Path(curr_qpa).exists():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(qpa_dir)

    curr_plugin = os.environ.get("QT_PLUGIN_PATH", "")
    if not curr_plugin or not Path(curr_plugin).exists():
        os.environ["QT_PLUGIN_PATH"] = str(plugin_root)

    bin_candidates = [
        Path(sys.prefix) / "Library" / "bin",
        Path(sys.prefix) / "Lib" / "site-packages" / "PyQt6" / "Qt6" / "bin",
    ]
    for bin_dir in bin_candidates:
        if not bin_dir.exists():
            continue
        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        try:
            os.add_dll_directory(str(bin_dir))
        except Exception:
            pass
        break


_bootstrap_qt_plugin_paths()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon

from frontend.app_meta import logo_icon_path, stylesheet_path
from frontend.windows.login_window import LoginWindow
from frontend.windows.main_window import MainWindow
from frontend.i18n.translator import set_locale, tr

# Color constants
BG_DARK = "#0D0D1A"
BG_CARD = "#1A1A2E"
TEXT_PRIMARY = "#E8E8F0"
TEXT_SECONDARY = "#7A7A9E"
BRAND_RED = "#F05C77"
ACCENT_PURPLE = "#8B5CF6"
PROFIT_RED = "#F05C77"
LOSS_GREEN = "#8B6FD6"
BORDER_COLOR = "#338B5CF6"

_backend_process: subprocess.Popen | None = None


def _is_backend_running(host: str = "127.0.0.1", port: int = 8000) -> bool:
    try:
        req = urllib.request.Request(f"http://{host}:{port}/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def stop_backend() -> None:
    """Stop the backend server only if this frontend instance started it."""
    global _backend_process
    if _backend_process is None:
        return

    process = _backend_process
    _backend_process = None

    if process.poll() is not None:
        return

    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
            process.wait(timeout=5)
        except Exception:
            pass


def start_backend():
    """Start the backend uvicorn server."""
    global _backend_process

    if _is_backend_running():
        _backend_process = None
        return None

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        _backend_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.app.main:app",
             "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"],
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        for _ in range(12):
            if _is_backend_running():
                break
            time.sleep(0.5)
        return _backend_process
    except Exception as e:
        _backend_process = None
        print(f"Backend start warning: {e}")
        return None


def setup_dark_palette(app):
    """Configure dark palette for the application."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG_DARK))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(BG_CARD))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2A2A3E"))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor("#2A2A3E"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(BRAND_RED))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)


def apply_global_style(app: QApplication) -> None:
    style_path = stylesheet_path()
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))


def apply_app_icon(app: QApplication) -> None:
    icon_path = logo_icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    atexit.register(stop_backend)
    app.aboutToQuit.connect(stop_backend)
    app.setStyle("Fusion")
    setup_dark_palette(app)
    apply_global_style(app)
    apply_app_icon(app)

    font = QFont("Microsoft YaHei UI", 10)
    if not QFont(font).exactMatch():
        font = QFont("Segoe UI", 10)
    app.setFont(font)

    start_backend()

    login = LoginWindow()
    if login.exec() == 1:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
