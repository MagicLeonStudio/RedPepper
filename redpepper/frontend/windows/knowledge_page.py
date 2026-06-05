"""Knowledge Aggregation Page."""

from __future__ import annotations

import os
import importlib
import re
import tempfile
import webbrowser
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QComboBox,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

try:
    _qt_web_core = importlib.import_module("PyQt6.QtWebEngineCore")
    _qt_web_widgets = importlib.import_module("PyQt6.QtWebEngineWidgets")
    QWebEngineSettings = getattr(_qt_web_core, "QWebEngineSettings")
    QWebEngineView = getattr(_qt_web_widgets, "QWebEngineView")
    WEB_ENGINE_AVAILABLE = True
except Exception:
    QWebEngineSettings = None
    QWebEngineView = None
    WEB_ENGINE_AVAILABLE = False

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


class KnowledgePage(QWidget):
    """Knowledge page with HTML import, auto-tagging, preview and delete operations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._knowledge: list[dict] = []
        self._view_data: list[dict] = []
        self._preview_zoom_pct = 100
        self._last_preview_html: str = ""
        self._last_preview_base_dir: str = ""
        self._current_preview_item: dict | None = None
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel(tr("knowledge.title"))
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        self.btn_import_html = QPushButton("📥 " + tr("knowledge.import_html"))
        self.btn_import_html.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #0EA5E9;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #38BDF8; }}
            """
        )
        self.btn_import_html.clicked.connect(self._on_import_html)
        action_bar.addWidget(self.btn_import_html)

        self.btn_delete = QPushButton("🗑 " + tr("common.delete"))
        self.btn_delete.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #EF4444;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #F87171; }}
            """
        )
        self.btn_delete.clicked.connect(self._on_delete_selected)
        action_bar.addWidget(self.btn_delete)

        self.btn_batch_delete = QPushButton("🧹 " + tr("knowledge.batch_delete"))
        self.btn_batch_delete.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #B91C1C;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #DC2626; }}
            """
        )
        self.btn_batch_delete.clicked.connect(self._on_batch_delete)
        action_bar.addWidget(self.btn_batch_delete)

        self.btn_refresh = QPushButton("🔄 " + tr("common.refresh"))
        self.btn_refresh.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {ACCENT_PURPLE};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #A78BFA; }}
            """
        )
        self.btn_refresh.clicked.connect(self._load_data)
        action_bar.addWidget(self.btn_refresh)

        action_bar.addStretch()
        left_layout.addLayout(action_bar)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("knowledge.search_placeholder"))
        self.search_input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {BG_CARD};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {ACCENT_PURPLE}; }}
            """
        )
        self.search_input.textChanged.connect(self._on_search)
        left_layout.addWidget(self.search_input)

        self.knowledge_table = QTableWidget()
        self.knowledge_table.setColumnCount(5)
        self.knowledge_table.setHorizontalHeaderLabels(
            [
                tr("knowledge.title_col"),
                tr("knowledge.source_col"),
                tr("knowledge.tags_col"),
                tr("knowledge.summary_col"),
                tr("common.date"),
            ]
        )
        self.knowledge_table.setStyleSheet(TABLE_STYLE)
        self.knowledge_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.knowledge_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.knowledge_table.setAlternatingRowColors(True)
        self.knowledge_table.verticalHeader().setVisible(False)
        self.knowledge_table.setColumnWidth(0, 250)
        self.knowledge_table.setColumnWidth(1, 120)
        self.knowledge_table.setColumnWidth(2, 170)
        self.knowledge_table.setColumnWidth(3, 440)
        self.knowledge_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.knowledge_table.setColumnWidth(4, 96)
        self.knowledge_table.itemSelectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.knowledge_table, 1)

        self.empty_hint = QLabel(tr("knowledge.empty"))
        self.empty_hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.hide()
        left_layout.addWidget(self.empty_hint)

        form_box = QGroupBox(tr("knowledge.add_entry"))
        form_box.setStyleSheet(
            f"""
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
            QLineEdit {{
                background-color: {BG_DARK};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 6px;
            }}
            """
        )
        form_layout = QFormLayout(form_box)
        form_layout.setSpacing(8)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(tr("knowledge.title"))
        form_layout.addRow(tr("knowledge.title") + ":", self.title_input)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(tr("knowledge.url_placeholder"))
        form_layout.addRow(tr("knowledge.url") + ":", self.url_input)

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText(tr("knowledge.tags_placeholder"))
        form_layout.addRow(tr("knowledge.tags") + ":", self.tags_input)

        btn_add = QPushButton("➕ " + tr("knowledge.add_link"))
        btn_add.setStyleSheet(
            f"""
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
            """
        )
        btn_add.clicked.connect(self._on_add)
        form_layout.addRow(btn_add)

        left_layout.addWidget(form_box)

        content_splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_widget.setObjectName("knowledgePreviewPane")
        right_widget.setStyleSheet(
            f"""
            QWidget#knowledgePreviewPane {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_COLOR};
                border-radius: 10px;
            }}
            """
        )
        preview_layout = QVBoxLayout(right_widget)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_layout.setSpacing(8)

        preview_top_bar = QHBoxLayout()
        preview_top_bar.setSpacing(8)
        preview_label = QLabel(tr("knowledge.preview_title"))
        preview_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 700;")
        preview_top_bar.addWidget(preview_label)

        self.preview_title = QLabel("-")
        self.preview_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 700;")
        self.preview_title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        preview_top_bar.addWidget(self.preview_title, 1)

        zoom_label = QLabel(tr("knowledge.preview_zoom"))
        zoom_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        preview_top_bar.addWidget(zoom_label)

        self.btn_open_in_browser = QPushButton("🌐 " + tr("knowledge.open_in_browser"))
        self.btn_open_in_browser.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #3B82F6; }}
            """
        )
        self.btn_open_in_browser.clicked.connect(self._on_open_in_browser)
        preview_top_bar.addWidget(self.btn_open_in_browser)

        self.zoom_combo = QComboBox(self)
        self.zoom_combo.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {BG_DARK};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 4px 8px;
                min-width: 86px;
            }}
            """
        )
        for pct in (75, 90, 100, 110, 125, 150):
            self.zoom_combo.addItem(f"{pct}%", pct)
        self.zoom_combo.setCurrentText("100%")
        self.zoom_combo.currentIndexChanged.connect(self._on_zoom_changed)
        preview_top_bar.addWidget(self.zoom_combo)
        preview_layout.addLayout(preview_top_bar)

        if WEB_ENGINE_AVAILABLE:
            self.preview_web = QWebEngineView(self)
            settings = self.preview_web.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            self.preview_web.loadFinished.connect(self._on_web_load_finished)
            preview_layout.addWidget(self.preview_web, 1)
            self.preview_browser = None
        else:
            self.preview_web = None
            self.preview_browser = QTextBrowser(self)
            self.preview_browser.setOpenExternalLinks(True)
            self.preview_browser.setStyleSheet(
                "QTextBrowser { background: #FFFFFF; color: #1F2937; border: 1px solid #CBD5E1; border-radius: 8px; }"
            )
            preview_layout.addWidget(self.preview_browser, 1)

        content_splitter.addWidget(right_widget)
        content_splitter.setStretchFactor(0, 5)
        content_splitter.setStretchFactor(1, 7)
        content_splitter.setSizes([640, 860])
        layout.addWidget(content_splitter, 1)

        self._render_preview(None)

    def _service(self):
        from frontend.services.knowledge_service import KnowledgeService

        return KnowledgeService()

    def _load_data(self):
        try:
            self._knowledge = self._service().get_knowledge()
        except Exception:
            self._knowledge = []
        self._refresh_table(self._knowledge)

    def _refresh_table(self, data: list[dict]):
        self._view_data = list(data)
        self.knowledge_table.setRowCount(len(self._view_data))

        for row, item in enumerate(self._view_data):
            values = [
                str(item.get("title", "") or ""),
                str(item.get("source", "") or ""),
                str(item.get("tags", "") or ""),
                str(item.get("summary", "") or "")[:220],
                str(item.get("created_at", "") or "")[:10],
            ]
            for col, val in enumerate(values):
                cell = QTableWidgetItem(val)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.knowledge_table.setItem(row, col, cell)

        self.empty_hint.setVisible(len(self._view_data) == 0)
        if self._view_data:
            self.knowledge_table.selectRow(0)
            self._render_preview(self._view_data[0])
        else:
            self._render_preview(None)

    def _selected_rows(self) -> list[int]:
        rows = {idx.row() for idx in self.knowledge_table.selectionModel().selectedRows()}
        return sorted(rows)

    def _on_search(self, *_args):
        query = self.search_input.text().strip().lower()
        if not query:
            self._refresh_table(self._knowledge)
            return

        filtered = []
        for item in self._knowledge:
            haystack = " ".join(
                [
                    str(item.get("title", "") or ""),
                    str(item.get("source", "") or ""),
                    str(item.get("tags", "") or ""),
                    str(item.get("summary", "") or ""),
                ]
            ).lower()
            if query in haystack:
                filtered.append(item)

        self._refresh_table(filtered)

    def _on_add(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, tr("common.warning"), tr("knowledge.title_required"))
            return

        payload = {
            "title": title,
            "url": self.url_input.text().strip() or None,
            "source": "manual",
            "tags": self.tags_input.text().strip() or None,
            "summary": None,
        }

        try:
            self._service().add_knowledge(payload)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("knowledge.add_failed") + f": {e}")
            return

        self.title_input.clear()
        self.url_input.clear()
        self.tags_input.clear()
        self._load_data()

    def _on_import_html(self):
        html_files, _ = QFileDialog.getOpenFileNames(
            self,
            tr("knowledge.import_html"),
            "",
            "HTML Files (*.html *.htm)",
        )
        if not html_files:
            return

        images_dir = ""
        choose_images = QMessageBox.question(
            self,
            tr("knowledge.import_images_dir"),
            tr("knowledge.import_images_dir_optional"),
        )
        if choose_images == QMessageBox.StandardButton.Yes:
            images_dir = QFileDialog.getExistingDirectory(
                self,
                tr("knowledge.import_images_dir"),
                "",
            )

        progress = QProgressDialog(tr("knowledge.import_progress_message"), "", 0, 0, self)
        progress.setWindowTitle(tr("knowledge.import_progress_title"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)

        self.btn_import_html.setEnabled(False)
        progress.show()
        QApplication.processEvents()

        try:
            result = self._service().import_from_html_files(html_files, images_dir or None)
            self._load_data()
            QMessageBox.information(
                self,
                tr("common.success"),
                tr(
                    "knowledge.import_summary",
                    result.get("total", 0),
                    result.get("created", 0),
                    result.get("duplicates", 0),
                    result.get("invalid", 0),
                ),
            )
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("knowledge.import_failed") + f": {e}")
        finally:
            progress.close()
            self.btn_import_html.setEnabled(True)

    def _on_selection_changed(self):
        rows = self._selected_rows()
        if not rows:
            self._render_preview(None)
            return
        item = self._view_data[rows[0]]
        self._render_preview(item)

    def _on_zoom_changed(self):
        value = self.zoom_combo.currentData()
        if isinstance(value, int):
            self._preview_zoom_pct = value
            self._apply_preview_zoom()

    def _apply_preview_zoom(self):
        zoom_factor = max(0.25, min(3.0, self._preview_zoom_pct / 100.0))
        if self.preview_web is not None:
            self.preview_web.setZoomFactor(zoom_factor)
        elif self.preview_browser is not None:
            self.preview_browser.setStyleSheet(
                f"QTextBrowser {{ background: #FFFFFF; color: #1F2937; border: 1px solid #CBD5E1; border-radius: 8px; font-size: {self._preview_zoom_pct}%; }}"
            )

    def _on_web_load_finished(self, ok: bool):
        # Fallback when WebEngine fails to render (blank preview cases on some Windows setups).
        if ok:
            return
        if self.preview_browser is None:
            self.preview_browser = QTextBrowser(self)
            self.preview_browser.setOpenExternalLinks(True)
            self.preview_browser.setStyleSheet(
                "QTextBrowser { background: #FFFFFF; color: #1F2937; border: 1px solid #CBD5E1; border-radius: 8px; }"
            )
            parent_layout = self.preview_web.parentWidget().layout() if self.preview_web is not None else None
            if parent_layout is not None:
                parent_layout.addWidget(self.preview_browser, 1)

        if self.preview_web is not None:
            self.preview_web.hide()
        self.preview_browser.show()
        if self._last_preview_base_dir:
            self.preview_browser.document().setBaseUrl(
                QUrl.fromLocalFile(os.path.join(self._last_preview_base_dir, ""))
            )
        self.preview_browser.setHtml(self._last_preview_html or tr("knowledge.preview_empty"))
        self._apply_preview_zoom()

    def _load_html_from_url(self, url: str) -> tuple[str, str]:
        path = Path(str(url or "").strip()).expanduser()
        if not path.exists() or not path.is_file() or path.suffix.lower() not in {".html", ".htm"}:
            return "", ""

        for enc in ("utf-8", "utf-8-sig", "gbk"):
            try:
                text = path.read_text(encoding=enc)
                if text.strip():
                    return text, str(path.parent)
            except Exception:
                continue
        return "", ""

    def _inject_base_href(self, html: str, base_dir: str) -> str:
        if not base_dir:
            return html
        if re.search(r"<base\s+href=", html, flags=re.IGNORECASE):
            return html

        base_href = Path(base_dir).resolve().as_uri().rstrip("/") + "/"
        base_tag = f'<base href="{base_href}">'

        if re.search(r"<head[^>]*>", html, flags=re.IGNORECASE):
            return re.sub(r"(<head[^>]*>)", r"\1\n" + base_tag, html, count=1, flags=re.IGNORECASE)

        return f"<head>{base_tag}</head>\n" + html

    def _on_open_in_browser(self):
        item = self._current_preview_item
        if not item:
            QMessageBox.warning(self, tr("common.warning"), tr("knowledge.select_preview"))
            return

        try:
            url = str(item.get("url") or "").strip()
            url_path = Path(url).expanduser() if url else None

            if url_path and url_path.exists() and url_path.is_file() and url_path.suffix.lower() in {".html", ".htm"}:
                webbrowser.open(url_path.resolve().as_uri())
                return

            html = str(item.get("content_html") or self._last_preview_html or "").strip()
            base_dir = str(item.get("content_base_dir") or self._last_preview_base_dir or "").strip()
            if not html:
                QMessageBox.warning(self, tr("common.warning"), tr("knowledge.preview_empty"))
                return

            html = self._inject_base_href(html, base_dir)

            preview_dir = Path(tempfile.gettempdir()) / "redpepper_knowledge_preview"
            preview_dir.mkdir(parents=True, exist_ok=True)
            item_id = item.get("id")
            file_name = f"knowledge_{item_id if item_id is not None else 'preview'}.html"
            tmp_file = preview_dir / file_name
            tmp_file.write_text(html, encoding="utf-8")
            webbrowser.open(tmp_file.resolve().as_uri())
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("knowledge.open_failed") + f": {e}")

    def _render_preview(self, item: dict | None):
        if not item:
            self._current_preview_item = None
            self.preview_title.setText(tr("knowledge.preview_title"))
            placeholder = f"<div style='padding:24px;font-size:15px;color:#64748B;'>{tr('knowledge.preview_empty')}</div>"
            if self.preview_web is not None:
                self.preview_web.setHtml(placeholder)
            elif self.preview_browser is not None:
                self.preview_browser.setHtml(placeholder)
            return

        self._current_preview_item = item

        title = str(item.get("title") or "").strip()
        html = str(item.get("content_html") or "").strip()
        base_dir = str(item.get("content_base_dir") or "").strip()
        summary = str(item.get("summary") or "").strip()
        url = str(item.get("url") or "").strip()

        # Backward compatibility: legacy rows may not store content_html/content_base_dir.
        if not html:
            loaded_html, loaded_base_dir = self._load_html_from_url(url)
            if loaded_html:
                html = loaded_html
                if not base_dir:
                    base_dir = loaded_base_dir

        self.preview_title.setText(title or tr("knowledge.preview_title"))

        if not html:
            html = f"<h2>{title}</h2><p>{summary or tr('knowledge.preview_empty')}</p>"

        self._last_preview_html = html
        self._last_preview_base_dir = base_dir

        if self.preview_web is not None:
            # Prefer direct file loading to preserve original visual behavior.
            url_path = Path(url).expanduser() if url else None
            if url_path and url_path.exists() and url_path.is_file() and url_path.suffix.lower() in {".html", ".htm"}:
                self.preview_web.show()
                if self.preview_browser is not None:
                    self.preview_browser.hide()
                self.preview_web.setUrl(QUrl.fromLocalFile(str(url_path.resolve())))
            else:
                base_url = QUrl.fromLocalFile(os.path.join(base_dir, "")) if base_dir else QUrl()
                self.preview_web.show()
                if self.preview_browser is not None:
                    self.preview_browser.hide()
                self.preview_web.setHtml(html, base_url)
        elif self.preview_browser is not None:
            if base_dir:
                self.preview_browser.document().setBaseUrl(QUrl.fromLocalFile(os.path.join(base_dir, "")))
            self.preview_browser.setHtml(html)

        self._apply_preview_zoom()

    def _on_delete_selected(self):
        rows = self._selected_rows()
        if not rows:
            QMessageBox.warning(self, tr("common.warning"), tr("knowledge.select_delete"))
            return

        item = self._view_data[rows[0]]
        item_id = item.get("id")
        if item_id is None:
            QMessageBox.warning(self, tr("common.warning"), tr("knowledge.select_delete"))
            return

        ok = QMessageBox.question(
            self,
            tr("common.warning"),
            tr("knowledge.delete_confirm"),
        )
        if ok != QMessageBox.StandardButton.Yes:
            return

        try:
            self._service().delete(int(item_id))
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("knowledge.delete_failed") + f": {e}")
            return

        self._load_data()

    def _on_batch_delete(self):
        rows = self._selected_rows()
        if not rows:
            QMessageBox.warning(self, tr("common.warning"), tr("knowledge.select_batch_delete"))
            return

        ids: list[int] = []
        for row in rows:
            item_id = self._view_data[row].get("id")
            if item_id is not None:
                ids.append(int(item_id))

        if not ids:
            QMessageBox.warning(self, tr("common.warning"), tr("knowledge.select_batch_delete"))
            return

        ok = QMessageBox.question(
            self,
            tr("common.warning"),
            tr("knowledge.batch_delete_confirm", count=len(ids)),
        )
        if ok != QMessageBox.StandardButton.Yes:
            return

        try:
            deleted = self._service().batch_delete(ids)
        except Exception as e:
            QMessageBox.warning(self, tr("common.error"), tr("knowledge.delete_failed") + f": {e}")
            return

        self._load_data()
        QMessageBox.information(
            self,
            tr("common.success"),
            tr("knowledge.batch_delete_success", count=deleted),
        )
