from __future__ import annotations

from pathlib import Path

import yaml

from frontend.app_meta import project_root


def _config_path() -> Path:
    return project_root() / "backend" / "config.yaml"


def get_ocr_runtime_target() -> tuple[str, str]:
    provider_name = "kimi"
    model_name = "kimi-k2.6"

    try:
        raw = yaml.safe_load(_config_path().read_text(encoding="utf-8")) or {}
    except Exception:
        return provider_name, model_name

    ai = raw.get("ai", {}) or {}
    providers = ai.get("providers", {}) or {}
    target = ai.get("scene_models", {}).get("screenshot_ocr") or ai.get("default_provider") or provider_name

    if target in providers:
        provider_name = target
        provider_cfg = providers.get(provider_name, {}) or {}
        model_name = str(provider_cfg.get("default_model") or provider_name)
        return provider_name, model_name

    for name, provider_cfg in providers.items():
        default_model = str((provider_cfg or {}).get("default_model") or "")
        if default_model == target:
            return name, default_model

    default_provider = str(ai.get("default_provider") or provider_name)
    provider_cfg = providers.get(default_provider, {}) or {}
    return default_provider, str(target or provider_cfg.get("default_model") or model_name)
