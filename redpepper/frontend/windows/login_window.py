"""Login / Set Password Window."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QWidget, QProgressBar, QFrame,
    QGraphicsDropShadowEffect, QSpacerItem, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QPixmap, QIcon

from frontend.i18n.translator import tr


class LoginWindow(QDialog):
    """Login or initial password setup dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("login.title"))
        self.setFixedSize(520, 700)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

        self._failed_attempts = 0
        self._is_first_use = True  # Will check via API

        self._build_ui()
        self._apply_styles()
        self._check_first_use()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _get_logo_path(self) -> str | None:
        """Resolve the path to the logo PNG."""
        candidates = [
            Path(__file__).resolve().parent.parent / "resources" / "logo.png",
            Path(__file__).resolve().parent.parent.parent.parent.parent / "frontend" / "resources" / "logo.png",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return None

    def _check_first_use(self):
        """Query backend to determine first-use mode."""
        try:
            from frontend.services.auth_service import AuthService
            auth = AuthService()
            result = auth.has_user()
            self._is_first_use = not result.get("has_user", False)
        except Exception:
            self._is_first_use = True
        self._first_use_mode = self._is_first_use
        self._update_mode_ui()

    # ------------------------------------------------------------------ #
    # UI Construction
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(56, 24, 56, 28)
        layout.setSpacing(12)

        # ---- Logo ----
        self.logo_label = QLabel()
        self.logo_label.setObjectName("LogoLabel")
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setMinimumHeight(88)
        logo_loaded = self._load_logo()
        layout.addWidget(self.logo_label)

        # ---- App name ----
        self.name_label = QLabel(tr("app_name"))
        self.name_label.setObjectName("BrandLabel")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setFont(QFont("Microsoft YaHei", 22, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: #E85D3B; margin-top: 0px; margin-bottom: 2px;")
        self.name_label.setVisible(not logo_loaded)
        layout.addWidget(self.name_label)

        # ---- Subtitle ----
        subtitle = QLabel(tr("login.subtitle"))
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Microsoft YaHei", 10))
        subtitle.setStyleSheet("color: #8B8FB2; margin-bottom: 10px;")
        layout.addWidget(subtitle)

        # ---- Divider line ----
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #2A2A3E; max-height: 1px; margin: 2px 0 4px 0;")
        layout.addWidget(line)

        layout.addSpacing(8)

        # ---- Dynamic Title ----
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Microsoft YaHei", 15, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #E8E8F0;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        layout.addSpacing(6)

        # ---- Username Input ----
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(tr("login.username_placeholder"))
        self.username_input.setMinimumHeight(44)
        layout.addWidget(self.username_input)

        # ---- Password Input ----
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(tr("login.password_placeholder"))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(44)
        self.password_input.textChanged.connect(self._on_password_changed)
        layout.addWidget(self.password_input)

        # ---- Confirm Password (first use only) ----
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText(tr("login.confirm_password"))
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setMinimumHeight(44)
        layout.addWidget(self.confirm_input)

        # ---- Password Strength Bar (first use only) ----
        self.strength_bar = QProgressBar()
        self.strength_bar.setMaximum(100)
        self.strength_bar.setValue(0)
        self.strength_bar.setTextVisible(True)
        self.strength_bar.setMaximumHeight(16)
        layout.addWidget(self.strength_bar)

        self.strength_label = QLabel(tr("login.password_strength"))
        self.strength_label.setStyleSheet("color: #7A7A9E; font-size: 11px;")
        layout.addWidget(self.strength_label)

        # ---- Error Message ----
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #EF4444; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_label)

        layout.addStretch(1)

        # ---- Action Button ----
        self.action_btn = QPushButton()
        self.action_btn.setMinimumHeight(48)
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.clicked.connect(self._on_action)
        layout.addWidget(self.action_btn)

        # ---- Switch Mode Link ----
        self.switch_btn = QPushButton()
        self.switch_btn.setFlat(True)
        self.switch_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #D4A017;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #F0C040;
            }
        """)
        self.switch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.switch_btn.clicked.connect(self._toggle_mode)
        layout.addWidget(self.switch_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # ---- Version ----
        version_label = QLabel("v0.1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #7A7A9E; font-size: 10px;")
        layout.addWidget(version_label)

    # ------------------------------------------------------------------ #
    # Logo loading
    # ------------------------------------------------------------------ #

    def _load_logo(self) -> bool:
        """Load and display the RedPepper logo."""
        logo_path = self._get_logo_path()
        if logo_path and os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                # Scale to fit while maintaining aspect ratio
                scaled = pixmap.scaled(
                    QSize(200, 92),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.logo_label.setPixmap(scaled)
                return True
        # Fallback: show a styled text logo
        self.logo_label.setText("🌶️")
        self.logo_label.setFont(QFont("Arial", 56))
        return False

    # ------------------------------------------------------------------ #
    # Styling
    # ------------------------------------------------------------------ #

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0B0D24;
            }
            QLabel {
                color: #E8E8F0;
            }
            QLabel#LogoLabel {
                margin-top: 4px;
                margin-bottom: 0px;
            }
            QLabel#BrandLabel {
                font-weight: 700;
                letter-spacing: 0.6px;
            }
            QLabel#SubtitleLabel {
                margin-bottom: 12px;
            }
            QLineEdit {
                background-color: #171A35;
                color: #E8E8F0;
                border: 1px solid #2D3E72;
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #3CB371;
            }
            QPushButton {
                background: qlineargradient(
                    spread: pad, x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #C23B22,
                    stop: 1 #9F5A9A
                );
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(
                    spread: pad, x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #E85D3B,
                    stop: 1 #B06AB3
                );
            }
            QPushButton:pressed {
                background: qlineargradient(
                    spread: pad, x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #A03018,
                    stop: 1 #5A3568
                );
            }
            QProgressBar {
                background-color: #1A1A2E;
                border: 1px solid #2A2A3E;
                border-radius: 4px;
                text-align: center;
                color: #E8E8F0;
            }
            QProgressBar::chunk {
                border-radius: 4px;
            }
        """)

    # ------------------------------------------------------------------ #
    # Mode switching (first-use vs login)
    # ------------------------------------------------------------------ #

    def _update_mode_ui(self):
        if self._first_use_mode:
            self.title_label.setText(tr("login.set_password_first"))
            self.action_btn.setText(tr("login.setup_btn"))
            self.username_input.show()
            self.confirm_input.show()
            self.strength_bar.show()
            self.strength_label.show()
            self.switch_btn.setText(tr("login.already_have_account"))
        else:
            self.title_label.setText(tr("login.title"))
            self.action_btn.setText(tr("login.login_btn"))
            self.username_input.show()
            self.confirm_input.hide()
            self.strength_bar.hide()
            self.strength_label.hide()
            self.switch_btn.setText(tr("login.first_time"))

    def _toggle_mode(self):
        self._first_use_mode = not self._first_use_mode
        self.error_label.setText("")
        self.password_input.clear()
        self.confirm_input.clear()
        self.username_input.clear()
        self.strength_bar.setValue(0)
        self._update_mode_ui()

    # ------------------------------------------------------------------ #
    # Password strength
    # ------------------------------------------------------------------ #

    def _evaluate_password_strength(self, password: str) -> int:
        if not password:
            return 0
        score = 0
        if len(password) >= 8:   score += 25
        if len(password) >= 12:  score += 15
        if any(c.isupper() for c in password):      score += 15
        if any(c.islower() for c in password):      score += 15
        if any(c.isdigit() for c in password):      score += 15
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):  score += 15
        return min(score, 100)

    def _on_password_changed(self, text: str):
        if not self._first_use_mode:
            return
        strength = self._evaluate_password_strength(text)
        self.strength_bar.setValue(strength)
        if strength < 40:
            self.strength_label.setText(tr("login.strength_weak"))
            self.strength_bar.setStyleSheet("""
                QProgressBar { background-color: #1A1A2E; border: 1px solid #2A2A3E; border-radius: 4px; text-align: center; }
                QProgressBar::chunk { background-color: #EF4444; border-radius: 4px; }
            """)
        elif strength < 70:
            self.strength_label.setText(tr("login.strength_medium"))
            self.strength_bar.setStyleSheet("""
                QProgressBar { background-color: #1A1A2E; border: 1px solid #2A2A3E; border-radius: 4px; text-align: center; }
                QProgressBar::chunk { background-color: #D4A017; border-radius: 4px; }
            """)
        else:
            self.strength_label.setText(tr("login.strength_strong"))
            self.strength_bar.setStyleSheet("""
                QProgressBar { background-color: #1A1A2E; border: 1px solid #2A2A3E; border-radius: 4px; text-align: center; }
                QProgressBar::chunk { background-color: #22C55E; border-radius: 4px; }
            """)

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def _validate_password(self, password: str) -> tuple[bool, str]:
        if len(password) < 8:
            return False, tr("login.password_too_short")
        has_letter = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)
        if not has_letter or not has_digit:
            return False, tr("login.password_requirements")
        return True, ""

    def _extract_http_error_detail(self, err: Exception) -> str:
        """Extract backend detail from HTTP errors for user-friendly display."""
        response = getattr(err, "response", None)
        if response is None:
            return str(err)
        try:
            payload = response.json()
            if isinstance(payload, dict) and payload.get("detail"):
                return str(payload["detail"])
        except Exception:
            pass
        return str(err)

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def _on_action(self):
        self.error_label.setText("")
        password = self.password_input.text()
        username = self.username_input.text().strip()

        if self._first_use_mode:
            # ---- Set password flow ----
            if not username:
                self.error_label.setText(tr("login.username_required"))
                return
            valid, msg = self._validate_password(password)
            if not valid:
                self.error_label.setText(msg)
                return
            confirm = self.confirm_input.text()
            if password != confirm:
                self.error_label.setText(tr("login.password_mismatch"))
                return
            try:
                from frontend.services.auth_service import AuthService
                auth = AuthService()
                result = auth.setup(username, password)
                if result:
                    self.accept()
                else:
                    self.error_label.setText(tr("login.setup_failed"))
            except Exception as e:
                self.error_label.setText(tr("login.error", self._extract_http_error_detail(e)))
        else:
            # ---- Login flow ----
            if not username:
                self.error_label.setText(tr("login.username_required"))
                return
            if not password:
                self.error_label.setText(tr("login.password_required"))
                return
            try:
                from frontend.services.auth_service import AuthService
                auth = AuthService()
                auth.login(username, password)
                self._failed_attempts = 0
                self.accept()
            except Exception as e:
                response = getattr(e, "response", None)
                if response is not None and response.status_code == 401:
                    # Retry once for accidental leading/trailing spaces in password input.
                    stripped_password = password.strip()
                    if stripped_password != password and stripped_password:
                        try:
                            from frontend.services.auth_service import AuthService
                            auth = AuthService()
                            auth.login(username, stripped_password)
                            self._failed_attempts = 0
                            self.accept()
                            return
                        except Exception:
                            pass
                    self._failed_attempts += 1
                    remaining = 5 - self._failed_attempts
                    if remaining <= 0:
                        self.error_label.setText(tr("login.too_many_attempts"))
                        self.action_btn.setEnabled(False)
                    else:
                        self.error_label.setText(tr("login.wrong_password_tip", remaining))
                    return
                self.error_label.setText(tr("login.error", self._extract_http_error_detail(e)))
