"""Dashboard / Overview Page."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QProgressBar, QPushButton, QGridLayout, QFrame, QSpacerItem,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from frontend.i18n.translator import tr

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


class StatCard(QGroupBox):
    """A statistics card with large number and label."""

    def __init__(self, title: str, value: str, subtitle: str = "", is_profit: bool = True, parent=None):
        super().__init__(parent)
        self.setTitle(title)
        self.setStyleSheet(f"""
            QGroupBox {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_COLOR};
                border-radius: 12px;
                padding: 16px;
                color: {TEXT_SECONDARY};
                font-size: 12px;
                font-weight: bold;
                margin-top: 18px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                top: 1px;
                left: 10px;
                padding: 2px 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Microsoft YaHei UI", 22, QFont.Weight.Bold))
        color = PROFIT_RED if is_profit else LOSS_GREEN
        self.value_label.setStyleSheet(f"color: {color};")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setMinimumHeight(36)
        layout.addWidget(self.value_label)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
            sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(sub)


class DashboardPage(QWidget):
    """Overview dashboard page with key metrics."""

    navigate_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        """Build the dashboard UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Page title
        title = QLabel(tr("dashboard.title"))
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        # === Row 1: Three stat cards ===
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        self.total_assets_card = StatCard(tr("dashboard.total_assets"), "¥0.00", "")
        row1.addWidget(self.total_assets_card, 1)

        self.total_return_card = StatCard(tr("dashboard.total_profit"), "+¥0.00", "", is_profit=True)
        row1.addWidget(self.total_return_card, 1)

        self.today_return_card = StatCard(tr("dashboard.today_profit"), "+¥0.00", "", is_profit=True)
        row1.addWidget(self.today_return_card, 1)

        layout.addLayout(row1)

        # === Row 2: Account Structure + Core Holdings ===
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        # Account structure card
        account_box = QGroupBox(tr("dashboard.account_structure"))
        account_box.setStyleSheet(f"""
            QGroupBox {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_COLOR};
                border-radius: 12px;
                padding: 16px;
                color: {TEXT_SECONDARY};
                font-size: 12px;
                font-weight: bold;
                margin-top: 18px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                top: 1px;
                left: 10px;
                padding: 2px 6px;
            }}
            QLabel {{
                color: {TEXT_PRIMARY};
            }}
        """)
        account_layout = QVBoxLayout(account_box)
        account_layout.setContentsMargins(12, 8, 12, 8)

        self.account_list = QVBoxLayout()
        self.account_list.setSpacing(8)
        account_layout.addLayout(self.account_list)
        account_layout.addStretch()
        row2.addWidget(account_box, 1)

        # Core holdings card
        holdings_box = QGroupBox(f"{tr('dashboard.core_holdings')} (TOP3)")
        holdings_box.setStyleSheet(f"""
            QGroupBox {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_COLOR};
                border-radius: 12px;
                padding: 16px;
                color: {TEXT_SECONDARY};
                font-size: 12px;
                font-weight: bold;
                margin-top: 18px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                top: 1px;
                left: 10px;
                padding: 2px 6px;
            }}
            QLabel {{
                color: {TEXT_PRIMARY};
            }}
        """)
        holdings_layout = QVBoxLayout(holdings_box)
        holdings_layout.setContentsMargins(12, 8, 12, 8)

        self.holdings_list = QVBoxLayout()
        self.holdings_list.setSpacing(8)
        holdings_layout.addLayout(self.holdings_list)
        holdings_layout.addStretch()
        row2.addWidget(holdings_box, 1)

        layout.addLayout(row2)

        # === Concentration Alert ===
        self.alert_frame = QFrame()
        self.alert_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {PROFIT_RED};
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        alert_layout = QHBoxLayout(self.alert_frame)
        alert_layout.setContentsMargins(12, 8, 12, 8)

        alert_icon = QLabel("⚠️")
        alert_icon.setFont(QFont("Microsoft YaHei UI", 20))
        alert_layout.addWidget(alert_icon)

        self.alert_text = QLabel(tr("dashboard.concentration_warning"))
        self.alert_text.setStyleSheet(f"color: {PROFIT_RED}; font-size: 13px;")
        alert_layout.addWidget(self.alert_text, 1)

        alert_close = QPushButton("✕")
        alert_close.setFixedSize(28, 28)
        alert_close.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                font-size: 14px;
            }}
            QPushButton:hover {{
                color: {TEXT_PRIMARY};
            }}
        """)
        alert_close.clicked.connect(lambda: self.alert_frame.hide())
        alert_layout.addWidget(alert_close)

        self.alert_frame.hide()
        layout.addWidget(self.alert_frame)

        # === Quick Actions ===
        actions_box = QGroupBox(tr("dashboard.quick_actions"))
        actions_box.setStyleSheet(f"""
            QGroupBox {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_COLOR};
                border-radius: 12px;
                padding: 16px;
                color: {TEXT_SECONDARY};
                font-size: 12px;
                font-weight: bold;
                margin-top: 18px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                top: 1px;
                left: 10px;
                padding: 2px 6px;
            }}
        """)
        actions_layout = QHBoxLayout(actions_box)
        actions_layout.setContentsMargins(12, 8, 12, 8)

        btn_view = QPushButton("📈 " + tr("dashboard.view_portfolio"))
        btn_view.setStyleSheet(f"""
            QPushButton {{
                background-color: {BRAND_RED};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #F37A90;
            }}
        """)
        btn_view.clicked.connect(self._on_view_portfolio)
        actions_layout.addWidget(btn_view)

        btn_check = QPushButton("🔍 " + tr("dashboard.trade_check"))
        btn_check.setStyleSheet(f"""
            QPushButton {{
                background-color: #2A2A3E;
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #3A3A4E;
            }}
        """)
        btn_check.clicked.connect(self._on_trade_check)
        actions_layout.addWidget(btn_check)

        btn_ai_chat = QPushButton("💬 " + tr("dashboard.ai_chat"))
        btn_ai_chat.setStyleSheet(f"""
            QPushButton {{
                background-color: #2A2A3E;
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #3A3A4E;
            }}
        """)
        btn_ai_chat.clicked.connect(self._on_ai_chat)
        actions_layout.addWidget(btn_ai_chat)
        actions_layout.addStretch()

        layout.addWidget(actions_box)
        layout.addStretch()

    def _on_view_portfolio(self):
        self.navigate_requested.emit("portfolio")

    def _on_trade_check(self):
        self.navigate_requested.emit("trade_log")

    def _on_ai_chat(self):
        self.navigate_requested.emit("ai_chat")

    def refresh_data(self):
        """Public refresh hook used by other pages/window after holdings change."""
        self._load_data()

    def _load_data(self):
        """Load dashboard data from services."""
        try:
            from frontend.services.portfolio_service import PortfolioService
            svc = PortfolioService()
            summary = svc.get_summary()

            total = float(summary.get("total_assets") or 0)
            ret = float(summary.get("total_return") or 0)
            today = float(summary.get("today_return") or 0)

            self.total_assets_card.value_label.setText(f"¥{total:,.2f}")

            ret_color = PROFIT_RED if ret >= 0 else LOSS_GREEN
            ret_sign = "+" if ret >= 0 else ""
            self.total_return_card.value_label.setText(f"{ret_sign}¥{ret:,.2f}")
            self.total_return_card.value_label.setStyleSheet(f"color: {ret_color};")

            today_color = PROFIT_RED if today >= 0 else LOSS_GREEN
            today_sign = "+" if today >= 0 else ""
            self.today_return_card.value_label.setText(f"{today_sign}¥{today:,.2f}")
            self.today_return_card.value_label.setStyleSheet(f"color: {today_color};")

            # Account structure
            accounts = summary.get("accounts", [])
            total_for_calc = total if total > 0 else 1
            while self.account_list.count():
                item = self.account_list.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            for acct in accounts:
                name = acct.get("name", "")
                amount = float(acct.get("amount") or 0)
                pct = (amount / total_for_calc) * 100

                row = QHBoxLayout()
                name_lbl = QLabel(name)
                name_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
                row.addWidget(name_lbl)

                bar = QProgressBar()
                bar.setMaximum(100)
                bar.setValue(int(pct))
                bar.setMaximumHeight(10)
                bar.setTextVisible(False)
                bar.setStyleSheet(f"""
                    QProgressBar {{
                        background-color: #2A2A3E;
                        border: none;
                        border-radius: 5px;
                    }}
                    QProgressBar::chunk {{
                        background-color: {ACCENT_PURPLE};
                        border-radius: 5px;
                    }}
                """)
                row.addWidget(bar, 1)

                amt_lbl = QLabel(f"¥{amount:,.0f} ({pct:.1f}%)")
                amt_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
                amt_lbl.setMinimumWidth(100)
                amt_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
                row.addWidget(amt_lbl)

                container = QWidget()
                container.setLayout(row)
                self.account_list.addWidget(container)

            # Core holdings
            holdings = summary.get("top_holdings", [])
            while self.holdings_list.count():
                item = self.holdings_list.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            for h in holdings[:3]:
                name = h.get("name", "")
                code = h.get("code", "")
                ret_pct = float(h.get("return_pct") or 0)
                color = PROFIT_RED if ret_pct >= 0 else LOSS_GREEN
                sign = "+" if ret_pct >= 0 else ""

                row = QHBoxLayout()
                info_lbl = QLabel(f"{name} ({code})")
                info_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
                row.addWidget(info_lbl)
                row.addStretch()

                pct_lbl = QLabel(f"{sign}{ret_pct:.2f}%")
                pct_lbl.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")
                row.addWidget(pct_lbl)

                container = QWidget()
                container.setLayout(row)
                self.holdings_list.addWidget(container)

            # Concentration alert
            max_pct = summary.get("max_concentration_pct", 0)
            if max_pct > 50:
                self.alert_frame.show()
                self.alert_text.setText(tr("dashboard.concentration_warning_pct", pct=f"{max_pct:.1f}"))

        except Exception:
            # Use demo data if backend unavailable
            self.total_assets_card.value_label.setText("¥128,450.00")
            self.total_return_card.value_label.setText("+¥12,340.00")
            self.total_return_card.value_label.setStyleSheet(f"color: {PROFIT_RED};")
            self.today_return_card.value_label.setText("+¥890.50")
            self.today_return_card.value_label.setStyleSheet(f"color: {PROFIT_RED};")

            demo_accounts = [
                (tr("dashboard.stock_etf"), 85400),
                (tr("dashboard.fund"), 32050),
                (tr("common.account"), 11000),
            ]
            for name, amount in demo_accounts:
                row = QHBoxLayout()
                name_lbl = QLabel(name)
                name_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
                row.addWidget(name_lbl)
                bar = QProgressBar()
                bar.setMaximum(128450)
                bar.setValue(amount)
                bar.setMaximumHeight(10)
                bar.setTextVisible(False)
                bar.setStyleSheet(f"""
                    QProgressBar {{ background-color: #2A2A3E; border: none; border-radius: 5px; }}
                    QProgressBar::chunk {{ background-color: {ACCENT_PURPLE}; border-radius: 5px; }}
                """)
                row.addWidget(bar, 1)
                amt_lbl = QLabel(f"¥{amount:,.0f}")
                amt_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
                amt_lbl.setMinimumWidth(100)
                amt_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
                row.addWidget(amt_lbl)
                container = QWidget()
                container.setLayout(row)
                self.account_list.addWidget(container)

            demo_holdings = [
                ("贵州茅台", "600519", 15.8),
                ("五粮液", "000858", 8.2),
                ("比亚迪", "002594", -3.5),
            ]
            for name, code, pct in demo_holdings:
                row = QHBoxLayout()
                info_lbl = QLabel(f"{name} ({code})")
                info_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
                row.addWidget(info_lbl)
                row.addStretch()
                color = PROFIT_RED if pct >= 0 else LOSS_GREEN
                sign = "+" if pct >= 0 else ""
                pct_lbl = QLabel(f"{sign}{pct:.2f}%")
                pct_lbl.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")
                row.addWidget(pct_lbl)
                container = QWidget()
                container.setLayout(row)
                self.holdings_list.addWidget(container)
