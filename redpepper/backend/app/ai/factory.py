"""AI Provider factory."""

from __future__ import annotations

from app.ai.deepseek_provider import DeepSeekProvider
from app.ai.kimi_provider import KimiProvider

PROVIDERS: dict[str, type] = {
    "kimi": KimiProvider,
    "deepseek": DeepSeekProvider,
}


def get_provider(name: str) -> KimiProvider | DeepSeekProvider:
    """Instantiate an AI provider by configuration name.

    The provider configuration is read from settings under the key
    ``ai.providers.<name>`` (supports dot-notation lookup).
    """
    from app.config import settings

    provider_config = settings.get(f"ai.providers.{name}")
    if not provider_config:
        raise ValueError(f"Provider {name} not configured")

    provider_class = PROVIDERS[name]
    return provider_class(
        api_key=provider_config.get("api_key", ""),
        base_url=provider_config.get("base_url", ""),
    )
