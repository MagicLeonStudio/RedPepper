"""Daily Briefing Page."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QLineEdit, QTextEdit,
    QFormLayout, QGroupBox, QDateEdit, QHeaderView, QMessageBox,
    QSplitter, QComboBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from frontend.i18n.translator import tr

# Color constants
BG_DARK = "#0D0D1A"
BG_CARD = "#1A1A2E"
TEXT_PRIMARY = "#E8E8F0"
TEXT_SECONDARY = "#7A7A9E"
BRAND_RED = "#E62E2E"
ACCENT_PURPLE = "#8B5CF6"
PROFIT_RED = "#EF4444"
LOSS_GREEN = "#22C55E"
BORDER_COLOR = "#8B5CF633"

TABLE_STYLE = f"""
    QTableWidget {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_COLOR};
        border-radius: 8px;
        color: {TEXT_PRIMARY};
        gridline-color: {BORDER_COLOR};
    }}
    QTableWidget::item {{
        padding: 8px;
        border-bottom: 1px solid {BORDER_COLOR};
    }}
    QTableWidget::item:selected {{
        background-color: #E62E2E44;
    }}
    QHeaderView::section {{
        background-color: #2A2A3E;
        color: {TEXT_SECONDARY};
        padding: 8px;
        border: none;
        border-bottom: 1px solid {BORDER_COLOR};
        font-weight: bold;
    }}
    QTableCornerButton::section {{
        background-color: #2A2A3E;
        border: none;
    }}
