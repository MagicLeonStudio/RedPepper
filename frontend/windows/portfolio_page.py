"""Portfolio Management Page."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QDialog,
    QLineEdit, QComboBox, QFormLayout, QMessageBox, QHeaderView,
    QDoubleSpinBox, QSpinBox, QGroupBox
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


class AddHoldingDialog(QDialog):
    """Dialog to add/edit a holding."""

    def __init__(self, parent=None, edit_data=None):
        super().__init__(parent)
        self.edit_data = edit_data
        self.setWindowTitle(tr("Add Holding") if not edit_data else tr("Edit Holding"))
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
            QDoubleSpinBox, QSpinBox {{
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

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText(tr("e.g. 600519"))
        layout.addRow(tr("Code:"), self.code_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(tr("e.g. Kweichow Moutai"))
        layout.addRow(tr("Name:"), self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems([tr("Stock"), tr("ETF"), tr("Fund")])
        layout.addRow(tr("Type:"), self.type_combo)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setMaximum(999999999)
        self.amount_spin.setDecimals(2)
        layout.addRow(tr("Amount (CNY):"), self.amount_spin)

        self.return_spin = QDoubleSpinBox()
        self.return_spin.setMaximum(999999999)
        self.return_spin.setMinimum(-999999999)
        self.return_spin.setDecimals(2)
        layout.addRow(tr("Return (CNY):"), self.return_spin)

        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setMaximum(999999)
        self.cost_spin.setDecimals(3)
        layout.addRow(tr("Cost Price:"), self.cost_spin)

        self.shares_spin = QDoubleSpinBox()
        self.shares_spin.setMaximum(999999999)
        self.shares_spin.setDecimals(2)
        layout.addRow(tr("Shares:"), self.shares_spin)

        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText(tr("e.g. Stock Account"))
        layout.addRow(tr("Account:"), self.account_input)

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
            self.code_input.setText(self.edit_data.get("code", ""))
            self.name_input.setText(self.edit_data.get("name", ""))
            self.type_combo.setCurrentText(self.edit_data.get("type", tr("Stock")))
            self.amount_spin.setValue(self.edit_data.get("amount", 0))
            self.return_spin.setValue(self.edit_data.get("return_value", 0))
            self.cost_spin.setValue(self.edit_data.get("cost_price", 0))
            self.shares_spin.setValue(self.edit_data.get("shares", 0))
            self.account_input.setText(self.edit_data.get("account", ""))

    def _on_save(self):
        if not self.code_input.text().strip():
            QMessageBox.warning(self, tr("Warning"), tr("Please enter the code"))
            return
        if not self.name_input.text().strip():
            QMessageBox.warning(self, tr("Warning"), tr("Please enter the name"))
            return
        self.accept()

    def get_data(self):
        return {
            "code": self.code_input.text().strip(),
            "name": self.name_input.text().strip(),
            "type": self.type_combo.currentText(),
            "amount": self.amount_spin.value(),
            "return_value": self.return_spin.value(),
            "cost_price": self.cost_spin.value(),
            "shares": self.shares_spin.value(),
            "account": self.account_input.text().strip(),
        }


class PortfolioPage(QWidget):
    """Portfolio management page with holdings table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stock_data = []
        self._fund_data = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel(tr("Portfolio"))
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        # Summary bar
        self.summary_label = QLabel(tr("Total: ¥0.00 | Holdings: 0"))
        self.summary_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        layout.addWidget(self.summary_label)

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

        # Stock/ETF tab
        self.stock_table = self._create_table()
        self.tabs.addTab(self.stock_table, tr("Stock / ETF"))

        # Fund tab
        self.fund_table = self._create_table()
        self.tabs.addTab(self.fund_table, tr("Fund"))

        layout.addWidget(self.tabs)

        # Action buttons
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

        # Empty hint
        self.empty_hint = QLabel(tr("No data. Click \"Add\" to create your first holding."))
        self.empty_hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(self.empty_hint)
        self.empty_hint.hide()

        layout.addLayout(btn_layout)

    def _create_table(self) -> QTableWidget:
        """Create a styled holdings table."""
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            tr("Code"), tr("Name"), tr("Type"), tr("Amount"),
            tr("Return"), tr("Cost Price"), tr("Shares"), tr("Account")
        ])
        table.setStyleSheet(TABLE_STYLE)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.setColumnWidth(0, 80)
        table.setColumnWidth(1, 120)
        table.setColumnWidth(2, 60)
        table.setColumnWidth(3, 100)
        table.setColumnWidth(4, 100)
        table.setColumnWidth(5, 80)
        table.setColumnWidth(6, 80)
        return table

    def _load_data(self):
        """Load portfolio data."""
        try:
            from backend.services.portfolio_service import PortfolioService
            svc = PortfolioService()
            self._stock_data = svc.get_stock_holdings()
            self._fund_data = svc.get_fund_holdings()
        except Exception:
            self._stock_data = []
            self._fund_data = []

        self._refresh_table(self.stock_table, self._stock_data)
        self._refresh_table(self.fund_table, self._fund_data)

        total = sum(h.get("amount", 0) for h in self._stock_data + self._fund_data)
        count = len(self._stock_data) + len(self._fund_data)
        self.summary_label.setText(tr("Total") + f": ¥{total:,.2f} | " + tr("Holdings") + f": {count}")

        if count == 0:
            self.empty_hint.show()
        else:
            self.empty_hint.hide()

    def _refresh_table(self, table: QTableWidget, data: list):
        """Refresh table with data."""
        table.setRowCount(len(data))
        for row, item in enumerate(data):
            values = [
                item.get("code", ""),
                item.get("name", ""),
                item.get("type", ""),
                f"¥{item.get('amount', 0):,.2f}",
                f"{'+' if item.get('return_value', 0) >= 0 else ''}¥{item.get('return_value', 0):,.2f}",
                f"{item.get('cost_price', 0):.3f}",
                f"{item.get('shares', 0):,.2f}",
                item.get("account", ""),
            ]
            for col, val in enumerate(values):
                cell = QTableWidgetItem(val)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 4:
                    ret = item.get("return_value", 0)
                    color = PROFIT_RED if ret >= 0 else LOSS_GREEN
                    cell.setForeground(QColor(color))
                table.setItem(row, col, cell)

    def _get_current_table(self) -> tuple[QTableWidget, list]:
        """Get the currently active table and its data."""
        if self.tabs.currentIndex() == 0:
            return self.stock_table, self._stock_data
        return self.fund_table, self._fund_data

    def _on_add(self):
        dialog = AddHoldingDialog(self)
        if dialog.exec() == 1:
            data = dialog.get_data()
            table, dataset = self._get_current_table()
            dataset.append(data)
            self._refresh_table(table, dataset)
            self._update_summary()

    def _on_edit(self):
        table, dataset = self._get_current_table()
        row = table.currentRow()
        if row < 0 or row >= len(dataset):
            QMessageBox.information(self, tr("Info"), tr("Please select a row to edit"))
            return
        dialog = AddHoldingDialog(self, edit_data=dataset[row])
        if dialog.exec() == 1:
            dataset[row] = dialog.get_data()
            self._refresh_table(table, dataset)
            self._update_summary()

    def _on_delete(self):
        table, dataset = self._get_current_table()
        row = table.currentRow()
        if row < 0 or row >= len(dataset):
            QMessageBox.information(self, tr("Info"), tr("Please select a row to delete"))
            return
        reply = QMessageBox.question(
            self, tr("Confirm"),
            tr("Delete this holding?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            dataset.pop(row)
            self._refresh_table(table, dataset)
            self._update_summary()

    def _update_summary(self):
        total = sum(h.get("amount", 0) for h in self._stock_data + self._fund_data)
        count = len(self._stock_data) + len(self._fund_data)
        self.summary_label.setText(tr("Total") + f": ¥{total:,.2f} | " + tr("Holdings") + f": {count}")
        if count == 0:
            self.empty_hint.show()
        else:
            self.empty_hint.hide()
