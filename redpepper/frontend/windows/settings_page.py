"""Settings Page."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFormLayout, QGroupBox, QMessageBox,
    QFileDialog, QScrollArea, QFrame, QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

from frontend.app_meta import APP_VERSION, logo_icon_path
from frontend.i18n.translator import tr
from frontend.widgets.language_switcher import LanguageSwitcher

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

GROUPBOX_STYLE = f"""
    QGroupBox {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_COLOR};
        border-radius: 10px;
        color: {TEXT_SECONDARY};
        font-size: 13px;
        font-weight: bold;
        margin-top: 16px;
        padding: 18px 12px 12px 12px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 8px;
        top: -2px;
        padding: 0 6px;
        background-color: {BG_CARD};
        color: #F2C94C;
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
        self._load_ai_config()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel(tr("settings.title"))
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Weight.Bold))
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
        lang_box = QGroupBox(tr("settings.language"))
        lang_box.setStyleSheet(GROUPBOX_STYLE)
        lang_layout = QFormLayout(lang_box)
        self._configure_form_layout(lang_layout)

        self.lang_switcher = LanguageSwitcher()
        self.lang_switcher.locale_changed.connect(self._on_locale_changed)
        lang_layout.addRow(tr("settings.language"), self.lang_switcher)

        container_layout.addWidget(lang_box)

        # === AI Configuration ===
        ai_box = QGroupBox(tr("settings.ai_config"))
        ai_box.setStyleSheet(GROUPBOX_STYLE)
        ai_layout = QFormLayout(ai_box)
        self._configure_form_layout(ai_layout)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["Kimi", "DeepSeek"])
        ai_layout.addRow(tr("settings.default_provider"), self.model_combo)

        self.kimi_key = QLineEdit()
        self.kimi_key.setPlaceholderText(tr("settings.api_key_kimi"))
        self.kimi_key.setEchoMode(QLineEdit.EchoMode.Password)
        ai_layout.addRow(tr("settings.api_key_kimi"), self.kimi_key)

        self.deepseek_key = QLineEdit()
        self.deepseek_key.setPlaceholderText(tr("settings.api_key_deepseek"))
        self.deepseek_key.setEchoMode(QLineEdit.EchoMode.Password)
        ai_layout.addRow(tr("settings.api_key_deepseek"), self.deepseek_key)

        btn_save_ai = QPushButton("💾 " + tr("common.save"))
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
        sec_box = QGroupBox(tr("settings.security"))
        sec_box.setStyleSheet(GROUPBOX_STYLE)
        sec_layout = QFormLayout(sec_box)
        self._configure_form_layout(sec_layout)

        self.old_password = QLineEdit()
        self.old_password.setPlaceholderText(tr("settings.old_password"))
        self.old_password.setEchoMode(QLineEdit.EchoMode.Password)
        sec_layout.addRow(tr("settings.old_password"), self.old_password)

        self.new_password = QLineEdit()
        self.new_password.setPlaceholderText(tr("settings.new_password"))
        self.new_password.setEchoMode(QLineEdit.EchoMode.Password)
        sec_layout.addRow(tr("settings.new_password"), self.new_password)

        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText(tr("login.confirm_password"))
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        sec_layout.addRow(tr("login.confirm_password"), self.confirm_password)

        btn_change = QPushButton("🔐 " + tr("settings.change_password"))
        btn_change.setStyleSheet(f"""
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
        btn_change.clicked.connect(self._on_change_password)
        sec_layout.addRow(btn_change)

        container_layout.addWidget(sec_box)

        # === Data Management ===
        data_box = QGroupBox(tr("settings.data_management"))
        data_box.setStyleSheet(GROUPBOX_STYLE)
        data_layout = QVBoxLayout(data_box)
        data_layout.setSpacing(10)

        data_btns = QHBoxLayout()

        btn_export = QPushButton("📤 " + tr("settings.export_data"))
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

        btn_import = QPushButton("📥 " + tr("settings.import_data"))
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

        btn_reset = QPushButton("⚠️ " + tr("settings.reset_data"))
        btn_reset.setStyleSheet(DANGER_BTN_STYLE)
        btn_reset.clicked.connect(self._on_reset)
        data_layout.addWidget(btn_reset)

        container_layout.addWidget(data_box)

        # === About ===
        about_box = QGroupBox(tr("settings.about"))
        about_box.setStyleSheet(GROUPBOX_STYLE)
        about_layout = QVBoxLayout(about_box)
        about_layout.setSpacing(8)

        app_name = QLabel()
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_path = logo_icon_path()
        if icon_path.exists():
            app_name.setPixmap(
                QPixmap(str(icon_path)).scaled(
                    72,
                    72,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            app_name.setText("RedPepper")
            app_name.setFont(QFont("Microsoft YaHei UI", 16, QFont.Weight.Bold))
            app_name.setStyleSheet(f"color: {BRAND_RED};")
        about_layout.addWidget(app_name)

        version = QLabel(f"{tr('settings.version')}: {APP_VERSION}")
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

    def _configure_form_layout(self, form_layout: QFormLayout) -> None:
        form_layout.setSpacing(14)
        form_layout.setHorizontalSpacing(18)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

    def _on_save_ai(self):
        model = self.model_combo.currentText()
        kimi = self.kimi_key.text()
        deepseek = self.deepseek_key.text()
        provider_map = {
            "Kimi": "kimi",
            "DeepSeek": "deepseek",
        }
        default_provider = provider_map.get(model)

        if not default_provider:
            QMessageBox.warning(self, tr("Warning"), tr("Unsupported AI provider"))
            return

        try:
            from frontend.services.data_service import DataService
            svc = DataService()
            svc.save_ai_config({
                "default_provider": default_provider,
                "providers": {
                    "kimi": {"api_key": kimi},
                    "deepseek": {"api_key": deepseek},
                },
            })
            self._load_ai_config()
            QMessageBox.information(self, tr("Success"), tr("AI settings saved"))
        except Exception as e:
            QMessageBox.warning(self, tr("Error"), tr("Failed to save AI settings") + f": {e}")

    def _load_ai_config(self) -> None:
        try:
            from frontend.services.data_service import DataService

            config = DataService().load_ai_config()
        except Exception:
            return

        default_provider = str(config.get("default_provider") or "kimi").lower()
        provider_labels = {
            "kimi": "Kimi",
            "deepseek": "DeepSeek",
        }
        label = provider_labels.get(default_provider, "Kimi")
        index = self.model_combo.findText(label)
        self.model_combo.setCurrentIndex(index if index >= 0 else 0)

        kimi_key = str((config.get("providers", {}).get("kimi", {}) or {}).get("api_key") or "")
        deepseek_key = str((config.get("providers", {}).get("deepseek", {}) or {}).get("api_key") or "")
        self.kimi_key.setText(kimi_key)
        self.deepseek_key.setText(deepseek_key)

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
            from frontend.services.auth_service import AuthService
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

    def _on_locale_changed(self, locale: str) -> None:
        window = self.window()
        if hasattr(window, "_on_locale_changed"):
            window._on_locale_changed(locale)

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Export Data"), "redpepper_data.redpepper",
            tr("RedPepper Backup (*.redpepper)")
        )
        if path:
            password, ok = QInputDialog.getText(
                self,
                tr("Export Data"),
                tr("Enter your password for export:"),
                QLineEdit.EchoMode.Password,
            )
            if not ok or not password:
                return

            try:
                from frontend.services.data_service import DataService
                svc = DataService()
                svc.export_data(password, path)
                QMessageBox.information(self, tr("Success"), tr("Data exported to") + f" {path}")
            except Exception as e:
                QMessageBox.warning(self, tr("Error"), tr("Export failed") + f": {e}")

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Import Data"), "",
            tr("RedPepper Backup (*.redpepper)")
        )
        if path:
            password, ok = QInputDialog.getText(
                self,
                tr("Import Data"),
                tr("Enter the backup password:"),
                QLineEdit.EchoMode.Password,
            )
            if not ok or not password:
                return

            try:
                from frontend.services.data_service import DataService
                svc = DataService()
                svc.import_data(path, password)
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
                    from frontend.services.data_service import DataService
                    svc = DataService()
                    result = svc.reset_all_data()
                    QMessageBox.information(
                        self,
                        tr("Info"),
                        result.get("message", tr("Reset is not available yet")),
                    )
                except Exception as e:
                    QMessageBox.warning(self, tr("Error"), tr("Reset failed") + f": {e}")
