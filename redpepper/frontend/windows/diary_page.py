"""Investment Diary Page."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFormLayout, QGroupBox, QDateEdit,
    QScrollArea, QFrame, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from frontend.i18n.translator import tr

# Color constants
BG_DARK = "#0D0D1A"
BG_CARD = "#1A1A2E"
TEXT_PRIMARY = "#E8E8F0"
TEXT_SECONDARY = "#7A7A9E"
BRAND_RED = "#F05C77"
ACCENT_PURPLE = "#8B5CF6"
BORDER_COLOR = "#338B5CF6"

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


class DiaryEntryWidget(QFrame):
    """Collapsible diary entry widget."""

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._data = data
        self._expanded = False
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_COLOR};
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        self._build_ui()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(8)

        # Header row
        header = QHBoxLayout()

        date_str = self._data.get("date", "")
        self.date_label = QLabel(f"📅 {date_str}")
        self.date_label.setFont(QFont("Microsoft YaHei UI", 13, QFont.Weight.Bold))
        self.date_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        header.addWidget(self.date_label)

        header.addStretch()

        self.toggle_btn = QPushButton("▼" if self._expanded else "▶")
        self.toggle_btn.setFixedSize(32, 32)
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {TEXT_PRIMARY};
            }}
        """)
        self.toggle_btn.clicked.connect(self._toggle)
        header.addWidget(self.toggle_btn)

        self.layout.addLayout(header)

        # Preview: best op + worst op
        best = self._data.get("best_op", "")
        worst = self._data.get("worst_op", "")
        preview = QLabel(f"👍 {best[:30]}{'...' if len(best) > 30 else ''}  |  👎 {worst[:30]}{'...' if len(worst) > 30 else ''}")
        preview.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        self.layout.addWidget(preview)

        # Detail area (hidden by default)
        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)
        detail_layout.setContentsMargins(8, 8, 8, 8)
        detail_layout.setSpacing(8)

        fields = [
            (tr("Best Operation"), "best_op"),
            (tr("Worst Operation"), "worst_op"),
            (tr("Decision Review"), "review"),
            (tr("Next Week Focus"), "next_focus"),
        ]
        for label, key in fields:
            lbl = QLabel(f"<b>{label}:</b> {self._data.get(key, '')}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
            detail_layout.addWidget(lbl)

        self.detail_widget.hide()
        self.layout.addWidget(self.detail_widget)

    def _toggle(self):
        self._expanded = not self._expanded
        self.detail_widget.setVisible(self._expanded)
        self.toggle_btn.setText("▼" if self._expanded else "▶")


class DiaryPage(QWidget):
    """Investment diary page for weekly reflection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._diaries = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel(tr("Investment Diary"))
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        # Split layout: form top, list bottom
        # === Write diary form ===
        form_box = QGroupBox(tr("Write Diary"))
        form_box.setStyleSheet(GROUPBOX_STYLE)
        form_layout = QFormLayout(form_box)
        form_layout.setSpacing(10)

        self.diary_date = QDateEdit()
        self.diary_date.setCalendarPopup(True)
        self.diary_date.setDate(QDate.currentDate())
        self.diary_date.setDisplayFormat("yyyy-MM-dd")
        form_layout.addRow(tr("Date:"), self.diary_date)

        self.best_op = QLineEdit()
        self.best_op.setPlaceholderText(tr("What was your best operation this week?"))
        form_layout.addRow(tr("Best Operation:"), self.best_op)

        self.worst_op = QLineEdit()
        self.worst_op.setPlaceholderText(tr("What was your worst operation this week?"))
        form_layout.addRow(tr("Worst Operation:"), self.worst_op)

        self.review = QTextEdit()
        self.review.setPlaceholderText(tr("Review your key decisions and their outcomes..."))
        self.review.setMaximumHeight(80)
        form_layout.addRow(tr("Decision Review:"), self.review)

        self.next_focus = QTextEdit()
        self.next_focus.setPlaceholderText(tr("What will you focus on next week?"))
        self.next_focus.setMaximumHeight(60)
        form_layout.addRow(tr("Next Week Focus:"), self.next_focus)

        btn_save = QPushButton("📔 " + tr("Save Diary"))
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {BRAND_RED};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #F37A90; }}
        """)
        btn_save.clicked.connect(self._on_save)
        form_layout.addRow(btn_save)

        layout.addWidget(form_box)

        # === Diary list ===
        list_label = QLabel(tr("Diary History"))
        list_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Weight.Bold))
        list_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(list_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch()

        self.scroll_area.setWidget(self.list_container)
        layout.addWidget(self.scroll_area)

    def _load_data(self):
        try:
            from frontend.services.diary_service import DiaryService
            svc = DiaryService()
            self._diaries = svc.get_diaries()
        except Exception:
            self._diaries = []
        self._refresh_list()

    def _refresh_list(self):
        # Clear existing entries (keep the stretch)
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sorted_diaries = sorted(self._diaries, key=lambda d: d.get("date", ""), reverse=True)
        for diary in sorted_diaries:
            entry = DiaryEntryWidget(diary)
            self.list_layout.insertWidget(self.list_layout.count() - 1, entry)

        if not sorted_diaries:
            hint = QLabel(tr("No diary entries yet. Write your first reflection!"))
            hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(self.list_layout.count() - 1, hint)

    def _on_save(self):
        best = self.best_op.text().strip()
        if not best:
            QMessageBox.warning(self, tr("Warning"), tr("Please fill in the best operation"))
            return

        data = {
            "date": self.diary_date.date().toString("yyyy-MM-dd"),
            "best_op": best,
            "worst_op": self.worst_op.text().strip(),
            "review": self.review.toPlainText(),
            "next_focus": self.next_focus.toPlainText(),
        }

        try:
            from frontend.services.diary_service import DiaryService
            svc = DiaryService()
            svc.add_diary(data)
        except Exception as e:
            QMessageBox.warning(self, tr("Error"), tr("Failed to save diary") + f": {e}")
            return

        self._load_data()

        self.best_op.clear()
        self.worst_op.clear()
        self.review.clear()
        self.next_focus.clear()
