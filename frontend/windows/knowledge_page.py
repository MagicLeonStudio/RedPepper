"""Knowledge Aggregation Page."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QLineEdit, QComboBox,
    QFormLayout, QGroupBox, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from frontend.i18n.translator import tr

# Color constants
BG_DARK = "#0D0D1A"
BG_CARD = "#1A1A2E"
TEXT_PRIMARY = "#E8E8F0"
TEXT_SECONDARY = "#7A7A9E"
BRAND_RED = "#E62E2E"
ACCENT_PURPLE = "#8B5CF6"
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
    QLineEdit {{
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
"""


class KnowledgePage(QWidget):
    """Knowledge aggregation page for collecting useful links and resources."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._knowledge = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel(tr("Knowledge Hub"))
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("Search knowledge..."))
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_CARD};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {ACCENT_PURPLE};
            }}
        """)
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)

        btn_search = QPushButton("🔍 " + tr("Search"))
        btn_search.setStyleSheet(f"""
            QPushButton {{
                background-color: {BRAND_RED};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: #FF4444; }}
        """)
        btn_search.clicked.connect(self._on_search)
        search_layout.addWidget(btn_search)

        layout.addLayout(search_layout)

        # Knowledge table
        self.knowledge_table = QTableWidget()
        self.knowledge_table.setColumnCount(4)
        self.knowledge_table.setHorizontalHeaderLabels([
            tr("Title"), tr("Source"), tr("Tags"), tr("URL")
        ])
        self.knowledge_table.setStyleSheet(TABLE_STYLE)
        self.knowledge_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.knowledge_table.setAlternatingRowColors(True)
        self.knowledge_table.verticalHeader().setVisible(False)
        self.knowledge_table.setColumnWidth(0, 200)
        self.knowledge_table.setColumnWidth(1, 100)
        self.knowledge_table.setColumnWidth(2, 150)
        self.knowledge_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.knowledge_table)

        # Empty hint
        self.empty_hint = QLabel(tr("No knowledge entries. Add your first link below."))
        self.empty_hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.hide()
        layout.addWidget(self.empty_hint)

        # Add link form
        form_box = QGroupBox(tr("Add Link"))
        form_box.setStyleSheet(GROUPBOX_STYLE)
        form_layout = QFormLayout(form_box)
        form_layout.setSpacing(10)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://")
        form_layout.addRow(tr("URL:"), self.url_input)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["zhihu", "Bilibili", "Web"])
        form_layout.addRow(tr("Source Type:"), self.source_combo)

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText(tr("e.g. value-investing, analysis"))
        form_layout.addRow(tr("Tags:"), self.tags_input)

        btn_add = QPushButton("➕ " + tr("Add Link"))
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {BRAND_RED};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #FF4444; }}
        """)
        btn_add.clicked.connect(self._on_add)
        form_layout.addRow(btn_add)

        layout.addWidget(form_box)

    def _load_data(self):
        try:
            from backend.services.knowledge_service import KnowledgeService
            svc = KnowledgeService()
            self._knowledge = svc.get_knowledge()
        except Exception:
            self._knowledge = []
        self._refresh_table()

    def _refresh_table(self, data=None):
        if data is None:
            data = self._knowledge
        self.knowledge_table.setRowCount(len(data))
        for row, item in enumerate(data):
            values = [
                item.get("title", ""),
                item.get("source", ""),
                item.get("tags", ""),
                item.get("url", ""),
            ]
            for col, val in enumerate(values):
                cell = QTableWidgetItem(val)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.knowledge_table.setItem(row, col, cell)

        if len(data) == 0:
            self.empty_hint.show()
        else:
            self.empty_hint.hide()

    def _on_search(self):
        query = self.search_input.text().strip().lower()
        if not query:
            self._refresh_table(self._knowledge)
            return
        filtered = [
            k for k in self._knowledge
            if query in k.get("title", "").lower()
            or query in k.get("tags", "").lower()
            or query in k.get("source", "").lower()
        ]
        self._refresh_table(filtered)

    def _on_add(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, tr("Warning"), tr("Please enter a URL"))
            return

        # Extract title from URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        title = parsed.netloc or url

        data = {
            "title": title,
            "url": url,
            "source": self.source_combo.currentText(),
            "tags": self.tags_input.text().strip(),
        }

        try:
            from backend.services.knowledge_service import KnowledgeService
            svc = KnowledgeService()
            svc.add_knowledge(data)
        except Exception:
            pass

        self._knowledge.insert(0, data)
        self._refresh_table()

        self.url_input.clear()
        self.tags_input.clear()
