"""Daily Briefing Page."""

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

        entry_box = QGroupBox(tr("briefing.manual_record"))
        entry_box.setStyleSheet(GROUPBOX_STYLE)
        entry_layout = QFormLayout(entry_box)
        entry_layout.setSpacing(8)

        self.entry_date = QDateEdit()
        self.entry_date.setCalendarPopup(True)
        self.entry_date.setDate(QDate.currentDate())
        self.entry_date.setDisplayFormat("yyyy-MM-dd")
        entry_layout.addRow(tr("briefing.date") + ":", self.entry_date)

        self.entry_title = QLineEdit()
        self.entry_title.setPlaceholderText(tr("briefing.title_placeholder"))
        entry_layout.addRow(tr("briefing.title_col") + ":", self.entry_title)

        self.entry_overseas = QTextEdit()
        self.entry_overseas.setPlaceholderText(tr("briefing.overseas_placeholder"))
        self.entry_overseas.setMaximumHeight(70)
        entry_layout.addRow(tr("briefing.overseas") + ":", self.entry_overseas)

        self.entry_domestic = QTextEdit()
        self.entry_domestic.setPlaceholderText(tr("briefing.domestic_placeholder"))
        self.entry_domestic.setMaximumHeight(70)
        entry_layout.addRow(tr("briefing.domestic") + ":", self.entry_domestic)

        self.entry_market = QTextEdit()
        self.entry_market.setPlaceholderText(tr("briefing.market_placeholder"))
        self.entry_market.setMaximumHeight(70)
        entry_layout.addRow(tr("briefing.market") + ":", self.entry_market)

        self.entry_summary = QTextEdit()
        self.entry_summary.setPlaceholderText(tr("briefing.summary_placeholder"))
        self.entry_summary.setMaximumHeight(70)
        entry_layout.addRow(tr("briefing.summary") + ":", self.entry_summary)

        btn_save = QPushButton("💾 " + tr("common.save"))
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
            QPushButton:hover {{ background-color: #F37A90; }}
        """)
        btn_save.clicked.connect(self._on_save_briefing)
        entry_layout.addRow(btn_save)

        right_layout.addWidget(entry_box)

        event_box = QGroupBox(tr("briefing.event_calendar"))
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

        event_form = QHBoxLayout()
        self.event_date = QDateEdit()
        self.event_date.setCalendarPopup(True)
        self.event_date.setDate(QDate.currentDate())
        self.event_date.setDisplayFormat("yyyy-MM-dd")
        event_form.addWidget(self.event_date)

        self.event_title = QLineEdit()
        self.event_title.setPlaceholderText(tr("briefing.event_title_placeholder"))
        event_form.addWidget(self.event_title, 1)

        btn_add_event = QPushButton("➕ " + tr("briefing.add_event"))
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
        splitter.setSizes([520, 520])

        layout.addWidget(splitter)

    def _load_data(self):
        try:
            from frontend.services.briefing_service import BriefingService

            svc = BriefingService()
            self._briefings = svc.get_briefings()
            self._events = svc.get_events()
        except Exception:
            self._briefings = []
            self._events = []

        self._event_count_by_date = {}
        for evt in self._events:
            date = str(evt.get("date", "") or "")
            if date:
                self._event_count_by_date[date] = self._event_count_by_date.get(date, 0) + 1

        self._refresh_history()
        self._refresh_events()
        self._refresh_today_card()

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

    def _refresh_events(self):
        self.event_list.clear()
        for evt in self._events:
            text = f"{evt.get('date', '')} - {evt.get('title', '')}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, evt)
            self.event_list.addItem(item)

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

    def _on_save_briefing(self):
        title = self.entry_title.text().strip()
        if not title:
            QMessageBox.warning(self, tr("common.warning"), tr("briefing.title_required"))
            return

        data = {
            "date": self.entry_date.date().toString("yyyy-MM-dd"),
            "title": title,
            "overseas": self.entry_overseas.toPlainText().strip(),
            "domestic": self.entry_domestic.toPlainText().strip(),
            "market": self.entry_market.toPlainText().strip(),
            "summary": self.entry_summary.toPlainText().strip(),
        }

        try:
            from frontend.services.briefing_service import BriefingService

            svc = BriefingService()
            svc.add_briefing(data)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("briefing.save_failed") + f": {e}")
            return

        self._load_data()
        self.entry_title.clear()
        self.entry_overseas.clear()
        self.entry_domestic.clear()
        self.entry_market.clear()
        self.entry_summary.clear()

    def _on_add_event(self):
        title = self.event_title.text().strip()
        if not title:
            QMessageBox.warning(self, tr("common.warning"), tr("briefing.event_title_required"))
            return

        data = {
            "date": self.event_date.date().toString("yyyy-MM-dd"),
            "title": title,
        }

        try:
            from frontend.services.briefing_service import BriefingService

            svc = BriefingService()
            svc.add_event(data)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("briefing.save_failed") + f": {e}")
            return

        self._load_data()
        self.event_title.clear()

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
