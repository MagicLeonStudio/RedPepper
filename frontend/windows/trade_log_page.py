"""Trade Log Page."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QComboBox, QLineEdit,
    QFormLayout, QGroupBox, QDateEdit, QDoubleSpinBox, QTextEdit,
    QHeaderView, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor

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

ACTION_COLORS = {
    "buy": "#EF4444",
    "sell": "#22C55E",
    "plan_buy": "#8B5CF6",
    "plan_sell": "#F59E0B",
    "hold_watch": "#7A7A9E",
}


class TradeLogPage(QWidget):
    """Trade log page for recording and viewing trading activities."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._log_data = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel(tr("Trade Log"))
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        # Splitter: form top, table bottom
        splitter = QSplitter(Qt.Orientation.Vertical)

        # === Top: Add log form ===
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)

        form_box = QGroupBox(tr("Record New Trade"))
        form_box.setStyleSheet(f"""
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
            QComboBox {{
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
            QDoubleSpinBox {{
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
        """)
        form_inner = QFormLayout(form_box)
        form_inner.setSpacing(10)

        # Date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        form_inner.addRow(tr("Date:"), self.date_edit)

        # Target name
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText(tr("e.g. 600519 Kweichow Moutai"))
        form_inner.addRow(tr("Target:"), self.target_input)

        # Action type
        self.action_combo = QComboBox()
        self.action_combo.addItem(tr("Buy"), "buy")
        self.action_combo.addItem(tr("Sell"), "sell")
        self.action_combo.addItem(tr("Plan Buy"), "plan_buy")
        self.action_combo.addItem(tr("Plan Sell"), "plan_sell")
        self.action_combo.addItem(tr("Hold & Watch"), "hold_watch")
        form_inner.addRow(tr("Action Type:"), self.action_combo)

        # Amount
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setMaximum(999999999)
        self.amount_spin.setDecimals(2)
        form_inner.addRow(tr("Amount (CNY):"), self.amount_spin)

        # Reason
        self.reason_input = QTextEdit()
        self.reason_input.setPlaceholderText(tr("Enter your reasoning for this trade..."))
        self.reason_input.setMaximumHeight(80)
        form_inner.addRow(tr("Reason:"), self.reason_input)

        # Emotion
        self.emotion_combo = QComboBox()
        self.emotion_combo.addItems([tr("Calm"), tr("Greedy"), tr("Fearful"), tr("Excited"), tr("Regretful")])
        form_inner.addRow(tr("Emotion:"), self.emotion_combo)

        # Submit button
        self.btn_submit = QPushButton("📝 " + tr("Record Trade"))
        self.btn_submit.setStyleSheet(f"""
            QPushButton {{
                background-color: {BRAND_RED};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #FF4444; }}
        """)
        self.btn_submit.clicked.connect(self._on_submit)
        form_inner.addRow(self.btn_submit)

        form_layout.addWidget(form_box)
        splitter.addWidget(form_widget)

        # === Bottom: Log table ===
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)

        table_label = QLabel(tr("Trade History"))
        table_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        table_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        table_layout.addWidget(table_label)

        self.log_table = QTableWidget()
        self.log_table.setColumnCount(7)
        self.log_table.setHorizontalHeaderLabels([
            tr("Date"), tr("Target"), tr("Action"),
            tr("Amount"), tr("Reason"), tr("Emotion"), tr("ID")
        ])
        self.log_table.setStyleSheet(TABLE_STYLE)
        self.log_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.log_table.setAlternatingRowColors(True)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.horizontalHeader().setStretchLastSection(True)
        self.log_table.setColumnWidth(0, 90)
        self.log_table.setColumnWidth(1, 140)
        self.log_table.setColumnWidth(2, 90)
        self.log_table.setColumnWidth(3, 100)
        self.log_table.setColumnWidth(4, 200)
        self.log_table.setColumnWidth(5, 80)
        table_layout.addWidget(self.log_table)

        splitter.addWidget(table_widget)
        splitter.setSizes([350, 450])

        layout.addWidget(splitter)

    def _load_data(self):
        try:
            from backend.services.trade_service import TradeService
            svc = TradeService()
            self._log_data = svc.get_trade_logs()
        except Exception:
            self._log_data = []
        self._refresh_table()

    def _refresh_table(self):
        self.log_table.setRowCount(len(self._log_data))
        for row, item in enumerate(self._log_data):
            action_key = item.get("action", "")
            action_display = {
                "buy": tr("Buy"),
                "sell": tr("Sell"),
                "plan_buy": tr("Plan Buy"),
                "plan_sell": tr("Plan Sell"),
                "hold_watch": tr("Hold & Watch"),
            }.get(action_key, action_key)

            values = [
                item.get("date", ""),
                item.get("target", ""),
                action_display,
                f"¥{item.get('amount', 0):,.2f}",
                item.get("reason", "")[:50],
                item.get("emotion", ""),
                str(item.get("id", "")),
            ]
            for col, val in enumerate(values):
                cell = QTableWidgetItem(val)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 2:
                    color = ACTION_COLORS.get(action_key, TEXT_SECONDARY)
                    cell.setForeground(QColor(color))
                    cell.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                self.log_table.setItem(row, col, cell)

    def _on_submit(self):
        target = self.target_input.text().strip()
        if not target:
            QMessageBox.warning(self, tr("Warning"), tr("Please enter the target name"))
            return

        data = {
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "target": target,
            "action": self.action_combo.currentData(),
            "amount": self.amount_spin.value(),
            "reason": self.reason_input.toPlainText(),
            "emotion": self.emotion_combo.currentText(),
        }

        try:
            from backend.services.trade_service import TradeService
            svc = TradeService()
            svc.add_trade_log(data)
        except Exception:
            pass

        self._log_data.insert(0, data)
        self._refresh_table()

        # Clear form
        self.target_input.clear()
        self.amount_spin.setValue(0)
        self.reason_input.clear()
        self.action_combo.setCurrentIndex(0)
