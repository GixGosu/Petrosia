from typing import Optional
from .base import BaseLLMProvider
from .claude import ClaudeProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider
from .mistral import MistralProvider
from .ollama import OllamaProvider
from config import settings

_provider_cache = {}


def get_llm_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None
) -> BaseLLMProvider:
    """Factory function to get LLM provider instance. Results are cached by (provider_name, model)."""

    provider_name = provider_name or settings.DEFAULT_LLM_PROVIDER

    cache_key = (provider_name, model)
    if cache_key in _provider_cache:
        return _provider_cache[cache_key]

    if provider_name == "claude":
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        resolved_model = model or "claude-sonnet-4-20250514"
        instance = ClaudeProvider(settings.ANTHROPIC_API_KEY, resolved_model)

    elif provider_name == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")
        resolved_model = model or "gpt-4o-mini"
        instance = OpenAIProvider(settings.OPENAI_API_KEY, resolved_model)

    elif provider_name == "gemini":
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not configured")
        resolved_model = model or "gemini-2.0-flash-exp"
        instance = GeminiProvider(settings.GOOGLE_API_KEY, resolved_model)

    elif provider_name == "mistral":
        if not settings.MISTRAL_API_KEY:
            raise ValueError("MISTRAL_API_KEY not configured")
        resolved_model = model or "mistral-small-latest"
        instance = MistralProvider(settings.MISTRAL_API_KEY, resolved_model)

    elif provider_name == "ollama":
        resolved_model = model or settings.DEFAULT_LLM_MODEL
        instance = OllamaProvider(settings.OLLAMA_BASE_URL, resolved_model)

    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")

    _provider_cache[cache_key] = instance
    return instance
