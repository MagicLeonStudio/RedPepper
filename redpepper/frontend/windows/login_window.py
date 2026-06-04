"""Login / Set Password Window."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QProgressBar, QFrame, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QRect, QParallelAnimationGroup
from PyQt6.QtGui import QFont, QColor, QPixmap, QIcon

from frontend.app_meta import APP_VERSION, full_logo_path, logo_icon_path, team_logo_path
from frontend.i18n.translator import tr


class LoginWindow(QDialog):
    """Login or initial password setup dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("login.title"))
        self.setFixedSize(560, 740)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        icon_path = logo_icon_path()
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._failed_attempts = 0
        self._is_first_use = True  # Will check via API
        self._intro_played = False
        self._intro_group = None

        self._build_ui()
        self._apply_styles()
        self._check_first_use()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _get_logo_path(self) -> str | None:
        """Resolve the path to the logo PNG."""
        path = full_logo_path()
        return str(path) if path.exists() else None

    def _get_team_logo_path(self) -> str | None:
        """Resolve the path to the team logo PNG."""
        path = team_logo_path()
        return str(path) if path.exists() else None

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
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(0)
        layout.addStretch(1)

        self.card = QFrame()
        self.card.setObjectName("LoginCard")
        card_shadow = QGraphicsDropShadowEffect(self.card)
        card_shadow.setBlurRadius(40)
        card_shadow.setOffset(0, 14)
        card_shadow.setColor(QColor(0, 0, 0, 150))
        self.card.setGraphicsEffect(card_shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(34, 24, 34, 22)
        card_layout.setSpacing(12)

        accent = QFrame()
        accent.setObjectName("TopAccent")
        accent.setFixedHeight(4)
        card_layout.addWidget(accent)

        card_layout.addSpacing(2)

        # ---- Logos (RedPepper + Team) ----
        logo_row = QHBoxLayout()
        logo_row.setSpacing(18)

        self.logo_label = QLabel()
        self.logo_label.setObjectName("LogoLabel")
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setMinimumHeight(84)
        logo_row.addWidget(self.logo_label, 1)

        self.team_logo_label = QLabel()
        self.team_logo_label.setObjectName("TeamLogoLabel")
        self.team_logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.team_logo_label.setMinimumHeight(84)
        logo_row.addWidget(self.team_logo_label, 1)

        redpepper_logo_loaded, team_logo_loaded = self._load_logos()
        card_layout.addLayout(logo_row)

        # ---- App name ----
        self.name_label = QLabel(tr("app_name"))
        self.name_label.setObjectName("BrandLabel")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setFont(QFont("Microsoft YaHei UI", 22, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: #F1704B; margin-top: 0px; margin-bottom: 0px;")
        self.name_label.setVisible(not (redpepper_logo_loaded or team_logo_loaded))
        card_layout.addWidget(self.name_label)

        # ---- Subtitle ----
        subtitle = QLabel(tr("login.subtitle"))
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Microsoft YaHei UI", 10))
        subtitle.setStyleSheet("color: #9FA7C7; margin-bottom: 10px;")
        card_layout.addWidget(subtitle)

        # ---- Divider line ----
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #2B335B; max-height: 1px; margin: 2px 0 6px 0;")
        card_layout.addWidget(line)

        card_layout.addSpacing(4)

        # ---- Dynamic Title ----
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Microsoft YaHei UI", 15, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #E8E8F0;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.title_label)

        card_layout.addSpacing(2)

        # ---- Username Input ----
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(tr("login.username_placeholder"))
        self.username_input.setObjectName("InputInRow")
        self.username_input.setMinimumHeight(46)
        self.username_row = self._build_input_row("👤", self.username_input)
        card_layout.addWidget(self.username_row)

        # ---- Password Input ----
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(tr("login.password_placeholder"))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setObjectName("InputInRow")
        self.password_input.setMinimumHeight(46)
        self.password_input.textChanged.connect(self._on_password_changed)
        self.password_row = self._build_input_row("🔒", self.password_input)
        card_layout.addWidget(self.password_row)

        # ---- Confirm Password (first use only) ----
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText(tr("login.confirm_password"))
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setObjectName("InputInRow")
        self.confirm_input.setMinimumHeight(46)
        self.confirm_row = self._build_input_row("🔐", self.confirm_input)
        card_layout.addWidget(self.confirm_row)

        # ---- Password Strength Bar (first use only) ----
        self.strength_bar = QProgressBar()
        self.strength_bar.setMaximum(100)
        self.strength_bar.setValue(0)
        self.strength_bar.setTextVisible(True)
        self.strength_bar.setMaximumHeight(16)
        card_layout.addWidget(self.strength_bar)

        self.strength_label = QLabel(tr("login.password_strength"))
        self.strength_label.setStyleSheet("color: #7A7A9E; font-size: 11px;")
        card_layout.addWidget(self.strength_label)

        # ---- Error Message ----
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #FF7A93; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.error_label)

        card_layout.addStretch(1)

        # ---- Action Button ----
        self.action_btn = QPushButton()
        self.action_btn.setObjectName("PrimaryActionButton")
        self.action_btn.setMinimumHeight(50)
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.clicked.connect(self._on_action)
        card_layout.addWidget(self.action_btn)

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
        card_layout.addWidget(self.switch_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # ---- Version ----
        version_label = QLabel(APP_VERSION)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #7A7A9E; font-size: 10px;")
        card_layout.addWidget(version_label)

        layout.addWidget(self.card)
        layout.addStretch(1)

    def _build_input_row(self, icon_text: str, input_widget: QLineEdit) -> QFrame:
        row = QFrame()
        row.setObjectName("InputRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 0, 12, 0)
        row_layout.setSpacing(8)

        icon_label = QLabel(icon_text)
        icon_label.setObjectName("InputIcon")
        icon_label.setFixedWidth(22)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(icon_label)

        row_layout.addWidget(input_widget, 1)
        return row

    # ------------------------------------------------------------------ #
    # Logo loading
    # ------------------------------------------------------------------ #

    def _load_logos(self) -> tuple[bool, bool]:
        """Load and display RedPepper + team logos side-by-side."""

        def _load_into(label: QLabel, path: str | None, fallback_text: str) -> bool:
            if path and os.path.exists(path):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        QSize(190, 86),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    label.setPixmap(scaled)
                    return True
            label.setText(fallback_text)
            label.setFont(QFont("Arial", 32))
            return False

        redpepper_loaded = _load_into(self.logo_label, self._get_logo_path(), "🌶️")
        team_loaded = _load_into(self.team_logo_label, self._get_team_logo_path(), "🏷")
        return redpepper_loaded, team_loaded

    # ------------------------------------------------------------------ #
    # Styling
    # ------------------------------------------------------------------ #

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: qradialgradient(
                    cx: 0.16, cy: 0.08, radius: 1.05,
                    fx: 0.16, fy: 0.08,
                    stop: 0 #2B1D37,
                    stop: 0.45 #131C3C,
                    stop: 1 #090E21
                );
            }
            QFrame#LoginCard {
                background-color: rgba(14, 19, 41, 0.94);
                border: 1px solid #334173;
                border-radius: 18px;
            }
            QFrame#TopAccent {
                border: none;
                border-radius: 2px;
                background: qlineargradient(
                    spread: pad, x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #EE6A43,
                    stop: 0.5 #E8B03A,
                    stop: 1 #F05C77
                );
            }
            QLabel {
                color: #E8E8F0;
            }
            QLabel#LogoLabel {
                margin-top: 2px;
                margin-bottom: 0px;
            }
            QLabel#TeamLogoLabel {
                margin-top: 2px;
                margin-bottom: 0px;
            }
            QLabel#BrandLabel {
                font-weight: 700;
                letter-spacing: 0.6px;
            }
            QLabel#SubtitleLabel {
                margin-bottom: 12px;
            }
            QFrame#InputRow {
                background-color: #1A2347;
                border: 1px solid #394A80;
                border-radius: 11px;
            }
            QLabel#InputIcon {
                color: #C8D3FF;
                font-size: 14px;
            }
            QLineEdit#InputInRow {
                background-color: transparent;
                color: #F2F5FF;
                border: none;
                border-radius: 0px;
                padding: 11px 2px;
                font-size: 14px;
            }
            QLineEdit#InputInRow:focus {
                background-color: transparent;
            }
            QPushButton#PrimaryActionButton {
                background: qlineargradient(
                    spread: pad, x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #E95F3E,
                    stop: 1 #D74B68
                );
                color: #FFFFFF;
                border: none;
                border-radius: 11px;
                padding: 12px 24px;
                font-size: 15px;
                font-weight: 700;
            }
            QPushButton#PrimaryActionButton:hover {
                background: qlineargradient(
                    spread: pad, x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #F37753,
                    stop: 1 #E45C7C
                );
            }
            QPushButton#PrimaryActionButton:pressed {
                background: qlineargradient(
                    spread: pad, x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #C94B31,
                    stop: 1 #B54057
                );
            }
            QProgressBar {
                background-color: #101735;
                border: 1px solid #2A355F;
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
            self.username_row.show()
            self.confirm_row.show()
            self.strength_bar.show()
            self.strength_label.show()
            self.switch_btn.setText(tr("login.already_have_account"))
        else:
            self.title_label.setText(tr("login.title"))
            self.action_btn.setText(tr("login.login_btn"))
            self.username_row.show()
            self.confirm_row.hide()
            self.strength_bar.hide()
            self.strength_label.hide()
            self.switch_btn.setText(tr("login.first_time"))

    def showEvent(self, event):
        super().showEvent(event)
        if not self._intro_played:
            self._intro_played = True
            self._run_intro_animation()

    def _run_intro_animation(self):
        end_rect = self.card.geometry()
        start_rect = QRect(end_rect.x(), end_rect.y() + 24, end_rect.width(), end_rect.height())

        self.card.setGeometry(start_rect)
        self.setWindowOpacity(0.0)

        move_anim = QPropertyAnimation(self.card, b"geometry", self)
        move_anim.setDuration(380)
        move_anim.setStartValue(start_rect)
        move_anim.setEndValue(end_rect)
        move_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        fade_anim.setDuration(320)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._intro_group = QParallelAnimationGroup(self)
        self._intro_group.addAnimation(move_anim)
        self._intro_group.addAnimation(fade_anim)
        self._intro_group.start()

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
                QProgressBar::chunk { background-color: #F05C77; border-radius: 4px; }
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
                QProgressBar::chunk { background-color: #8B6FD6; border-radius: 4px; }
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