"""

GROUPBOX_STYLE = f"""
    QGroupBox {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_COLOR};
        border-radius: 10px;
        color: {TEXT_SECONDARY};
        font-size: 12px;
        font-weight: bold;
        margin-top: 8px;
        padding: 12px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
    }}
    QLabel {{ color: {TEXT_PRIMARY}; font-size: 12px; }}
    QDateEdit {{
        background-color: {BG_DARK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        padding: 6px;
    }}
    QLineEdit {{
        background-color: {BG_DARK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        padding: 6px;
    }}
    QTextEdit {{
        background-color: {BG_DARK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        padding: 6px;
    }}
"""


class BriefingPage(QWidget):
    """Daily briefing page with market summaries and event calendar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._briefings = []
        self._events = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel(tr("Daily Briefing"))
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === Left Panel ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Task instruction card
        task_box = QGroupBox(tr("Task Guide"))
        task_box.setStyleSheet(GROUPBOX_STYLE)
        task_layout = QVBoxLayout(task_box)
        task_text = QLabel(
            tr("Every trading day at 08:30, the system automatically pushes a briefing task.\n"
               "Please review overseas markets, domestic events, and form your comprehensive judgment.")
        )
        task_text.setWordWrap(True)
        task_text.setStyleSheet(f"color: {TEXT_SECONDARY};")
        task_layout.addWidget(task_text)
        left_layout.addWidget(task_box)

        # Today's briefing card
        self.today_box = QGroupBox(tr("Today's Briefing"))
        self.today_box.setStyleSheet(GROUPBOX_STYLE)
        today_layout = QVBoxLayout(self.today_box)
        self.today_content = QLabel(tr("No briefing for today yet."))
        self.today_content.setWordWrap(True)
        self.today_content.setStyleSheet(f"color: {TEXT_SECONDARY};")
        today_layout.addWidget(self.today_content)
        left_layout.addWidget(self.today_box)

        # History table
        history_label = QLabel(tr("History"))
        history_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        history_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        left_layout.addWidget(history_label)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels([
            tr("Date"), tr("Title"), tr("Overseas"), tr("Judgment")
        ])
        self.history_table.setStyleSheet(TABLE_STYLE)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setColumnWidth(0, 90)
        self.history_table.setColumnWidth(1, 120)
        self.history_table.setColumnWidth(2, 120)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        left_layout.addWidget(self.history_table)

        splitter.addWidget(left_widget)

        # === Right Panel: Manual entry + Calendar ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Manual entry form
        entry_box = QGroupBox(tr("Manual Entry"))
        entry_box.setStyleSheet(GROUPBOX_STYLE)
        entry_layout = QFormLayout(entry_box)
        entry_layout.setSpacing(8)

        self.entry_date = QDateEdit()
        self.entry_date.setCalendarPopup(True)
        self.entry_date.setDate(QDate.currentDate())
        self.entry_date.setDisplayFormat("yyyy-MM-dd")
        entry_layout.addRow(tr("Date:"), self.entry_date)

        self.entry_title = QLineEdit()
        self.entry_title.setPlaceholderText(tr("Briefing title"))
        entry_layout.addRow(tr("Title:"), self.entry_title)

        self.entry_overseas = QTextEdit()
        self.entry_overseas.setPlaceholderText(tr("Overseas market events..."))
        self.entry_overseas.setMaximumHeight(60)
        entry_layout.addRow(tr("Overseas:"), self.entry_overseas)

        self.entry_domestic = QTextEdit()
        self.entry_domestic.setPlaceholderText(tr("Domestic market events..."))
        self.entry_domestic.setMaximumHeight(60)
        entry_layout.addRow(tr("Domestic:"), self.entry_domestic)

        self.entry_trend = QComboBox()
        self.entry_trend.addItems([tr("Bullish"), tr("Bearish"), tr("Neutral"), tr("Volatile")])
        entry_layout.addRow(tr("Market Trend:"), self.entry_trend)

        self.entry_judgment = QTextEdit()
        self.entry_judgment.setPlaceholderText(tr("Your comprehensive judgment..."))
        self.entry_judgment.setMaximumHeight(60)
        entry_layout.addRow(tr("Judgment:"), self.entry_judgment)

        btn_save = QPushButton("💾 " + tr("Save Briefing"))
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {BRAND_RED};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #FF4444; }}
        """)
        btn_save.clicked.connect(self._on_save_briefing)
        entry_layout.addRow(btn_save)

        right_layout.addWidget(entry_box)

        # Event calendar area
        event_box = QGroupBox(tr("Event Calendar"))
        event_box.setStyleSheet(GROUPBOX_STYLE)
        event_layout = QVBoxLayout(event_box)

        self.event_list = QListWidget()
        self.event_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {BG_DARK};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 6px;
                border-bottom: 1px solid {BORDER_COLOR};
            }}
        """)
        event_layout.addWidget(self.event_list)

        # Add event form
        event_form = QHBoxLayout()
        self.event_date = QDateEdit()
        self.event_date.setCalendarPopup(True)
        self.event_date.setDate(QDate.currentDate())
        self.event_date.setDisplayFormat("yyyy-MM-dd")
        event_form.addWidget(self.event_date)

        self.event_title = QLineEdit()
        self.event_title.setPlaceholderText(tr("Event title"))
        event_form.addWidget(self.event_title, 1)

        btn_add_event = QPushButton("➕ " + tr("Add"))
        btn_add_event.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_PURPLE};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background-color: #A78BFA; }}
        """)
        btn_add_event.clicked.connect(self._on_add_event)
        event_form.addWidget(btn_add_event)

        event_layout.addLayout(event_form)
        right_layout.addWidget(event_box)

        splitter.addWidget(right_widget)
        splitter.setSizes([500, 500])

        layout.addWidget(splitter)

    def _load_data(self):
        try:
            from backend.services.briefing_service import BriefingService
            svc = BriefingService()
            self._briefings = svc.get_briefings()
            self._events = svc.get_events()
        except Exception:
            self._briefings = []
            self._events = []

        self._refresh_history()
        self._refresh_events()

        # Check for today's briefing
        today_str = QDate.currentDate().toString("yyyy-MM-dd")
        for b in self._briefings:
            if b.get("date") == today_str:
                self.today_content.setText(
                    f"<b>{b.get('title', '')}</b><br>"
                    f"{tr('Overseas')}: {b.get('overseas', '')}<br>"
                    f"{tr('Domestic')}: {b.get('domestic', '')}<br>"
                    f"{tr('Trend')}: {b.get('trend', '')}<br>"
                    f"{tr('Judgment')}: {b.get('judgment', '')}"
                )
                break

    def _refresh_history(self):
        self.history_table.setRowCount(len(self._briefings))
        for row, item in enumerate(self._briefings):
            values = [
                item.get("date", ""),
                item.get("title", ""),
                item.get("overseas", "")[:30] + "..." if len(item.get("overseas", "")) > 30 else item.get("overseas", ""),
                item.get("judgment", "")[:40] + "..." if len(item.get("judgment", "")) > 40 else item.get("judgment", ""),
            ]
            for col, val in enumerate(values):
                cell = QTableWidgetItem(val)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.history_table.setItem(row, col, cell)

    def _refresh_events(self):
        self.event_list.clear()
        for evt in self._events:
            text = f"{evt.get('date', '')} - {evt.get('title', '')}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, evt)
            self.event_list.addItem(item)

    def _on_save_briefing(self):
        title = self.entry_title.text().strip()
        if not title:
            QMessageBox.warning(self, tr("Warning"), tr("Please enter a title"))
            return

        data = {
            "date": self.entry_date.date().toString("yyyy-MM-dd"),
            "title": title,
            "overseas": self.entry_overseas.toPlainText(),
            "domestic": self.entry_domestic.toPlainText(),
            "trend": self.entry_trend.currentText(),
            "judgment": self.entry_judgment.toPlainText(),
        }

        try:
            from backend.services.briefing_service import BriefingService
            svc = BriefingService()
            svc.add_briefing(data)
        except Exception:
            pass

        self._briefings.insert(0, data)
        self._refresh_history()

        self.entry_title.clear()
        self.entry_overseas.clear()
        self.entry_domestic.clear()
        self.entry_judgment.clear()

    def _on_add_event(self):
        title = self.event_title.text().strip()
        if not title:
            return

        data = {
            "date": self.event_date.date().toString("yyyy-MM-dd"),
            "title": title,
        }

        try:
            from backend.services.briefing_service import BriefingService
            svc = BriefingService()
            svc.add_event(data)
        except Exception:
            pass

        self._events.append(data)
        self._refresh_events()
        self.event_title.clear()
