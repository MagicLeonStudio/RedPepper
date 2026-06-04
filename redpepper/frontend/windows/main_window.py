"""Main Application Window."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QStatusBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap

from frontend.app_meta import APP_VERSION, full_logo_path, logo_icon_path
from frontend.i18n.translator import tr
from frontend.widgets.language_switcher import LanguageSwitcher
from frontend.windows.dashboard_page import DashboardPage
from frontend.windows.portfolio_page import PortfolioPage
from frontend.windows.watchlist_page import WatchlistPage
from frontend.windows.trade_log_page import TradeLogPage
from frontend.windows.briefing_page import BriefingPage
from frontend.windows.diary_page import DiaryPage
from frontend.windows.knowledge_page import KnowledgePage
from frontend.windows.settings_page import SettingsPage

# Color constants
BG_DARK = "#0D0D1A"
BG_CARD = "#1A1A2E"
TEXT_PRIMARY = "#E8E8F0"
TEXT_SECONDARY = "#7A7A9E"
BRAND_RED = "#F05C77"
ACCENT_PURPLE = "#8B5CF6"
BORDER_COLOR = "#338B5CF6"


class NavButton(QPushButton):
    """Sidebar navigation button."""

    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(f"{icon}  {text}", parent)
        self.setMinimumHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self._active = False
        self._update_style()

    def set_active(self, active: bool):
        """Set button active/highlighted state."""
        self._active = active
        self._update_style()

    def _update_style(self):
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {BRAND_RED};
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 16px;
                    font-size: 13px;
                    font-weight: bold;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: #F37A90;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {TEXT_PRIMARY};
                    border: none;
                    border-radius: 8px;
                    padding: 10px 16px;
                    font-size: 13px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: #2A2A3E;
                }}
            """)


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("app_title"))
        self.resize(1200, 800)
        icon_path = logo_icon_path()
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._nav_buttons = []
        self._pages = {}

        self._build_ui()
        self._setup_status_check()
        self._select_page(0)

    def _build_ui(self):
        """Build the main window UI."""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === Left Sidebar ===
        sidebar = self._build_sidebar()
        layout.addWidget(sidebar)

        # === Content Area ===
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {BG_DARK};")
        layout.addWidget(self.stack, 1)

        # Create pages
        self._add_page("dashboard", DashboardPage(), "📊", tr("nav.dashboard"))
        self._add_page("portfolio", PortfolioPage(), "📈", tr("nav.portfolio"))
        self._add_page("watchlist", WatchlistPage(), "👁", tr("nav.watchlist"))
        self._add_page("trade_log", TradeLogPage(), "📝", tr("nav.trade_log"))
        self._add_page("briefing", BriefingPage(), "📰", tr("nav.briefing"))
        self._add_page("diary", DiaryPage(), "📔", tr("nav.diary"))
        self._add_page("knowledge", KnowledgePage(), "📚", tr("nav.knowledge"))
        self._add_page("settings", SettingsPage(), "⚙", tr("nav.settings"))

        # === Status Bar ===
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {BG_CARD};
                color: {TEXT_SECONDARY};
                border-top: 1px solid {BORDER_COLOR};
            }}
        """)
        self._status_label = QLabel(tr("status.backend_connecting"))
        self.status_bar.addWidget(self._status_label)

    def _build_sidebar(self) -> QWidget:
        """Build the left sidebar."""
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_CARD};
                border-right: 1px solid {BORDER_COLOR};
            }}
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)

        # Logo area
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = full_logo_path()
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path)).scaled(
                140,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText("RedPepper")
            logo_label.setFont(QFont("Microsoft YaHei UI", 16, QFont.Weight.Bold))
            logo_label.setStyleSheet(f"color: {BRAND_RED}; padding: 8px;")
        layout.addWidget(logo_label)

        layout.addSpacing(12)

        # Nav items
        nav_items = [
            ("📊", tr("nav.dashboard")),
            ("📈", tr("nav.portfolio")),
            ("👁", tr("nav.watchlist")),
            ("📝", tr("nav.trade_log")),
            ("📰", tr("nav.briefing")),
            ("📔", tr("nav.diary")),
            ("📚", tr("nav.knowledge")),
            ("⚙", tr("nav.settings")),
        ]

        for idx, (icon, text) in enumerate(nav_items):
            btn = NavButton(icon, text)
            btn.clicked.connect(lambda checked, i=idx: self._select_page(i))
            self._nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # Bottom: Language switcher + version
        lang_switcher = LanguageSwitcher()
        lang_switcher.locale_changed.connect(self._on_locale_changed)
        layout.addWidget(lang_switcher)

        version_label = QLabel(APP_VERSION)
        version_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        return sidebar

    def _add_page(self, key: str, page, icon: str, text: str):
        """Add a page to the stacked widget."""
        self._pages[key] = page
        self.stack.addWidget(page)

    def _select_page(self, index: int):
        """Select a page by index."""
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.set_active(i == index)

    def _on_locale_changed(self, locale: str):
        """Handle language change."""
        current_index = self.stack.currentIndex()
        replacement = MainWindow()
        replacement._select_page(current_index)
        replacement.show()

        from PyQt6.QtWidgets import QApplication

        QApplication.instance()._redpepper_main_window = replacement
        self.close()

    def _setup_status_check(self):
        """Setup periodic backend status check."""
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._check_backend_status)
        self._status_timer.start(10000)  # every 10 seconds
        QTimer.singleShot(2000, self._check_backend_status)

    def _check_backend_status(self):
        """Check if backend is running."""
        try:
            import urllib.request
            req = urllib.request.Request(
                "http://127.0.0.1:8000/api/health",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    self._status_label.setText(tr("status.backend_connected"))
                    self._status_label.setStyleSheet("color: #8B6FD6;")
                else:
                    self._status_label.setText(tr("status.backend_error"))
                    self._status_label.setStyleSheet("color: #F05C77;")
        except Exception:
            self._status_label.setText(tr("status.backend_disconnected"))
            self._status_label.setStyleSheet("color: #F05C77;")
