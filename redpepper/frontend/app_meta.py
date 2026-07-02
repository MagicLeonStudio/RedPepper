from __future__ import annotations

from pathlib import Path

APP_VERSION = "v0.0.7"


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def full_logo_path() -> Path:
    return project_root().parent / "assets" / "logo.png"


def logo_icon_path() -> Path:
    return project_root().parent / "assets" / "logo-icon.png"


def team_logo_path() -> Path:
    return project_root().parent / "assets" / "logo_mls.png"


def logo_path() -> Path:
    return full_logo_path()


def stylesheet_path() -> Path:
    return Path(__file__).resolve().parent / "resources" / "style.qss"
