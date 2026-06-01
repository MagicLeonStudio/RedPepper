"""Watchlist Page."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QDialog,
    QLineEdit, QComboBox, QFormLayout, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt
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

STATUS_COLORS = {
    "watching": "#8B5CF6",
    "triggered": "#EF4444",
    "bought": "#22C55E",
    "archived": "#7A7A9E",
}


class AddWatchDialog(QDialog):
    """Dialog to add/edit a watchlist item."""

    def __init__(self, parent=None, edit_data=None):
        super().__init__(parent)
        self.edit_data = edit_data
        self.setWindowTitle(tr("Add Watch Item") if not edit_data else tr("Edit Watch Item"))
        self.setMinimumWidth(400)
        self._build_ui()
        self.setStyleSheet(f"""
            QDialog {{ background-color: {BG_DARK}; }}
            QLabel {{ color: {TEXT_PRIMARY}; }}
            QLineEdit {{
                background-color: {BG_CARD};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {ACCENT_PURPLE}; }}
            QComboBox {{
                background-color: {BG_CARD};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 8px;
            }}
            QPushButton {{
                background-color: {BRAND_RED};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{ background-color: #FF4444; }}
        """)

    def _build_ui(self):
        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(tr("e.g. Kweichow Moutai"))
        layout.addRow(tr("Name:"), self.name_input)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText(tr("e.g. 600519"))
        layout.addRow(tr("Code:"), self.code_input)

        self.industry_input = QLineEdit()
        self.industry_input.setPlaceholderText(tr("e.g. Liquor"))
        layout.addRow(tr("Industry:"), self.industry_input)

        self.condition_input = QLineEdit()
        self.condition_input.setPlaceholderText(tr("e.g. PE < 30"))
        layout.addRow(tr("Trigger Condition:"), self.condition_input)

        self.rating_combo = QComboBox()
        self.rating_combo.addItems(["A", "B", "C", "D"])
        layout.addRow(tr("Rating:"), self.rating_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItems([tr("watching"), tr("triggered"), tr("bought"), tr("archived")])
        layout.addRow(tr("Status:"), self.status_combo)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton(tr("Save"))
        btn_save.clicked.connect(self._on_save)
        btn_cancel = QPushButton(tr("Cancel"))
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: #2A2A3E;
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{ background-color: #3A3A4E; }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)

        if self.edit_data:
            self.name_input.setText(self.edit_data.get("name", ""))
            self.code_input.setText(self.edit_data.get("code", ""))
            self.industry_input.setText(self.edit_data.get("industry", ""))
            self.condition_input.setText(self.edit_data.get("condition", ""))
            self.rating_combo.setCurrentText(self.edit_data.get("rating", "A"))
            self.status_combo.setCurrentText(self.edit_data.get("status", tr("watching")))

    def _on_save(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, tr("Warning"), tr("Please enter the name"))
            return
        self.accept()

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "code": self.code_input.text().strip(),
            "industry": self.industry_input.text().strip(),
            "condition": self.condition_input.text().strip(),
            "rating": self.rating_combo.currentText(),
            "status": self.status_combo.currentText(),
        }


class WatchlistPage(QWidget):
    """Watchlist page for tracking stocks and funds of interest."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stock_watches = []
        self._fund_watches = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel(tr("Watchlist"))
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                background-color: {BG_CARD};
            }}
            QTabBar::tab {{
                background-color: #2A2A3E;
                color: {TEXT_SECONDARY};
                padding: 10px 20px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {BRAND_RED};
                color: #FFFFFF;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: #3A3A4E;
            }}
        """)

        self.stock_table = self._create_table()
        self.tabs.addTab(self.stock_table, tr("Stock Watch"))

        self.fund_table = self._create_table()
        self.tabs.addTab(self.fund_table, tr("Fund Watch"))

        layout.addWidget(self.tabs)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_add = QPushButton("➕ " + tr("Add"))
        self.btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {BRAND_RED};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #FF4444; }}
        """)
        self.btn_add.clicked.connect(self._on_add)
        btn_layout.addWidget(self.btn_add)

        self.btn_edit = QPushButton("✏️ " + tr("Edit"))
        self.btn_edit.setStyleSheet(f"""
            QPushButton {{
                background-color: #2A2A3E;
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #3A3A4E; }}
        """)
        self.btn_edit.clicked.connect(self._on_edit)
        btn_layout.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("🗑 " + tr("Delete"))
        self.btn_delete.setStyleSheet(f"""
            QPushButton {{
                background-color: #2A2A3E;
                color: #EF4444;
                border: 1px solid #EF4444;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #EF444422; }}
        """)
        self.btn_delete.clicked.connect(self._on_delete)
        btn_layout.addWidget(self.btn_delete)

        btn_layout.addStretch()

        self.empty_hint = QLabel(tr("No watch items. Click \"Add\" to create one."))
        self.empty_hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.hide()
        btn_layout.addWidget(self.empty_hint)

        layout.addLayout(btn_layout)

    def _create_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            tr("Name"), tr("Code"), tr("Industry"),
            tr("Trigger Condition"), tr("Rating"), tr("Status")
        ])
        table.setStyleSheet(TABLE_STYLE)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.setColumnWidth(0, 140)
        table.setColumnWidth(1, 80)
        table.setColumnWidth(2, 100)
        table.setColumnWidth(3, 160)
        table.setColumnWidth(4, 60)
        return table

    def _load_data(self):
        try:
            from backend.services.watchlist_service import WatchlistService
            svc = WatchlistService()
            self._stock_watches = svc.get_stock_watchlist()
            self._fund_watches = svc.get_fund_watchlist()
        except Exception:
            self._stock_watches = []
            self._fund_watches = []

        self._refresh_table(self.stock_table, self._stock_watches)
        self._refresh_table(self.fund_table, self._fund_watches)
        self._check_empty()

    def _refresh_table(self, table: QTableWidget, data: list):
        table.setRowCount(len(data))
        for row, item in enumerate(data):
            values = [
                item.get("name", ""),
                item.get("code", ""),
                item.get("industry", ""),
                item.get("condition", ""),
                item.get("rating", ""),
                item.get("status", tr("watching")),
            ]
            for col, val in enumerate(values):
                cell = QTableWidgetItem(val)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 5:
                    status = val.lower()
                    color = STATUS_COLORS.get(status, ACCENT_PURPLE)
                    cell.setForeground(QColor(color))
                    cell.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                if col == 4:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, col, cell)

    def _get_current(self):
        if self.tabs.currentIndex() == 0:
            return self.stock_table, self._stock_watches
        return self.fund_table, self._fund_watches

    def _on_add(self):
        dialog = AddWatchDialog(self)
        if dialog.exec() == 1:
            data = dialog.get_data()
            table, dataset = self._get_current()
            dataset.append(data)
            self._refresh_table(table, dataset)
            self._check_empty()

    def _on_edit(self):
        table, dataset = self._get_current()
        row = table.currentRow()
        if row < 0 or row >= len(dataset):
            QMessageBox.information(self, tr("Info"), tr("Please select a row to edit"))
            return
        dialog = AddWatchDialog(self, edit_data=dataset[row])
        if dialog.exec() == 1:
            dataset[row] = dialog.get_data()
            self._refresh_table(table, dataset)

    def _on_delete(self):
        table, dataset = self._get_current()
        row = table.currentRow()
        if row < 0 or row >= len(dataset):
            QMessageBox.information(self, tr("Info"), tr("Please select a row to delete"))
            return
        reply = QMessageBox.question(
            self, tr("Confirm"),
            tr("Delete this item?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            dataset.pop(row)
            self._refresh_table(table, dataset)
            self._check_empty()

    def _check_empty(self):
        count = len(self._stock_watches) + len(self._fund_watches)
        if count == 0:
            self.empty_hint.show()
        else:
            self.empty_hint.hide()
