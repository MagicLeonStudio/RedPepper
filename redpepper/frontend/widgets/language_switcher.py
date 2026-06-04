"""Language switcher dropdown component."""

from PyQt6.QtWidgets import QComboBox
from PyQt6.QtCore import pyqtSignal

from frontend.i18n.translator import get_locale, set_locale, tr


class LanguageSwitcher(QComboBox):
    """Language switcher dropdown that emits locale_changed signal."""

    locale_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_locale = get_locale()

        self.addItem("中文", "zh_CN")
        self.addItem("English", "en_US")

        self.setStyleSheet(
            f"""
            QComboBox {{
                background-color: #2A2A3E;
                color: #E8E8F0;
                border: 1px solid #338B5CF6;
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 100px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #2A2A3E;
                color: #E8E8F0;
                selection-background-color: #F05C77;
                selection-color: #FFFFFF;
                border: 1px solid #338B5CF6;
            }}
        """
        )

        self.currentIndexChanged.connect(self._on_selection_changed)
        current_index = self.findData(self._current_locale)
        if current_index >= 0:
            self.setCurrentIndex(current_index)

    def _on_selection_changed(self, index: int) -> None:
        """Handle locale selection change."""
        locale = self.itemData(index)
        if locale and locale != self._current_locale:
            self._current_locale = locale
            set_locale(locale)
            self.locale_changed.emit(locale)
