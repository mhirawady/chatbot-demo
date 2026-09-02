"""Selects the configured LLM provider."""

from config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    ProviderName,
)
from providers.base import LLMProvider


def build_provider(name: ProviderName) -> LLMProvider:
    """Instantiate the adapter for the named provider."""
    if name == "anthropic":
        from providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=ANTHROPIC_API_KEY)
    if name == "openrouter":
        from providers.openrouter_provider import OpenRouterProvider

        return OpenRouterProvider(api_key=OPENROUTER_API_KEY)
    raise ValueError(f"Unknown provider: {name!r}")


def resolve_model(name: ProviderName) -> str:
    """Return the model identifier for the named provider."""
    if name == "anthropic":
        return ANTHROPIC_MODEL
    if name == "openrouter":
        return OPENROUTER_MODEL
    raise ValueError(f"Unknown provider: {name!r}")
