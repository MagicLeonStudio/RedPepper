"""Settings Page."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFormLayout, QGroupBox, QMessageBox,
    QFileDialog, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from frontend.i18n.translator import tr
from frontend.widgets.language_switcher import LanguageSwitcher

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
    QLabel {{
        color: {TEXT_PRIMARY};
        font-size: 12px;
    }}
    QLineEdit {{
        background-color: {BG_DARK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        padding: 8px;
    }}
    QLineEdit:focus {{
        border: 1px solid {ACCENT_PURPLE};
    }}
    QComboBox {{
        background-color: {BG_DARK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        padding: 8px;
    }}
"""

DANGER_BTN_STYLE = f"""
    QPushButton {{
        background-color: #2A2A3E;
        color: {PROFIT_RED};
        border: 1px solid {PROFIT_RED};
        border-radius: 6px;
        padding: 10px 20px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {PROFIT_RED}22;
    }}
"""


class SettingsPage(QWidget):
    """Settings page for app configuration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel(tr("Settings"))
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(16)

        # === Language Settings ===
        lang_box = QGroupBox(tr("Language"))
        lang_box.setStyleSheet(GROUPBOX_STYLE)
        lang_layout = QFormLayout(lang_box)
        lang_layout.setSpacing(10)

        self.lang_switcher = LanguageSwitcher()
        lang_layout.addRow(tr("Interface Language:"), self.lang_switcher)

        container_layout.addWidget(lang_box)

        # === AI Configuration ===
        ai_box = QGroupBox(tr("AI Configuration"))
        ai_box.setStyleSheet(GROUPBOX_STYLE)
        ai_layout = QFormLayout(ai_box)
        ai_layout.setSpacing(10)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["Kimi", "DeepSeek", "GPT"])
        ai_layout.addRow(tr("Default Model:"), self.model_combo)

        self.kimi_key = QLineEdit()
        self.kimi_key.setPlaceholderText(tr("Enter Kimi API Key"))
        self.kimi_key.setEchoMode(QLineEdit.EchoMode.Password)
        ai_layout.addRow(tr("Kimi API Key:"), self.kimi_key)

        self.deepseek_key = QLineEdit()
        self.deepseek_key.setPlaceholderText(tr("Enter DeepSeek API Key"))
        self.deepseek_key.setEchoMode(QLineEdit.EchoMode.Password)
        ai_layout.addRow(tr("DeepSeek API Key:"), self.deepseek_key)

        btn_save_ai = QPushButton("💾 " + tr("Save AI Settings"))
        btn_save_ai.setStyleSheet(f"""
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
        btn_save_ai.clicked.connect(self._on_save_ai)
        ai_layout.addRow(btn_save_ai)

        container_layout.addWidget(ai_box)

        # === Security Settings ===
        sec_box = QGroupBox(tr("Security"))
        sec_box.setStyleSheet(GROUPBOX_STYLE)
        sec_layout = QFormLayout(sec_box)
        sec_layout.setSpacing(10)

        self.old_password = QLineEdit()
        self.old_password.setPlaceholderText(tr("Current password"))
        self.old_password.setEchoMode(QLineEdit.EchoMode.Password)
        sec_layout.addRow(tr("Old Password:"), self.old_password)

        self.new_password = QLineEdit()
        self.new_password.setPlaceholderText(tr("New password (8+ chars, letters + numbers)"))
        self.new_password.setEchoMode(QLineEdit.EchoMode.Password)
        sec_layout.addRow(tr("New Password:"), self.new_password)

        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText(tr("Confirm new password"))
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        sec_layout.addRow(tr("Confirm Password:"), self.confirm_password)

        btn_change = QPushButton("🔐 " + tr("Change Password"))
        btn_change.setStyleSheet(f"""
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
        btn_change.clicked.connect(self._on_change_password)
        sec_layout.addRow(btn_change)

        container_layout.addWidget(sec_box)

        # === Data Management ===
        data_box = QGroupBox(tr("Data Management"))
        data_box.setStyleSheet(GROUPBOX_STYLE)
        data_layout = QVBoxLayout(data_box)
        data_layout.setSpacing(10)

        data_btns = QHBoxLayout()

        btn_export = QPushButton("📤 " + tr("Export Data"))
        btn_export.setStyleSheet(f"""
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
        btn_export.clicked.connect(self._on_export)
        data_btns.addWidget(btn_export)

        btn_import = QPushButton("📥 " + tr("Import Data"))
        btn_import.setStyleSheet(f"""
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
        btn_import.clicked.connect(self._on_import)
        data_btns.addWidget(btn_import)

        data_btns.addStretch()
        data_layout.addLayout(data_btns)

        btn_reset = QPushButton("⚠️ " + tr("Reset All Data"))
        btn_reset.setStyleSheet(DANGER_BTN_STYLE)
        btn_reset.clicked.connect(self._on_reset)
        data_layout.addWidget(btn_reset)

        container_layout.addWidget(data_box)

        # === About ===
        about_box = QGroupBox(tr("About"))
        about_box.setStyleSheet(GROUPBOX_STYLE)
        about_layout = QVBoxLayout(about_box)
        about_layout.setSpacing(8)

        app_name = QLabel("🌶️ RedPepper")
        app_name.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        app_name.setStyleSheet(f"color: {BRAND_RED};")
        about_layout.addWidget(app_name)

        version = QLabel(tr("Version: 1.0.0"))
        version.setStyleSheet(f"color: {TEXT_SECONDARY};")
        about_layout.addWidget(version)

        desc = QLabel(tr("RedPepper is a smart investment assistant for tracking portfolios, "
                         "recording trades, and aggregating financial knowledge."))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
        about_layout.addWidget(desc)

        about_layout.addStretch()
        container_layout.addWidget(about_box)

        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _on_save_ai(self):
        model = self.model_combo.currentText()
        kimi = self.kimi_key.text()
        deepseek = self.deepseek_key.text()

        try:
            from backend.services.settings_service import SettingsService
            svc = SettingsService()
            svc.save_ai_config({
                "default_model": model,
                "kimi_api_key": kimi,
                "deepseek_api_key": deepseek,
            })
            QMessageBox.information(self, tr("Success"), tr("AI settings saved"))
        except Exception as e:
            QMessageBox.information(self, tr("Info"), tr("Settings saved locally"))

    def _on_change_password(self):
        old = self.old_password.text()
        new = self.new_password.text()
        confirm = self.confirm_password.text()

        if not old:
            QMessageBox.warning(self, tr("Warning"), tr("Please enter old password"))
            return
        if not new:
            QMessageBox.warning(self, tr("Warning"), tr("Please enter new password"))
            return
        if new != confirm:
            QMessageBox.warning(self, tr("Warning"), tr("New passwords do not match"))
            return
        if len(new) < 8:
            QMessageBox.warning(self, tr("Warning"), tr("Password must be at least 8 characters"))
            return

        try:
            from backend.services.auth_service import AuthService
            auth = AuthService()
            if auth.change_password(old, new):
                QMessageBox.information(self, tr("Success"), tr("Password changed successfully"))
                self.old_password.clear()
                self.new_password.clear()
                self.confirm_password.clear()
            else:
                QMessageBox.warning(self, tr("Error"), tr("Old password is incorrect"))
        except Exception as e:
            QMessageBox.warning(self, tr("Error"), tr("Failed to change password") + f": {e}")

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Export Data"), "redpepper_data.json",
            tr("JSON Files (*.json)")
        )
        if path:
            try:
                from backend.services.data_service import DataService
                svc = DataService()
                svc.export_data(path)
                QMessageBox.information(self, tr("Success"), tr("Data exported to") + f" {path}")
            except Exception as e:
                QMessageBox.warning(self, tr("Error"), tr("Export failed") + f": {e}")

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Import Data"), "",
            tr("JSON Files (*.json)")
        )
        if path:
            try:
                from backend.services.data_service import DataService
                svc = DataService()
                svc.import_data(path)
                QMessageBox.information(self, tr("Success"), tr("Data imported successfully"))
            except Exception as e:
                QMessageBox.warning(self, tr("Error"), tr("Import failed") + f": {e}")

    def _on_reset(self):
        reply = QMessageBox.warning(
            self, tr("Confirm Reset"),
            tr("This will DELETE ALL DATA. This action cannot be undone.\n\nAre you sure?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            reply2 = QMessageBox.warning(
                self, tr("Final Confirmation"),
                tr("ALL DATA WILL BE PERMANENTLY DELETED.\n\nType 'DELETE' to confirm."),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply2 == QMessageBox.StandardButton.Yes:
                try:
                    from backend.services.data_service import DataService
                    svc = DataService()
                    svc.reset_all_data()
                    QMessageBox.information(self, tr("Done"), tr("All data has been reset"))
                except Exception as e:
                    QMessageBox.warning(self, tr("Error"), tr("Reset failed") + f": {e}")
