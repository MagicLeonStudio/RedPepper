"""Portfolio Management Page."""

import hashlib

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QDialog,
    QLineEdit, QComboBox, QFormLayout, QMessageBox, QHeaderView,
    QDoubleSpinBox, QSpinBox, QGroupBox, QFileDialog, QInputDialog, QMenu, QApplication, QTextEdit
)
from PyQt6.QtCore import Qt
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

STATUS_COLORS = {
    "holding": "#8B6FD6",
    "reduced": "#F59E0B",
    "closed": "#7A7A9E",
}

GROUP_TAG_COLORS = [
    "#FFF05C77",
    "#FF8B5CF6",
    "#FF3B82F6",
    "#FF14B8A6",
    "#FFF59E0B",
    "#FFEF4444",
    "#FFEC4899",
    "#FF6366F1",
    "#FF84CC16",
    "#FF0EA5E9",
]


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


class AddHoldingDialog(QDialog):
    """Dialog to add/edit a holding."""

    def __init__(self, parent=None, edit_data=None):
        super().__init__(parent)
        self.edit_data = edit_data
        self.setWindowTitle(tr("portfolio.add_holding") if not edit_data else tr("portfolio.edit_holding"))
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
            QPushButton:hover {{ background-color: #F37A90; }}
        """)

    def _build_ui(self):
        layout = QFormLayout(self)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText(tr("portfolio.code_placeholder"))
        layout.addRow(tr("common.code") + ":", self.code_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(tr("portfolio.name_placeholder"))
        layout.addRow(tr("common.name") + ":", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItem(tr("portfolio.stock"), "Stock")
        self.type_combo.addItem(tr("portfolio.etf"), "ETF")
        self.type_combo.addItem(tr("portfolio.fund"), "Fund")
        layout.addRow(tr("common.type") + ":", self.type_combo)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setMaximum(999999999)
        self.amount_spin.setDecimals(2)
        layout.addRow(tr("trade_log.amount_cny") + ":", self.amount_spin)

        self.return_spin = QDoubleSpinBox()
        self.return_spin.setMaximum(999999999)
        self.return_spin.setMinimum(-999999999)
        self.return_spin.setDecimals(2)
        layout.addRow(tr("portfolio.return") + ":", self.return_spin)

        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setMaximum(999999)
        self.cost_spin.setDecimals(3)
        layout.addRow(tr("dashboard.cost_price") + ":", self.cost_spin)

        self.shares_spin = QDoubleSpinBox()
        self.shares_spin.setMaximum(999999999)
        self.shares_spin.setDecimals(2)
        layout.addRow(tr("dashboard.shares") + ":", self.shares_spin)

        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText(tr("portfolio.account_placeholder"))
        layout.addRow(tr("common.account") + ":", self.account_input)

        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("例如：核心持仓 / 指数ETF / 基金配置")
        layout.addRow("分组:", self.group_input)

        self.status_combo = QComboBox()
        self.status_combo.addItem("持有中", "holding")
        self.status_combo.addItem("减仓中", "reduced")
        self.status_combo.addItem("已清仓", "closed")
        layout.addRow("状态:", self.status_combo)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton(tr("common.save"))
        btn_save.clicked.connect(self._on_save)
        btn_cancel = QPushButton(tr("common.cancel"))
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
            holding_type = str(self.edit_data.get("type", "Stock")).strip().lower()
            index = self.type_combo.findData({"stock": "Stock", "etf": "ETF", "fund": "Fund"}.get(holding_type, "Stock"))
            self.type_combo.setCurrentIndex(index if index >= 0 else 0)
            self.amount_spin.setValue(self.edit_data.get("amount", 0))
            self.return_spin.setValue(self.edit_data.get("return_value", 0))
            self.cost_spin.setValue(self.edit_data.get("cost_price", 0))
            self.shares_spin.setValue(self.edit_data.get("shares", 0))
            self.account_input.setText(self.edit_data.get("account", ""))
            self.group_input.setText(self.edit_data.get("group", ""))
            status_value = str(self.edit_data.get("status", "holding")).strip().lower()
            status_index = self.status_combo.findData(status_value)
            self.status_combo.setCurrentIndex(status_index if status_index >= 0 else 0)

    def _on_save(self):
        if not self.code_input.text().strip():
            QMessageBox.warning(self, tr("common.warning"), tr("portfolio.please_enter_code"))
            return
        if not self.name_input.text().strip():
            QMessageBox.warning(self, tr("common.warning"), tr("portfolio.please_enter_name"))
            return
        self.accept()

    def get_data(self):
        return {
            "code": self.code_input.text().strip(),
            "name": self.name_input.text().strip(),
            "type": self.type_combo.currentData(),
            "amount": self.amount_spin.value(),
            "return_value": self.return_spin.value(),
            "cost_price": self.cost_spin.value(),
            "shares": self.shares_spin.value(),
            "account": self.account_input.text().strip(),
            "group": self.group_input.text().strip(),
            "status": self.status_combo.currentData(),
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
        title = QLabel(tr("portfolio.title"))
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        # Summary bar
        self.summary_label = QLabel()
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
        self.tabs.addTab(self.stock_table, tr("portfolio.stock_etf"))

        # Fund tab
        self.fund_table = self._create_table()
        self.tabs.addTab(self.fund_table, tr("portfolio.fund"))

        layout.addWidget(self.tabs)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.btn_add = QPushButton("➕ " + tr("common.add"))
        self.btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {BRAND_RED};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #F37A90; }}
        """)
        self.btn_add.clicked.connect(self._on_add)
        btn_layout.addWidget(self.btn_add)

        self.btn_edit = QPushButton("✏️ " + tr("common.edit"))
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

        self.btn_delete = QPushButton("🗑 " + tr("common.delete"))
        self.btn_delete.setStyleSheet(f"""
            QPushButton {{
                background-color: #2A2A3E;
                color: #F05C77;
                border: 1px solid #F05C77;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #44F05C77; }}
        """)
        self.btn_delete.clicked.connect(self._on_delete)
        btn_layout.addWidget(self.btn_delete)

        self.btn_import_screenshot = QPushButton("🖼 " + tr("portfolio.import_from_screenshot"))
        self.btn_import_screenshot.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_PURPLE};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #A78BFA; }}
        """)
        self.btn_import_screenshot.clicked.connect(self._on_import_screenshot)
        btn_layout.addWidget(self.btn_import_screenshot)

        self.btn_import_data = QPushButton("📄 " + tr("portfolio.import_text"))
        self.btn_import_data.setStyleSheet(f"""
            QPushButton {{
                background-color: #D4A017;
                color: #1A1A2E;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #EAB308; }}
        """)
        self.btn_import_data.clicked.connect(self._on_import_data)
        btn_layout.addWidget(self.btn_import_data)

        self.btn_smart_group = QPushButton("🧠 智能分组 ▾")
        self.btn_smart_group.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_PURPLE};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #A78BFA; }}
        """)
        self.btn_smart_group.clicked.connect(self._on_smart_group)
        btn_layout.addWidget(self.btn_smart_group)

        btn_layout.addStretch()

        # Empty hint
        self.empty_hint = QLabel(tr("portfolio.empty"))
        self.empty_hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(self.empty_hint)
        self.empty_hint.hide()

        layout.addLayout(btn_layout)

    def _create_table(self) -> QTableWidget:
        """Create a styled holdings table."""
        table = QTableWidget()
        table.setColumnCount(10)
        table.setHorizontalHeaderLabels([
            tr("common.code"), tr("common.name"), tr("common.type"), "分组", tr("common.status"),
            tr("common.amount"), tr("portfolio.return"), tr("dashboard.cost_price"), tr("dashboard.shares"), tr("common.account")
        ])
        table.setStyleSheet(TABLE_STYLE)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.setColumnWidth(0, 80)
        table.setColumnWidth(1, 120)
        table.setColumnWidth(2, 60)
        table.setColumnWidth(3, 120)
        table.setColumnWidth(4, 80)
        table.setColumnWidth(5, 100)
        table.setColumnWidth(6, 100)
        table.setColumnWidth(7, 80)
        table.setColumnWidth(8, 80)
        return table

    def _load_data(self):
        """Load portfolio data."""
        try:
            from frontend.services.portfolio_service import PortfolioService
            svc = PortfolioService()
            self._stock_data = svc.get_stock_holdings()
            self._fund_data = svc.get_fund_holdings()
        except Exception:
            self._stock_data = []
            self._fund_data = []

        self._refresh_table(self.stock_table, self._stock_data)
        self._refresh_table(self.fund_table, self._fund_data)

        total = sum(float(h.get("amount") or 0) for h in self._stock_data + self._fund_data)
        count = len(self._stock_data) + len(self._fund_data)
        self.summary_label.setText(f"{tr('portfolio.total')}: ¥{total:,.2f} | {tr('common.holdings')}: {count}")

        if count == 0:
            self.empty_hint.show()
        else:
            self.empty_hint.hide()

    def _refresh_table(self, table: QTableWidget, data: list):
        """Refresh table with data."""
        table.setRowCount(len(data))
        for row, item in enumerate(data):
            amount = float(item.get("amount") or 0)
            return_value = float(item.get("return_value") or 0)
            cost_price = float(item.get("cost_price") or 0)
            shares = float(item.get("shares") or 0)
            group_name = str(item.get("group", "") or "").strip() or "未分组"
            status_key = str(item.get("status", "holding")).strip().lower()
            values = [
                item.get("code", ""),
                item.get("name", ""),
                {
                    "stock": tr("portfolio.stock"),
                    "etf": tr("portfolio.etf"),
                    "fund": tr("portfolio.fund"),
                }.get(str(item.get("type", "")).strip().lower(), item.get("type", "")),
                group_name,
                {
                    "holding": "持有中",
                    "reduced": "减仓中",
                    "closed": "已清仓",
                }.get(status_key, status_key or "持有中"),
                f"¥{amount:,.2f}",
                f"{'+' if return_value >= 0 else ''}¥{return_value:,.2f}",
                f"{cost_price:.3f}",
                f"{shares:,.2f}",
                item.get("account", ""),
            ]
            for col, val in enumerate(values):
                cell = QTableWidgetItem(val)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 3:
                    cell.setForeground(QColor(self._group_color_for_name(group_name)))
                    cell.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
                if col == 4:
                    color = STATUS_COLORS.get(status_key, ACCENT_PURPLE)
                    cell.setForeground(QColor(color))
                    cell.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
                if col == 6:
                    ret = return_value
                    color = PROFIT_RED if ret >= 0 else LOSS_GREEN
                    cell.setForeground(QColor(color))
                if col in {2, 4, 8}:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, col, cell)

    def _group_color_for_name(self, group_name: str) -> str:
        text = str(group_name or "").strip() or "未分组"
        digest = hashlib.md5(text.encode("utf-8")).digest()
        return GROUP_TAG_COLORS[digest[0] % len(GROUP_TAG_COLORS)]

    def _selected_ids(self) -> list[int]:
        table, dataset = self._get_current_table()
        rows = sorted({index.row() for index in table.selectionModel().selectedRows()})
        ids: list[int] = []
        for row in rows:
            if row < 0 or row >= len(dataset):
                continue
            item_id = dataset[row].get("id")
            if item_id is None:
                continue
            ids.append(int(item_id))
        return ids

    def _show_group_result(self, result: dict):
        updated = int(result.get("updated", 0) if isinstance(result, dict) else 0)
        groups = list(result.get("groups", []) if isinstance(result, dict) else [])
        parts = [f"已更新 {updated} 条"]
        if groups:
            summary = []
            for group in groups:
                if not isinstance(group, dict):
                    continue
                name = str(group.get("name", "") or "")
                count = int(group.get("count", 0) or 0)
                if name:
                    summary.append(f"{name}({count})")
            if summary:
                parts.append("分组结果：" + "，".join(summary))
        QMessageBox.information(self, tr("common.success"), "\n".join(parts))

    def _on_smart_group(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {BG_CARD};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: #3A3A4E;
            }}
        """)

        action_auto = menu.addAction("🧠 全自动分组")
        action_semi = menu.addAction("🤝 半自动分组")
        action_manual = menu.addAction("🏷 手动改组")

        action_auto.triggered.connect(self._on_smart_group_auto)
        action_semi.triggered.connect(self._on_smart_group_semi)
        action_manual.triggered.connect(self._on_manual_group)

        menu.exec(self.btn_smart_group.mapToGlobal(self.btn_smart_group.rect().bottomLeft()))

    def _on_smart_group_auto(self):
        from frontend.services.portfolio_service import PortfolioService

        ids = self._selected_ids()
        scope_text = "当前选中条目" if ids else "当前页全部条目"
        reply = QMessageBox.question(
            self,
            tr("common.confirm"),
            f"将对{scope_text}执行全自动智能分组，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        svc = PortfolioService()
        try:
            result = svc.smart_group_auto(ids=ids)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), f"智能分组失败: {e}")
            return
        self._load_data()
        self._show_group_result(result)

    def _on_smart_group_semi(self):
        from frontend.services.portfolio_service import PortfolioService

        group_text, ok = QInputDialog.getText(
            self,
            "半自动分组",
            "请输入组名（用逗号分隔），例如：核心持仓,指数ETF,基金配置",
        )
        if not ok:
            return

        group_names = [name.strip() for name in str(group_text).replace("，", ",").split(",") if name.strip()]
        if not group_names:
            QMessageBox.information(self, tr("common.info"), "至少输入一个组名")
            return

        ids = self._selected_ids()
        svc = PortfolioService()
        try:
            result = svc.smart_group_semi(group_names=group_names, ids=ids)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), f"半自动分组失败: {e}")
            return
        self._load_data()
        self._show_group_result(result)

    def _on_manual_group(self):
        from frontend.services.portfolio_service import PortfolioService

        ids = self._selected_ids()
        if not ids:
            QMessageBox.information(self, tr("common.info"), "请先选择要改组的条目")
            return

        group_name, ok = QInputDialog.getText(
            self,
            "手动改组",
            "请输入新的组名（留空表示清除分组）",
        )
        if not ok:
            return

        svc = PortfolioService()
        try:
            svc.smart_group_manual(ids=ids, group_name=group_name)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), f"手动改组失败: {e}")
            return

        self._load_data()
        QMessageBox.information(self, tr("common.success"), f"已更新 {len(ids)} 条")

    def _get_current_table(self) -> tuple[QTableWidget, list]:
        """Get the currently active table and its data."""
        if self.tabs.currentIndex() == 0:
            return self.stock_table, self._stock_data
        return self.fund_table, self._fund_data

    def _on_add(self):
        dialog = AddHoldingDialog(self)
        if dialog.exec() == 1:
            from frontend.services.portfolio_service import PortfolioService

            data = dialog.get_data()
            svc = PortfolioService()
            try:
                svc.create(data)
            except Exception as e:
                QMessageBox.warning(self, tr("common.error"), tr("portfolio.save_failed") + f": {e}")
                return
            self._load_data()

    def _on_edit(self):
        table, dataset = self._get_current_table()
        row = table.currentRow()
        if row < 0 or row >= len(dataset):
            QMessageBox.information(self, tr("common.info"), tr("portfolio.select_edit"))
            return
        dialog = AddHoldingDialog(self, edit_data=dataset[row])
        if dialog.exec() == 1:
            from frontend.services.portfolio_service import PortfolioService

            item_id = dataset[row].get("id")
            if item_id is None:
                QMessageBox.warning(self, tr("common.error"), tr("portfolio.missing_id"))
                return

            svc = PortfolioService()
            try:
                svc.update(item_id, dialog.get_data())
            except Exception as e:
                QMessageBox.warning(self, tr("common.error"), tr("portfolio.update_failed") + f": {e}")
                return
            self._load_data()

    def _on_delete(self):
        table, dataset = self._get_current_table()
        row = table.currentRow()
        if row < 0 or row >= len(dataset):
            QMessageBox.information(self, tr("common.info"), tr("portfolio.select_delete"))
            return
        reply = QMessageBox.question(
            self, tr("common.confirm"),
            tr("portfolio.delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            from frontend.services.portfolio_service import PortfolioService

            item_id = dataset[row].get("id")
            if item_id is None:
                QMessageBox.warning(self, tr("common.error"), tr("portfolio.missing_id"))
                return

            svc = PortfolioService()
            try:
                svc.delete(item_id)
            except Exception as e:
                QMessageBox.warning(self, tr("common.error"), tr("portfolio.delete_failed") + f": {e}")
                return
            self._load_data()

    def _update_summary(self):
        total = sum(float(h.get("amount") or 0) for h in self._stock_data + self._fund_data)
        count = len(self._stock_data) + len(self._fund_data)
        self.summary_label.setText(f"{tr('portfolio.total')}: ¥{total:,.2f} | {tr('common.holdings')}: {count}")
        if count == 0:
            self.empty_hint.show()
        else:
            self.empty_hint.hide()

    def _on_import_screenshot(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("portfolio.import_from_screenshot"),
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not file_path:
            return

        from frontend.services.portfolio_service import PortfolioService

        svc = PortfolioService()
        try:
            extraction = run_ocr_import(
                self,
                tr("portfolio.screenshot_extract_csv_title"),
                svc.extract_csv_from_screenshot,
                file_path,
            )

            extracted_csv = str(extraction.get("csv_text", "") if isinstance(extraction, dict) else "")
            confirmed_csv = self._confirm_csv_before_import(extracted_csv)
            if confirmed_csv is None:
                return

            created_items = run_ocr_import(
                self,
                tr("portfolio.screenshot_normalize_title"),
                lambda _unused, progress_callback=None: svc.import_from_screenshot_csv_text(
                    confirmed_csv,
                    progress_callback=progress_callback,
                ),
                "csv-confirmed",
            )
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("portfolio.screenshot_import_failed") + f": {e}")
            return

        self._load_data()
        QMessageBox.information(
            self,
            tr("common.success"),
            tr("portfolio.screenshot_import_success", count=len(created_items)),
        )

    def _confirm_csv_before_import(self, csv_text: str) -> str | None:
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("portfolio.confirm_csv_title"))
        dialog.setModal(True)
        dialog.resize(760, 560)

        layout = QVBoxLayout(dialog)
        tip = QLabel(tr("portfolio.confirm_csv_tip"))
        tip.setWordWrap(True)
        layout.addWidget(tip)

        editor = QTextEdit(dialog)
        editor.setPlainText(str(csv_text or ""))
        editor.setMinimumHeight(420)
        layout.addWidget(editor)

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton(tr("common.cancel"))
        btn_ok = QPushButton(tr("portfolio.confirm_import"))
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

        btn_cancel.clicked.connect(dialog.reject)
        btn_ok.clicked.connect(dialog.accept)

        if dialog.exec() != 1:
            return None

        final_csv = editor.toPlainText().strip()
        if not final_csv:
            QMessageBox.warning(self, tr("common.warning"), tr("portfolio.csv_empty_cancelled"))
            return None
        return final_csv

    def _on_import_data(self):
        from frontend.services.portfolio_service import PortfolioService

        source_dialog = QMessageBox(self)
        source_dialog.setWindowTitle(tr("portfolio.import_text"))
        source_dialog.setIcon(QMessageBox.Icon.Question)
        source_dialog.setText(tr("portfolio.import_source_prompt"))
        btn_file = source_dialog.addButton(tr("portfolio.import_from_file"), QMessageBox.ButtonRole.ActionRole)
        btn_clipboard = source_dialog.addButton(tr("portfolio.import_from_clipboard"), QMessageBox.ButtonRole.ActionRole)
        source_dialog.addButton(QMessageBox.StandardButton.Cancel)
        source_dialog.exec()

        clicked = source_dialog.clickedButton()
        if clicked is None or clicked not in (btn_file, btn_clipboard):
            return

        service = PortfolioService()
        try:
            if clicked == btn_file:
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    tr("portfolio.import_text"),
                    "",
                    "Text/CSV Files (*.txt *.csv);;Text Files (*.txt);;CSV Files (*.csv);;All Files (*)",
                )
                if not file_path:
                    return
                if file_path.lower().endswith(".csv"):
                    result = service.import_from_csv(file_path)
                else:
                    result = service.import_from_text_file(file_path)
            else:
                text = QApplication.clipboard().text().strip()
                if not text:
                    QMessageBox.information(self, tr("common.info"), tr("portfolio.clipboard_empty"))
                    return
                try:
                    result = service.import_from_csv_text_with_progress(text)
                except Exception:
                    result = service.import_from_text(text)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("portfolio.import_failed") + f": {e}")
            return

        self._load_data()
        errors = list(result.get("errors", []) if isinstance(result, dict) else [])
        message = tr("portfolio.import_summary", total=result.get("total", 0), created=result.get("created", 0))
        if errors:
            message += "\n" + tr("portfolio.import_errors_preview", errors="；".join(str(e) for e in errors[:3]))
        QMessageBox.information(
            self,
            tr("common.success"),
            message,
        )
