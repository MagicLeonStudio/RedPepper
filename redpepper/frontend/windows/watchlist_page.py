"""Watchlist Page."""

import hashlib

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QDialog,
    QLineEdit, QComboBox, QFormLayout, QMessageBox, QHeaderView,
    QFileDialog, QApplication, QInputDialog, QMenu
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

STATUS_COLORS = {
    "watching": "#8B5CF6",
    "triggered": "#F05C77",
    "bought": "#8B6FD6",
    "archived": "#7A7A9E",
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


class AddWatchDialog(QDialog):
    """Dialog to add/edit a watchlist item."""

    def __init__(self, parent=None, edit_data=None):
        super().__init__(parent)
        self.edit_data = edit_data
        self.setWindowTitle(tr("watchlist.add_item") if not edit_data else tr("watchlist.edit_item"))
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
            QPushButton:hover {{ background-color: #F37A90; }}
        """)

    def _build_ui(self):
        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(tr("watchlist.name_placeholder"))
        layout.addRow(tr("common.name") + ":", self.name_input)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText(tr("watchlist.code_placeholder"))
        layout.addRow(tr("common.code") + ":", self.code_input)

        self.industry_input = QLineEdit()
        self.industry_input.setPlaceholderText(tr("watchlist.industry_placeholder"))
        layout.addRow(tr("watchlist.industry") + ":", self.industry_input)

        self.condition_input = QLineEdit()
        self.condition_input.setPlaceholderText(tr("watchlist.condition_placeholder"))
        layout.addRow(tr("watchlist.trigger_condition") + ":", self.condition_input)

        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("例如：AI主线 / 防御轮动 / 指数ETF")
        layout.addRow("分组:", self.group_input)

        self.rating_combo = QComboBox()
        self.rating_combo.addItems(["A", "B", "C", "D"])
        layout.addRow(tr("watchlist.rating") + ":", self.rating_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItem(tr("watchlist.watching"), "watching")
        self.status_combo.addItem(tr("watchlist.triggered"), "triggered")
        self.status_combo.addItem(tr("watchlist.bought"), "bought")
        self.status_combo.addItem(tr("watchlist.archived"), "archived")
        layout.addRow(tr("watchlist.status") + ":", self.status_combo)

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
            self.name_input.setText(self.edit_data.get("name", ""))
            self.code_input.setText(self.edit_data.get("code", ""))
            self.industry_input.setText(self.edit_data.get("industry", ""))
            self.condition_input.setText(self.edit_data.get("condition", ""))
            self.group_input.setText(self.edit_data.get("group", ""))
            self.rating_combo.setCurrentText(self.edit_data.get("rating", "A"))
            status_value = str(self.edit_data.get("status", "watching")).strip().lower()
            index = self.status_combo.findData(status_value)
            self.status_combo.setCurrentIndex(index if index >= 0 else 0)

    def _on_save(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, tr("common.warning"), tr("watchlist.please_enter_name"))
            return
        self.accept()

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "code": self.code_input.text().strip(),
            "industry": self.industry_input.text().strip(),
            "condition": self.condition_input.text().strip(),
            "group": self.group_input.text().strip(),
            "rating": self.rating_combo.currentText(),
            "status": self.status_combo.currentData(),
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
        title = QLabel(tr("watchlist.title"))
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Weight.Bold))
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
        self.tabs.addTab(self.stock_table, tr("watchlist.stock_watch"))

        self.fund_table = self._create_table()
        self.tabs.addTab(self.fund_table, tr("watchlist.fund_watch"))

        layout.addWidget(self.tabs)

        # Buttons
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

        self.btn_batch_delete = QPushButton("🧹 " + tr("watchlist.batch_delete"))
        self.btn_batch_delete.setStyleSheet(f"""
            QPushButton {{
                background-color: #2A2A3E;
                color: #F59E0B;
                border: 1px solid #F59E0B;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #33F59E0B; }}
        """)
        self.btn_batch_delete.clicked.connect(self._on_batch_delete)
        btn_layout.addWidget(self.btn_batch_delete)

        self.btn_import_screenshot = QPushButton("🖼 " + tr("watchlist.import_from_screenshot"))
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

        self.btn_import_csv = QPushButton("📄 " + tr("watchlist.import_from_csv"))
        self.btn_import_csv.setStyleSheet(f"""
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
        self.btn_import_csv.clicked.connect(self._on_import_csv)
        btn_layout.addWidget(self.btn_import_csv)

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

        self.empty_hint = QLabel(tr("watchlist.empty"))
        self.empty_hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.hide()
        btn_layout.addWidget(self.empty_hint)

        layout.addLayout(btn_layout)

    def _create_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            tr("watchlist.index"), tr("common.name"), tr("common.code"), "分组", tr("watchlist.industry"),
            tr("watchlist.trigger_condition"), tr("watchlist.rating"), tr("watchlist.status")
        ])
        table.setStyleSheet(TABLE_STYLE)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.setColumnWidth(0, 56)
        table.setColumnWidth(1, 140)
        table.setColumnWidth(2, 80)
        table.setColumnWidth(3, 120)
        table.setColumnWidth(4, 100)
        table.setColumnWidth(5, 160)
        table.setColumnWidth(6, 60)
        return table

    def _load_data(self):
        try:
            from frontend.services.watchlist_service import WatchlistService
            svc = WatchlistService()
            all_items = svc.get_all()
            self._stock_watches = [item for item in all_items if str(item.get("type", "")) != "Fund"]
            self._fund_watches = [item for item in all_items if str(item.get("type", "")) == "Fund"]
        except Exception:
            self._stock_watches = []
            self._fund_watches = []

        self._refresh_table(self.stock_table, self._stock_watches)
        self._refresh_table(self.fund_table, self._fund_watches)
        self._check_empty()

    def _refresh_table(self, table: QTableWidget, data: list):
        table.setRowCount(len(data))
        for row, item in enumerate(data):
            group_name = str(item.get("group", "") or "").strip() or "未分组"
            values = [
                str(row + 1),
                item.get("name", ""),
                item.get("code", ""),
                group_name,
                item.get("industry", ""),
                item.get("condition", ""),
                item.get("rating", ""),
                {
                    "watching": tr("watchlist.watching"),
                    "triggered": tr("watchlist.triggered"),
                    "bought": tr("watchlist.bought"),
                    "archived": tr("watchlist.archived"),
                    "holding": tr("watchlist.holding"),
                }.get(str(item.get("status", "watching")).strip().lower(), item.get("status", tr("watchlist.watching"))),
            ]
            for col, val in enumerate(values):
                cell = QTableWidgetItem(val)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 3:
                    cell.setForeground(QColor(self._group_color_for_name(group_name)))
                    cell.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
                if col == 7:
                    status = str(item.get("status", "watching")).strip().lower()
                    color = STATUS_COLORS.get(status, ACCENT_PURPLE)
                    cell.setForeground(QColor(color))
                    cell.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
                if col in {0, 6}:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, col, cell)

    def _group_color_for_name(self, group_name: str) -> str:
        text = str(group_name or "").strip() or "未分组"
        digest = hashlib.md5(text.encode("utf-8")).digest()
        return GROUP_TAG_COLORS[digest[0] % len(GROUP_TAG_COLORS)]

    def _selected_ids(self) -> list[int]:
        table, dataset = self._get_current()
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
        from frontend.services.watchlist_service import WatchlistService

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

        svc = WatchlistService()
        try:
            result = svc.smart_group_auto(ids=ids)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), f"智能分组失败: {e}")
            return
        self._load_data()
        self._show_group_result(result)

    def _on_smart_group_semi(self):
        from frontend.services.watchlist_service import WatchlistService

        group_text, ok = QInputDialog.getText(
            self,
            "半自动分组",
            "请输入组名（用逗号分隔），例如：AI主线,防御轮动,指数ETF",
        )
        if not ok:
            return

        group_names = [name.strip() for name in str(group_text).replace("，", ",").split(",") if name.strip()]
        if not group_names:
            QMessageBox.information(self, tr("common.info"), "至少输入一个组名")
            return

        ids = self._selected_ids()
        svc = WatchlistService()
        try:
            result = svc.smart_group_semi(group_names=group_names, ids=ids)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), f"半自动分组失败: {e}")
            return
        self._load_data()
        self._show_group_result(result)

    def _on_manual_group(self):
        from frontend.services.watchlist_service import WatchlistService

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

        svc = WatchlistService()
        try:
            svc.smart_group_manual(ids=ids, group_name=group_name)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), f"手动改组失败: {e}")
            return

        self._load_data()
        QMessageBox.information(self, tr("common.success"), f"已更新 {len(ids)} 条")

    def _get_current(self):
        if self.tabs.currentIndex() == 0:
            return self.stock_table, self._stock_watches
        return self.fund_table, self._fund_watches

    def _on_add(self):
        dialog = AddWatchDialog(self)
        if dialog.exec() == 1:
            from frontend.services.watchlist_service import WatchlistService

            data = dialog.get_data()
            data["type"] = "Stock" if self.tabs.currentIndex() == 0 else "Fund"
            svc = WatchlistService()
            try:
                svc.create(data)
            except Exception as e:
                QMessageBox.warning(self, tr("common.error"), tr("watchlist.save_failed") + f": {e}")
                return
            self._load_data()

    def _on_edit(self):
        table, dataset = self._get_current()
        row = table.currentRow()
        if row < 0 or row >= len(dataset):
            QMessageBox.information(self, tr("common.info"), tr("watchlist.select_edit"))
            return
        dialog = AddWatchDialog(self, edit_data=dataset[row])
        if dialog.exec() == 1:
            from frontend.services.watchlist_service import WatchlistService

            item_id = dataset[row].get("id")
            if item_id is None:
                QMessageBox.warning(self, tr("common.error"), tr("watchlist.missing_id"))
                return

            data = dialog.get_data()
            data["type"] = dataset[row].get("type", "Stock")

            svc = WatchlistService()
            try:
                svc.update(item_id, data)
            except Exception as e:
                QMessageBox.warning(self, tr("common.error"), tr("watchlist.update_failed") + f": {e}")
                return
            self._load_data()

    def _on_delete(self):
        table, dataset = self._get_current()
        row = table.currentRow()
        if row < 0 or row >= len(dataset):
            QMessageBox.information(self, tr("common.info"), tr("watchlist.select_delete"))
            return
        reply = QMessageBox.question(
            self, tr("common.confirm"),
            tr("watchlist.delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            from frontend.services.watchlist_service import WatchlistService

            item_id = dataset[row].get("id")
            if item_id is None:
                QMessageBox.warning(self, tr("common.error"), tr("watchlist.missing_id"))
                return

            svc = WatchlistService()
            try:
                svc.delete(item_id)
            except Exception as e:
                QMessageBox.warning(self, tr("common.error"), tr("watchlist.delete_failed") + f": {e}")
                return
            self._load_data()

    def _on_batch_delete(self):
        table, dataset = self._get_current()
        selected_rows = sorted({index.row() for index in table.selectionModel().selectedRows()}, reverse=True)
        if not selected_rows:
            QMessageBox.information(self, tr("common.info"), tr("watchlist.select_batch_delete"))
            return

        reply = QMessageBox.question(
            self,
            tr("common.confirm"),
            tr("watchlist.batch_delete_confirm", count=len(selected_rows)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from frontend.services.watchlist_service import WatchlistService

        svc = WatchlistService()
        deleted = 0
        for row in selected_rows:
            if row < 0 or row >= len(dataset):
                continue
            item_id = dataset[row].get("id")
            if item_id is None:
                continue
            try:
                svc.delete(item_id)
                deleted += 1
            except Exception:
                continue

        self._load_data()
        QMessageBox.information(self, tr("common.success"), tr("watchlist.batch_delete_success", count=deleted))

    def _check_empty(self):
        count = len(self._stock_watches) + len(self._fund_watches)
        if count == 0:
            self.empty_hint.show()
        else:
            self.empty_hint.hide()

    def _on_import_screenshot(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("watchlist.import_from_screenshot"),
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not file_path:
            return

        from frontend.services.watchlist_service import WatchlistService

        try:
            service = WatchlistService()
            csv_result = run_ocr_import(
                self,
                tr("watchlist.screenshot_to_csv"),
                service.screenshot_to_csv,
                file_path,
            )
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("watchlist.screenshot_import_failed") + f": {e}")
            return

        items = list(csv_result.get("items", []) if isinstance(csv_result, dict) else [])
        if not items:
            QMessageBox.information(self, tr("common.info"), tr("watchlist.csv_empty"))
            return

        reply = QMessageBox.question(
            self,
            tr("common.confirm"),
            tr("watchlist.csv_ready_import_confirm", count=len(items)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            created_items = service.import_from_extracted_items(items)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("watchlist.screenshot_import_failed") + f": {e}")
            return

        self._load_data()
        QMessageBox.information(
            self,
            tr("common.success"),
            tr("watchlist.screenshot_import_success", count=len(created_items)),
        )

    def _on_import_csv(self):
        from frontend.services.watchlist_service import WatchlistService

        source_dialog = QMessageBox(self)
        source_dialog.setWindowTitle(tr("watchlist.import_from_csv"))
        source_dialog.setIcon(QMessageBox.Icon.Question)
        source_dialog.setText(tr("watchlist.csv_import_source_prompt"))
        btn_file = source_dialog.addButton(tr("watchlist.csv_import_from_file"), QMessageBox.ButtonRole.ActionRole)
        btn_clipboard = source_dialog.addButton(tr("watchlist.csv_import_from_clipboard"), QMessageBox.ButtonRole.ActionRole)
        source_dialog.addButton(QMessageBox.StandardButton.Cancel)
        source_dialog.exec()

        clicked = source_dialog.clickedButton()
        service = WatchlistService()
        if clicked is btn_file:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                tr("watchlist.import_from_csv"),
                "",
                "CSV Files (*.csv)",
            )
            if not file_path:
                return
            task = service.import_from_csv_with_progress
            task_arg = file_path
        elif clicked is btn_clipboard:
            csv_text = QApplication.clipboard().text().strip()
            if not csv_text:
                QMessageBox.information(self, tr("common.info"), tr("watchlist.csv_clipboard_empty"))
                return
            task = service.import_from_csv_text_with_progress
            task_arg = csv_text
        else:
            return

        try:
            result = run_ocr_import(
                self,
                tr("watchlist.import_from_csv"),
                task,
                task_arg,
            )
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("watchlist.import_from_csv") + f": {e}")
            return

        self._load_data()
        created = int(result.get("created", 0) if isinstance(result, dict) else 0)
        errors = list(result.get("errors", []) if isinstance(result, dict) else [])
        total = int(result.get("total", 0) if isinstance(result, dict) else 0)
        parsed = int(result.get("parsed", 0) if isinstance(result, dict) else max(created, 0))
        invalid = int(result.get("invalid", 0) if isinstance(result, dict) else 0)
        duplicates = int(result.get("duplicates", 0) if isinstance(result, dict) else 0)
        existing_rows_before = int(result.get("existing_rows_before", 0) if isinstance(result, dict) else 0)
        existing_unique_before = int(result.get("existing_unique_codes_before", 0) if isinstance(result, dict) else 0)
        message = tr("watchlist.import_from_csv_summary", total=total, parsed=parsed, invalid=invalid, duplicates=duplicates, created=created)
        if existing_rows_before or existing_unique_before:
            message += "\n" + tr(
                "watchlist.import_from_csv_existing_summary",
                existing_rows=existing_rows_before,
                existing_unique=existing_unique_before,
            )
        if errors:
            message += "\n" + tr("watchlist.csv_import_with_errors", count=len(errors))
        QMessageBox.information(self, tr("common.success"), message)
