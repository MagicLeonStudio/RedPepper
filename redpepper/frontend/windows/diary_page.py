"""Investment Diary Page."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QFormLayout,
    QGroupBox,
    QDateEdit,
    QScrollArea,
    QFrame,
    QMessageBox,
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
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_COLOR};
                border-radius: 10px;
                padding: 12px;
            }}
            """
        )
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        date_str = self._data.get("date", "")
        date_label = QLabel(f"📅 {date_str}")
        date_label.setFont(QFont("Microsoft YaHei UI", 13, QFont.Weight.Bold))
        date_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        header.addWidget(date_label)

        header.addStretch()

        self.toggle_btn = QPushButton("▼" if self._expanded else "▶")
        self.toggle_btn.setFixedSize(32, 32)
        self.toggle_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                font-size: 12px;
            }}
            QPushButton:hover {{ color: {TEXT_PRIMARY}; }}
            """
        )
        self.toggle_btn.clicked.connect(self._toggle)
        header.addWidget(self.toggle_btn)

        layout.addLayout(header)

        best = str(self._data.get("best_op", "") or "")
        worst = str(self._data.get("worst_op", "") or "")
        preview = QLabel(
            f"👍 {best[:24]}{'...' if len(best) > 24 else ''}  |  "
            f"👎 {worst[:24]}{'...' if len(worst) > 24 else ''}"
        )
        preview.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(preview)

        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)
        detail_layout.setContentsMargins(8, 8, 8, 8)
        detail_layout.setSpacing(8)

        fields = [
            (tr("diary.best_op"), "best_op"),
            (tr("diary.worst_op"), "worst_op"),
            (tr("diary.reflection"), "review"),
            (tr("diary.focus"), "next_focus"),
        ]
        for label, key in fields:
            val = str(self._data.get(key, "") or "")
            lbl = QLabel(f"<b>{label}:</b> {val if val else '-'}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
            detail_layout.addWidget(lbl)

        self.detail_widget.hide()
        layout.addWidget(self.detail_widget)

    def _toggle(self):
        self._expanded = not self._expanded
        self.detail_widget.setVisible(self._expanded)
        self.toggle_btn.setText("▼" if self._expanded else "▶")


class DiaryPage(QWidget):
    """Investment diary page with AGI2Rich import support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._diaries = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel(tr("diary.title"))
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.btn_import_agi2rich = QPushButton("📥 " + tr("diary.import_from_agi2rich_html"))
        self.btn_import_agi2rich.setStyleSheet(
            f"""
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
            """
        )
        self.btn_import_agi2rich.clicked.connect(self._on_import_agi2rich_html)
        top_bar.addWidget(self.btn_import_agi2rich)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        form_box = QGroupBox(tr("diary.write_diary"))
        form_box.setStyleSheet(GROUPBOX_STYLE)
        form_layout = QFormLayout(form_box)
        form_layout.setSpacing(10)

        self.diary_date = QDateEdit()
        self.diary_date.setCalendarPopup(True)
        self.diary_date.setDate(QDate.currentDate())
        self.diary_date.setDisplayFormat("yyyy-MM-dd")
        form_layout.addRow(tr("diary.date") + ":", self.diary_date)

        self.best_op = QLineEdit()
        self.best_op.setPlaceholderText(tr("diary.best_placeholder"))
        form_layout.addRow(tr("diary.best_op") + ":", self.best_op)

        self.worst_op = QLineEdit()
        self.worst_op.setPlaceholderText(tr("diary.worst_placeholder"))
        form_layout.addRow(tr("diary.worst_op") + ":", self.worst_op)

        self.review = QTextEdit()
        self.review.setPlaceholderText(tr("diary.review_placeholder"))
        self.review.setMaximumHeight(80)
        form_layout.addRow(tr("diary.reflection") + ":", self.review)

        self.next_focus = QTextEdit()
        self.next_focus.setPlaceholderText(tr("diary.focus_placeholder"))
        self.next_focus.setMaximumHeight(60)
        form_layout.addRow(tr("diary.focus") + ":", self.next_focus)

        btn_save = QPushButton("📔 " + tr("diary.write_diary"))
        btn_save.setStyleSheet(
            f"""
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
            """
        )
        btn_save.clicked.connect(self._on_save)
        form_layout.addRow(btn_save)

        layout.addWidget(form_box)

        list_label = QLabel(tr("diary.history"))
        list_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Weight.Bold))
        list_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(list_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            """
        )

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
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sorted_diaries = sorted(self._diaries, key=lambda d: d.get("date", ""), reverse=True)
        for diary in sorted_diaries:
            entry = DiaryEntryWidget(diary)
            self.list_layout.insertWidget(self.list_layout.count() - 1, entry)

        if not sorted_diaries:
            hint = QLabel(tr("diary.empty"))
            hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(self.list_layout.count() - 1, hint)

    def _on_save(self):
        best = self.best_op.text().strip()
        if not best:
            QMessageBox.warning(self, tr("common.warning"), tr("diary.best_required"))
            return

        data = {
            "date": self.diary_date.date().toString("yyyy-MM-dd"),
            "best_op": best,
            "worst_op": self.worst_op.text().strip(),
            "review": self.review.toPlainText().strip(),
            "next_focus": self.next_focus.toPlainText().strip(),
        }

        try:
            from frontend.services.diary_service import DiaryService

            svc = DiaryService()
            svc.add_diary(data)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("diary.save_failed") + f": {e}")
            return

        self._load_data()
        self.best_op.clear()
        self.worst_op.clear()
        self.review.clear()
        self.next_focus.clear()

    def _on_import_agi2rich_html(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("diary.import_from_agi2rich_html"),
            "",
            "HTML Files (*.html *.htm)",
        )
        if not file_path:
            return

        progress = QProgressDialog(
            tr("diary.import_progress_message"),
            "",
            0,
            0,
            self,
        )
        progress.setWindowTitle(tr("diary.import_progress_title"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)

        self.btn_import_agi2rich.setEnabled(False)
        progress.show()
        QApplication.processEvents()

        try:
            from frontend.services.diary_service import DiaryService

            svc = DiaryService()
            result = svc.import_from_agi2rich_html(file_path)
            self._load_data()
            QMessageBox.information(
                self,
                tr("common.success"),
                tr(
                    "diary.import_summary",
                    result.get("total", 0),
                    result.get("created", 0),
                    result.get("duplicates", 0),
                    result.get("invalid", 0),
                ),
            )
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("diary.import_failed") + f": {e}")
        finally:
            progress.close()
            self.btn_import_agi2rich.setEnabled(True)
