"""Daily Briefing Page."""

import json

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QFormLayout,
    QGroupBox,
    QDateEdit,
    QHeaderView,
    QMessageBox,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QProgressDialog,
    QApplication,
    QDialog,
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
    """Daily briefing page with import, full-detail display, and event linkage."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._briefings = []
        self._events = []
        self._runs = []
        self._visible_runs = []
        self._event_count_by_date = {}
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel(tr("briefing.title"))
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        btn_import = QPushButton("📥 " + tr("briefing.import_from_agi2rich_html"))
        btn_import.setStyleSheet(f"""
            QPushButton {{
                background-color: #0EA5E9;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #38BDF8; }}
        """)
        btn_import.clicked.connect(self._on_import_agi2rich_html)
        top_bar.addWidget(btn_import)

        btn_refresh = QPushButton("🔄 " + tr("common.refresh"))
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_PURPLE};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #A78BFA; }}
        """)
        btn_refresh.clicked.connect(self._load_data)
        top_bar.addWidget(btn_refresh)

        btn_open = QPushButton("🌅 " + tr("briefing.generate_open"))
        btn_open.setStyleSheet(f"""
            QPushButton {{
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #3B82F6; }}
        """)
        btn_open.clicked.connect(lambda: self._generate_briefing("open"))
        top_bar.addWidget(btn_open)

        btn_midday = QPushButton("☀️ " + tr("briefing.generate_midday"))
        btn_midday.setStyleSheet(f"""
            QPushButton {{
                background-color: #D97706;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #F59E0B; }}
        """)
        btn_midday.clicked.connect(lambda: self._generate_briefing("midday"))
        top_bar.addWidget(btn_midday)

        btn_close = QPushButton("🌙 " + tr("briefing.generate_close"))
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: #7C3AED;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #8B5CF6; }}
        """)
        btn_close.clicked.connect(lambda: self._generate_briefing("close"))
        top_bar.addWidget(btn_close)

        btn_manual = QPushButton("📝 " + tr("briefing.manual_record"))
        btn_manual.setStyleSheet(f"""
            QPushButton {{
                background-color: {BRAND_RED};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #F37A90; }}
        """)
        btn_manual.clicked.connect(self._open_manual_record_dialog)
        top_bar.addWidget(btn_manual)

        btn_event = QPushButton("➕ " + tr("briefing.add_event"))
        btn_event.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_PURPLE};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #A78BFA; }}
        """)
        btn_event.clicked.connect(self._open_add_event_dialog)
        top_bar.addWidget(btn_event)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        task_box = QGroupBox(tr("briefing.task_guide"))
        task_box.setStyleSheet(GROUPBOX_STYLE)
        task_layout = QVBoxLayout(task_box)
        task_text = QLabel(tr("briefing.task_guide_desc"))
        task_text.setWordWrap(True)
        task_text.setStyleSheet(f"color: {TEXT_SECONDARY};")
        task_layout.addWidget(task_text)
        left_layout.addWidget(task_box)

        self.today_box = QGroupBox(tr("briefing.today_briefing"))
        self.today_box.setStyleSheet(GROUPBOX_STYLE)
        today_layout = QVBoxLayout(self.today_box)
        self.today_content = QLabel(tr("briefing.no_today_briefing"))
        self.today_content.setWordWrap(True)
        self.today_content.setStyleSheet(f"color: {TEXT_SECONDARY};")
        today_layout.addWidget(self.today_content)
        left_layout.addWidget(self.today_box)

        history_label = QLabel(tr("briefing.history"))
        history_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Weight.Bold))
        history_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        left_layout.addWidget(history_label)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(
            [
                tr("briefing.date"),
                tr("briefing.title_col"),
                tr("briefing.summary_col"),
                tr("briefing.related_events"),
            ]
        )
        self.history_table.setStyleSheet(TABLE_STYLE)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.itemSelectionChanged.connect(self._on_history_selection_changed)
        left_layout.addWidget(self.history_table)

        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        detail_box = QGroupBox(tr("briefing.detail_title"))
        detail_box.setStyleSheet(GROUPBOX_STYLE)
        detail_layout = QVBoxLayout(detail_box)

        self.detail_title = QLabel("-")
        self.detail_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold;")
        detail_layout.addWidget(self.detail_title)

        self.detail_body = QLabel(tr("briefing.empty"))
        self.detail_body.setWordWrap(True)
        self.detail_body.setTextFormat(Qt.TextFormat.RichText)
        self.detail_body.setStyleSheet(f"color: {TEXT_SECONDARY};")
        detail_layout.addWidget(self.detail_body)

        self.related_event_list = QListWidget()
        self.related_event_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {BG_DARK};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 4px;
                min-height: 90px;
            }}
            QListWidget::item {{
                padding: 6px;
                border-bottom: 1px solid {BORDER_COLOR};
            }}
        """)
        detail_layout.addWidget(self.related_event_list)

        right_layout.addWidget(detail_box)

        run_box = QGroupBox(tr("briefing.run_status"))
        run_box.setStyleSheet(GROUPBOX_STYLE)
        run_layout = QVBoxLayout(run_box)

        self.run_status_label = QLabel(tr("briefing.run_status_empty"))
        self.run_status_label.setWordWrap(True)
        self.run_status_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        run_layout.addWidget(self.run_status_label)

        self.run_list = QListWidget()
        self.run_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {BG_DARK};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 4px;
                min-height: 120px;
            }}
            QListWidget::item {{
                padding: 6px;
                border-bottom: 1px solid {BORDER_COLOR};
            }}
        """)
        self.run_list.itemSelectionChanged.connect(self._update_run_action_buttons)
        run_layout.addWidget(self.run_list)

        run_action_row = QHBoxLayout()
        run_action_row.setSpacing(8)

        self.btn_view_run_context = QPushButton(tr("briefing.view_run_context"))
        self.btn_view_run_context.setStyleSheet(f"""
            QPushButton {{
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #3B82F6; }}
            QPushButton:disabled {{ background-color: #334155; color: #94A3B8; }}
        """)
        self.btn_view_run_context.clicked.connect(self._show_selected_run_context)
        run_action_row.addWidget(self.btn_view_run_context)

        self.btn_view_run_detail = QPushButton(tr("briefing.view_run_detail"))
        self.btn_view_run_detail.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_PURPLE};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #A78BFA; }}
            QPushButton:disabled {{ background-color: #334155; color: #94A3B8; }}
        """)
        self.btn_view_run_detail.clicked.connect(self._show_selected_run_detail)
        run_action_row.addWidget(self.btn_view_run_detail)

        run_layout.addLayout(run_action_row)

        right_layout.addWidget(run_box)

        right_layout.addStretch(1)

        splitter.addWidget(right_widget)
        splitter.setSizes([520, 520])

        layout.addWidget(splitter)

    def _load_data(self):
        try:
            from frontend.services.briefing_service import BriefingService

            svc = BriefingService()
            self._briefings = svc.get_briefings()
            self._events = svc.get_events()
            self._runs = svc.get_runs()
        except Exception:
            self._briefings = []
            self._events = []
            self._runs = []

        self._event_count_by_date = {}
        for evt in self._events:
            date = str(evt.get("date", "") or "")
            if date:
                self._event_count_by_date[date] = self._event_count_by_date.get(date, 0) + 1

        self._refresh_history()
        self._refresh_today_card()
        self._refresh_runs()

        if self._briefings:
            self.history_table.selectRow(0)
            self._show_briefing_detail(self._briefings[0])
        else:
            self._show_empty_detail()

    def _refresh_today_card(self):
        today_str = QDate.currentDate().toString("yyyy-MM-dd")
        matched = None
        for b in self._briefings:
            if b.get("date") == today_str:
                matched = b
                break
        if not matched:
            self.today_content.setText(tr("briefing.no_today_briefing"))
            return

        self.today_content.setText(
            f"<b>{matched.get('title', '')}</b><br>"
            f"{tr('briefing.overseas')}: {matched.get('overseas', '') or '-'}<br>"
            f"{tr('briefing.domestic')}: {matched.get('domestic', '') or '-'}<br>"
            f"{tr('briefing.market')}: {matched.get('market', '') or '-'}<br>"
            f"{tr('briefing.summary')}: {matched.get('summary', '') or '-'}"
        )

    def _refresh_history(self):
        self.history_table.setRowCount(len(self._briefings))
        for row, item in enumerate(self._briefings):
            date = str(item.get("date", "") or "")
            summary = str(item.get("judgment", "") or "")
            summary_short = summary[:70] + "..." if len(summary) > 70 else summary
            values = [
                date,
                str(item.get("title", "") or ""),
                summary_short,
                str(self._event_count_by_date.get(date, 0)),
            ]
            for col, val in enumerate(values):
                cell = QTableWidgetItem(val)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.history_table.setItem(row, col, cell)

    def _refresh_runs(self):
        self.run_list.clear()
        self._visible_runs = []
        if not self._runs:
            self.run_status_label.setText(tr("briefing.run_status_empty"))
            self.run_list.addItem(QListWidgetItem(tr("briefing.run_list_empty")))
            self._update_run_action_buttons()
            return

        latest = self._runs[0]
        latest_text = tr(
            "briefing.run_status_latest",
            latest.get("session_label", "-"),
            latest.get("status", "-"),
            latest.get("created_at", "-") or "-",
        )
        if latest.get("error_message"):
            latest_text += "\n" + tr("briefing.run_status_error", latest.get("error_message", ""))
        self.run_status_label.setText(latest_text)

        self._visible_runs = list(self._runs[:8])
        for item in self._visible_runs:
            text = tr(
                "briefing.run_list_item",
                item.get("date", "-"),
                item.get("session_label", "-"),
                item.get("status", "-"),
            )
            if item.get("error_message"):
                text += " | " + str(item.get("error_message", ""))
            self.run_list.addItem(QListWidgetItem(text))
        if self._visible_runs:
            self.run_list.setCurrentRow(0)
        self._update_run_action_buttons()

    def _show_empty_detail(self):
        self.detail_title.setText("-")
        self.detail_body.setText(tr("briefing.empty"))
        self.related_event_list.clear()
        self.related_event_list.addItem(QListWidgetItem(tr("briefing.event_none")))

    def _show_briefing_detail(self, briefing: dict):
        date = str(briefing.get("date", "") or "")
        holdings_text = str(briefing.get("holdings", "") or "").strip()
        holdings_block = ""
        if holdings_text:
            holdings_block = f"<br><br><b>{tr('briefing.holdings')}</b><br>{holdings_text}"
        self.detail_title.setText(f"{date} | {briefing.get('title', '')}")
        self.detail_body.setText(
            f"<b>{tr('briefing.overseas')}</b><br>{briefing.get('overseas', '') or '-'}<br><br>"
            f"<b>{tr('briefing.domestic')}</b><br>{briefing.get('domestic', '') or '-'}<br><br>"
            f"<b>{tr('briefing.market')}</b><br>{briefing.get('trend', '') or '-'}<br><br>"
            f"<b>{tr('briefing.summary')}</b><br>{briefing.get('judgment', '') or '-'}"
            f"{holdings_block}"
        )

        self.related_event_list.clear()
        related = [e for e in self._events if str(e.get("date", "") or "") == date]
        if not related:
            self.related_event_list.addItem(QListWidgetItem(tr("briefing.event_none")))
            return
        for evt in related:
            text = f"[{evt.get('date', '')}] {evt.get('title', '')}"
            if evt.get("impact"):
                text += f" | {tr('briefing.impact')}: {evt.get('impact')}"
            self.related_event_list.addItem(QListWidgetItem(text))

    def _on_history_selection_changed(self):
        rows = self.history_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if row < 0 or row >= len(self._briefings):
            return
        self._show_briefing_detail(self._briefings[row])

    def _update_run_action_buttons(self):
        run = self._selected_run()
        enabled = run is not None
        self.btn_view_run_context.setEnabled(enabled)
        self.btn_view_run_detail.setEnabled(enabled)

    def _selected_run(self) -> dict | None:
        row = self.run_list.currentRow()
        if row < 0 or row >= len(self._visible_runs):
            return None
        return self._visible_runs[row]

    def _prettify_payload(self, raw_value) -> str:
        text = str(raw_value or "").strip()
        if not text:
            return tr("briefing.run_payload_empty")
        try:
            return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
        except Exception:
            return text

    def _show_payload_dialog(self, title: str, content: str):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.resize(860, 620)

        layout = QVBoxLayout(dialog)
        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setPlainText(content)
        viewer.setStyleSheet(f"""
            QTextEdit {{
                background-color: {BG_DARK};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 8px;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
            }}
        """)
        layout.addWidget(viewer)

        btn_close = QPushButton(tr("common.close"))
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_PURPLE};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #A78BFA; }}
        """)
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        dialog.exec()

    def _show_selected_run_context(self):
        run = self._selected_run()
        if run is None:
            QMessageBox.information(self, tr("common.warning"), tr("briefing.run_select_required"))
            return
        title = tr("briefing.run_context_title", run.get("date", "-"), run.get("session_label", "-"))
        self._show_payload_dialog(title, self._prettify_payload(run.get("context_payload")))

    def _show_selected_run_detail(self):
        run = self._selected_run()
        if run is None:
            QMessageBox.information(self, tr("common.warning"), tr("briefing.run_select_required"))
            return

        sections = [
            tr("briefing.run_meta_title"),
            f"date: {run.get('date', '-')}",
            f"session_type: {run.get('session_type', '-')}",
            f"trigger_type: {run.get('trigger_type', '-')}",
            f"status: {run.get('status', '-')}",
            f"provider: {run.get('provider', '-')}",
            f"model: {run.get('model', '-')}",
            f"created_at: {run.get('created_at', '-')}",
            f"started_at: {run.get('started_at', '-')}",
            f"finished_at: {run.get('finished_at', '-')}",
            f"retry_count: {run.get('retry_count', 0)}",
            "",
            tr("briefing.run_error_title"),
            str(run.get("error_message", "") or tr("briefing.run_error_empty")),
            "",
            tr("briefing.run_result_title"),
            self._prettify_payload(run.get("result_payload")),
        ]
        title = tr("briefing.run_detail_title", run.get("date", "-"), run.get("session_label", "-"))
        self._show_payload_dialog(title, "\n".join(sections))

    def _generate_briefing(self, session_type: str):
        progress = QProgressDialog(
            tr("briefing.generate_progress_message"),
            "",
            0,
            0,
            self,
        )
        progress.setWindowTitle(tr("briefing.generate_progress_title"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()

        try:
            from frontend.services.briefing_service import BriefingService

            svc = BriefingService()
            result = svc.generate(session_type=session_type, date=QDate.currentDate().toString("yyyy-MM-dd"))
            briefing = result.get("briefing", {}) if isinstance(result, dict) else {}
            run = result.get("run", {}) if isinstance(result, dict) else {}
            self._load_data()
            QMessageBox.information(
                self,
                tr("common.success"),
                tr(
                    "briefing.generate_success",
                    briefing.get("title", "-"),
                    briefing.get("status", "success"),
                    run.get("provider", "-"),
                ),
            )
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("briefing.generate_failed") + f": {e}")
        finally:
            progress.close()

    def _open_manual_record_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("briefing.manual_record"))
        dialog.setModal(True)
        dialog.resize(760, 620)

        layout = QFormLayout(dialog)
        layout.setSpacing(10)

        entry_date = QDateEdit()
        entry_date.setCalendarPopup(True)
        entry_date.setDate(QDate.currentDate())
        entry_date.setDisplayFormat("yyyy-MM-dd")
        layout.addRow(tr("briefing.date") + ":", entry_date)

        entry_title = QLineEdit()
        entry_title.setPlaceholderText(tr("briefing.title_placeholder"))
        layout.addRow(tr("briefing.title_col") + ":", entry_title)

        entry_overseas = QTextEdit()
        entry_overseas.setPlaceholderText(tr("briefing.overseas_placeholder"))
        entry_overseas.setMinimumHeight(90)
        layout.addRow(tr("briefing.overseas") + ":", entry_overseas)

        entry_domestic = QTextEdit()
        entry_domestic.setPlaceholderText(tr("briefing.domestic_placeholder"))
        entry_domestic.setMinimumHeight(90)
        layout.addRow(tr("briefing.domestic") + ":", entry_domestic)

        entry_market = QTextEdit()
        entry_market.setPlaceholderText(tr("briefing.market_placeholder"))
        entry_market.setMinimumHeight(90)
        layout.addRow(tr("briefing.market") + ":", entry_market)

        entry_summary = QTextEdit()
        entry_summary.setPlaceholderText(tr("briefing.summary_placeholder"))
        entry_summary.setMinimumHeight(90)
        layout.addRow(tr("briefing.summary") + ":", entry_summary)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(tr("common.cancel"))
        btn_save = QPushButton("💾 " + tr("common.save"))
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {BRAND_RED};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #F37A90; }}
        """)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addRow(btn_row)

        btn_cancel.clicked.connect(dialog.reject)

        def _save_and_close():
            data = {
                "date": entry_date.date().toString("yyyy-MM-dd"),
                "title": entry_title.text().strip(),
                "overseas": entry_overseas.toPlainText().strip(),
                "domestic": entry_domestic.toPlainText().strip(),
                "market": entry_market.toPlainText().strip(),
                "summary": entry_summary.toPlainText().strip(),
            }
            if self._on_save_briefing(data):
                dialog.accept()

        btn_save.clicked.connect(_save_and_close)
        dialog.exec()

    def _on_save_briefing(self, data: dict) -> bool:
        title = str(data.get("title", "") or "").strip()
        if not title:
            QMessageBox.warning(self, tr("common.warning"), tr("briefing.title_required"))
            return False

        try:
            from frontend.services.briefing_service import BriefingService

            svc = BriefingService()
            svc.add_briefing(data)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("briefing.save_failed") + f": {e}")
            return False

        self._load_data()
        return True

    def _open_add_event_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("briefing.add_event"))
        dialog.setModal(True)
        dialog.resize(540, 220)

        layout = QFormLayout(dialog)
        layout.setSpacing(10)

        event_date = QDateEdit()
        event_date.setCalendarPopup(True)
        event_date.setDate(QDate.currentDate())
        event_date.setDisplayFormat("yyyy-MM-dd")
        layout.addRow(tr("briefing.date") + ":", event_date)

        event_title = QLineEdit()
        event_title.setPlaceholderText(tr("briefing.event_title_placeholder"))
        layout.addRow(tr("briefing.event_desc") + ":", event_title)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(tr("common.cancel"))
        btn_save = QPushButton("➕ " + tr("briefing.add_event"))
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_PURPLE};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #A78BFA; }}
        """)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addRow(btn_row)

        btn_cancel.clicked.connect(dialog.reject)

        def _save_and_close():
            data = {
                "date": event_date.date().toString("yyyy-MM-dd"),
                "title": event_title.text().strip(),
            }
            if self._on_add_event(data):
                dialog.accept()

        btn_save.clicked.connect(_save_and_close)
        dialog.exec()

    def _on_add_event(self, data: dict) -> bool:
        title = str(data.get("title", "") or "").strip()
        if not title:
            QMessageBox.warning(self, tr("common.warning"), tr("briefing.event_title_required"))
            return False

        try:
            from frontend.services.briefing_service import BriefingService

            svc = BriefingService()
            svc.add_event(data)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("briefing.save_failed") + f": {e}")
            return False

        self._load_data()
        return True

    def _on_import_agi2rich_html(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("briefing.import_from_agi2rich_html"),
            "",
            "HTML Files (*.html *.htm)",
        )
        if not file_path:
            return

        progress = QProgressDialog(
            tr("briefing.import_progress_message"),
            "",
            0,
            0,
            self,
        )
        progress.setWindowTitle(tr("briefing.import_progress_title"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()

        try:
            from frontend.services.briefing_service import BriefingService

            svc = BriefingService()
            result = svc.import_from_agi2rich_html(file_path)
            self._load_data()
            QMessageBox.information(
                self,
                tr("common.success"),
                tr(
                    "briefing.import_summary",
                    result.get("briefings_total", 0),
                    result.get("briefings_created", 0),
                    result.get("briefings_duplicates", 0),
                    result.get("events_total", 0),
                    result.get("events_created", 0),
                    result.get("events_duplicates", 0),
                ),
            )
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("briefing.import_failed") + f": {e}")
        finally:
            progress.close()
