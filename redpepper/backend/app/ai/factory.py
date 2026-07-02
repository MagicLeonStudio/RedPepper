"""AI Provider factory."""

from __future__ import annotations

from backend.app.ai.deepseek_provider import DeepSeekProvider
from backend.app.ai.kimi_provider import KimiProvider

PROVIDERS: dict[str, type] = {
    "kimi": KimiProvider,
    "deepseek": DeepSeekProvider,
}


def resolve_provider_target(name_or_model: str) -> tuple[str, object, str | None]:
    """Resolve a provider reference that may be a provider name or model name.

    Returns ``(provider_name, provider_config, model_name)``.
    """
    from backend.app.config import settings

    provider_config = settings.get(f"ai.providers.{name_or_model}")
    if provider_config:
        return name_or_model, provider_config, provider_config.get("default_model", None)

    providers = settings.get("ai.providers")
    if not providers:
        raise ValueError("No AI providers configured")

    for provider_name in PROVIDERS:
        candidate_config = settings.get(f"ai.providers.{provider_name}")
        if not candidate_config:
            continue

        default_model = candidate_config.get("default_model", None)
        if name_or_model == default_model:
            return provider_name, candidate_config, name_or_model

    # Fallback: infer the provider from a model-name prefix so scene_models can
    # reference specific models beyond each provider's default (e.g. the
    # "deepseek-v4-pro" model still maps to the "deepseek" provider).
    lowered = str(name_or_model or "").strip().lower()
    _MODEL_PREFIX_TO_PROVIDER = {
        "deepseek": "deepseek",
        "kimi": "kimi",
        "moonshot": "kimi",
    }
    for prefix, provider_name in _MODEL_PREFIX_TO_PROVIDER.items():
        if lowered.startswith(prefix):
            candidate_config = settings.get(f"ai.providers.{provider_name}")
            if candidate_config:
                return provider_name, candidate_config, name_or_model

    raise ValueError(f"Provider or model '{name_or_model}' is not configured")


def get_provider(name: str) -> KimiProvider | DeepSeekProvider:
    """Instantiate an AI provider by configuration name.

    The provider configuration is read from settings under the key
    ``ai.providers.<name>`` (supports dot-notation lookup).
    """
    from backend.app.config import settings

    provider_name, provider_config, _ = resolve_provider_target(name)

    api_key = provider_config.get("api_key", "")
    if not api_key:
        raise ValueError(f"Provider '{provider_name}' API key is not configured")

    provider_class = PROVIDERS[provider_name]
    return provider_class(
        api_key=api_key,
        base_url=provider_config.get("base_url", ""),
    )
