"""Trade Log Page."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QComboBox, QLineEdit,
    QFormLayout, QGroupBox, QDateEdit, QDoubleSpinBox, QTextEdit,
    QHeaderView, QMessageBox, QSplitter, QFileDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor

from frontend.i18n.translator import tr
from frontend.widgets.ocr_progress import run_ocr_import

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
        background-color: #44F05C77;
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
    "buy": "#F05C77",
    "sell": "#8B6FD6",
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
        title = QLabel(tr("trade_log.title"))
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        import_bar = QHBoxLayout()
        import_bar.setSpacing(10)

        btn_import_screenshot = QPushButton("🖼 " + tr("portfolio.import_from_screenshot"))
        btn_import_screenshot.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_PURPLE};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #A78BFA; }}
        """)
        btn_import_screenshot.clicked.connect(self._on_import_screenshot)
        import_bar.addWidget(btn_import_screenshot)

        btn_import_csv = QPushButton("📄 " + tr("portfolio.import_from_csv"))
        btn_import_csv.setStyleSheet(f"""
            QPushButton {{
                background-color: #D4A017;
                color: #1A1A2E;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #EAB308; }}
        """)
        btn_import_csv.clicked.connect(self._on_import_csv)
        import_bar.addWidget(btn_import_csv)
        import_bar.addStretch()
        layout.addLayout(import_bar)

        # Splitter: form top, table bottom
        splitter = QSplitter(Qt.Orientation.Vertical)

        # === Top: Add log form ===
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)

        form_box = QGroupBox(tr("trade_log.record_new"))
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
        form_inner.addRow(tr("trade_log.date") + ":", self.date_edit)

        # Target name
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText(tr("trade_log.target_placeholder"))
        form_inner.addRow(tr("trade_log.target") + ":", self.target_input)

        # Action type
        self.action_combo = QComboBox()
        self.action_combo.addItem(tr("trade_log.buy"), "buy")
        self.action_combo.addItem(tr("trade_log.sell"), "sell")
        self.action_combo.addItem(tr("trade_log.plan_buy"), "plan_buy")
        self.action_combo.addItem(tr("trade_log.plan_sell"), "plan_sell")
        self.action_combo.addItem(tr("trade_log.hold_watch"), "hold_watch")
        form_inner.addRow(tr("trade_log.action_type") + ":", self.action_combo)

        # Amount
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setMaximum(999999999)
        self.amount_spin.setDecimals(2)
        form_inner.addRow(tr("trade_log.amount_cny") + ":", self.amount_spin)

        # Reason
        self.reason_input = QTextEdit()
        self.reason_input.setPlaceholderText(tr("trade_log.reason_placeholder"))
        self.reason_input.setMaximumHeight(80)
        form_inner.addRow(tr("common.reason") + ":", self.reason_input)

        # Emotion
        self.emotion_combo = QComboBox()
        self.emotion_combo.addItem(tr("trade_log.calm"), "calm")
        self.emotion_combo.addItem(tr("trade_log.greedy"), "greedy")
        self.emotion_combo.addItem(tr("trade_log.fearful"), "fearful")
        self.emotion_combo.addItem(tr("trade_log.excited"), "excited")
        self.emotion_combo.addItem(tr("trade_log.regretful"), "regretful")
        form_inner.addRow(tr("trade_log.emotion") + ":", self.emotion_combo)

        # Submit button
        self.btn_submit = QPushButton("📝 " + tr("trade_log.record_trade"))
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
            QPushButton:hover {{ background-color: #F37A90; }}
        """)
        self.btn_submit.clicked.connect(self._on_submit)
        form_inner.addRow(self.btn_submit)

        form_layout.addWidget(form_box)
        splitter.addWidget(form_widget)

        # === Bottom: Log table ===
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)

        table_label = QLabel(tr("trade_log.trade_history"))
        table_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Weight.Bold))
        table_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        table_layout.addWidget(table_label)

        self.log_table = QTableWidget()
        self.log_table.setColumnCount(7)
        self.log_table.setHorizontalHeaderLabels([
            tr("trade_log.date"), tr("trade_log.target"), tr("trade_log.action"),
            tr("common.amount"), tr("common.reason"), tr("trade_log.emotion"), tr("common.id")
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
            from frontend.services.trade_log_service import TradeLogService
            svc = TradeLogService()
            self._log_data = svc.get_trade_logs()
        except Exception:
            self._log_data = []
        self._refresh_table()

    def _refresh_table(self):
        self.log_table.setRowCount(len(self._log_data))
        for row, item in enumerate(self._log_data):
            action_key = item.get("action", "")
            action_display = {
                "buy": tr("trade_log.buy"),
                "sell": tr("trade_log.sell"),
                "plan_buy": tr("trade_log.plan_buy"),
                "plan_sell": tr("trade_log.plan_sell"),
                "hold_watch": tr("trade_log.hold_watch"),
            }.get(action_key, action_key)

            emotion_key = str(item.get("emotion", "")).strip().lower()
            emotion_display = {
                "calm": tr("trade_log.calm"),
                "greedy": tr("trade_log.greedy"),
                "fearful": tr("trade_log.fearful"),
                "excited": tr("trade_log.excited"),
                "regretful": tr("trade_log.regretful"),
                "confident": tr("trade_log.confident"),
            }.get(emotion_key, item.get("emotion", ""))

            values = [
                item.get("date", ""),
                item.get("target", ""),
                action_display,
                f"¥{item.get('amount', 0):,.2f}",
                item.get("reason", "")[:50],
                emotion_display,
                str(item.get("id", "")),
            ]
            for col, val in enumerate(values):
                cell = QTableWidgetItem(val)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 2:
                    color = ACTION_COLORS.get(action_key, TEXT_SECONDARY)
                    cell.setForeground(QColor(color))
                    cell.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
                self.log_table.setItem(row, col, cell)

    def _on_submit(self):
        target = self.target_input.text().strip()
        if not target:
            QMessageBox.warning(self, tr("common.warning"), tr("trade_log.please_enter_target"))
            return

        data = {
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "target": target,
            "action": self.action_combo.currentData(),
            "amount": self.amount_spin.value(),
            "reason": self.reason_input.toPlainText(),
            "emotion": self.emotion_combo.currentData(),
        }

        try:
            from frontend.services.trade_log_service import TradeLogService
            svc = TradeLogService()
            svc.add_trade_log(data)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("trade_log.save_failed") + f": {e}")
            return

        self._load_data()

        # Clear form
        self.target_input.clear()
        self.amount_spin.setValue(0)
        self.reason_input.clear()
        self.action_combo.setCurrentIndex(0)
        self.emotion_combo.setCurrentIndex(0)

    def _on_import_screenshot(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("portfolio.import_from_screenshot"),
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not file_path:
            return

        try:
            from frontend.services.trade_log_service import TradeLogService
            service = TradeLogService()
            created_items = run_ocr_import(
                self,
                tr("portfolio.import_from_screenshot"),
                service.import_from_screenshot,
                file_path,
            )
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("portfolio.screenshot_import_failed") + f": {e}")
            return

        self._load_data()
        QMessageBox.information(self, tr("common.success"), tr("portfolio.screenshot_import_success", count=len(created_items)))

    def _on_import_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("portfolio.import_from_csv"),
            "",
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        try:
            from frontend.services.trade_log_service import TradeLogService
            result = TradeLogService().import_from_csv(file_path)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("portfolio.import_from_csv") + f": {e}")
            return

        self._load_data()
        QMessageBox.information(self, tr("common.success"), tr("portfolio.import_from_csv") + f": {result.get('created', 0)}")
