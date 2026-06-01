"""RedPepper configuration module.

Loads configuration from config.yaml and provides a global settings object
with dot-notation access to nested configuration values.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class ConfigSection:
    """A recursive configuration section that supports dot-notation access."""

    def __init__(self, data: dict[str, Any]) -> None:
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigSection(value))
            else:
                setattr(self, key, value)

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"ConfigSection({attrs})"

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key path (dot-notation)."""
        parts = key.split(".")
        obj: Any = self
        for part in parts:
            if isinstance(obj, ConfigSection) and hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return default
        return obj

    def to_dict(self) -> dict[str, Any]:
        """Convert the configuration section back to a dictionary."""
        result: dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if isinstance(value, ConfigSection):
                result[key] = value.to_dict()
            else:
                result[key] = value
        return result


class Settings:
    """Global application settings loaded from config.yaml."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        if config_path is None:
            # Look for config.yaml in the same directory as this file,
            # then fall back to the project root.
            here = Path(__file__).resolve().parent
            project_root = here.parent
            for candidate in (here / "config.yaml", project_root / "config.yaml"):
                if candidate.exists():
                    config_path = candidate
                    break
            if config_path is None:
                raise FileNotFoundError(
                    "config.yaml not found. Please provide an explicit config_path."
                )

        self._config_path = Path(config_path)
        self._raw: dict[str, Any] = {}
        self._reload()

    def _reload(self) -> None:
        """Reload configuration from the YAML file."""
        with open(self._config_path, "r", encoding="utf-8") as fh:
            self._raw = yaml.safe_load(fh) or {}
        for key, value in self._raw.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigSection(value))
            else:
                setattr(self, key, value)

    @property
    def raw(self) -> dict[str, Any]:
        """Return the raw configuration dictionary."""
        return self._raw

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key path (e.g. 'ai.default_provider')."""
        parts = key.split(".")
        obj: Any = self
        for part in parts:
            if isinstance(obj, ConfigSection) and hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return default
        return obj

    def reload(self) -> None:
        """Reload configuration from disk."""
        self._reload()


# ---------------------------------------------------------------------------
# Global settings singleton
# ---------------------------------------------------------------------------

_settings_instance: Settings | None = None


def get_settings(config_path: str | Path | None = None) -> Settings:
    """Return the global Settings singleton."""
    global _settings_instance
    if _settings_instance is None or config_path is not None:
        _settings_instance = Settings(config_path)
    return _settings_instance


# Shortcut for direct import
settings = get_settings()
