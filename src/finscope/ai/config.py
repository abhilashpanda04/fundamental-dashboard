"""AI provider detection and model configuration.

Scans environment variables to find the first available LLM provider
and returns a pydantic-ai model string.  The priority order can be
overridden by setting ``FINSCOPE_AI_MODEL`` explicitly.

Environment variables checked (in order):
    FINSCOPE_AI_MODEL   → explicit override (e.g. "openai:gpt-4o")
    OPENAI_API_KEY      → openai:gpt-4o
    ANTHROPIC_API_KEY   → anthropic:claude-sonnet-4-20250514
    GEMINI_API_KEY      → google-gla:gemini-2.0-flash
    GROQ_API_KEY        → groq:llama-3.3-70b-versatile
    MISTRAL_API_KEY     → mistral:mistral-large-latest
"""

from __future__ import annotations

import os

__all__ = ["get_ai_model", "is_ai_available", "get_ai_status"]

# ── Provider detection order ──────────────────────────────────────────────────

_PROVIDERS: list[tuple[str, str, str]] = [
    # (env_var,            model_string,                         display_name)
    ("OPENAI_API_KEY",     "openai:gpt-4o",                     "OpenAI GPT-4o"),
    ("ANTHROPIC_API_KEY",  "anthropic:claude-sonnet-4-20250514",        "Anthropic Claude Sonnet"),
    ("GEMINI_API_KEY",     "google-gla:gemini-2.0-flash",       "Google Gemini 2.0 Flash"),
    ("GROQ_API_KEY",       "groq:llama-3.3-70b-versatile",      "Groq Llama 3.3 70B"),
    ("MISTRAL_API_KEY",    "mistral:mistral-large-latest",      "Mistral Large"),
]


def get_ai_model() -> str | None:
    """Return the pydantic-ai model string for the first available provider.

    Returns ``None`` when no API key is found in the environment.

    If ``FINSCOPE_AI_MODEL`` is set, it takes absolute priority::

        export FINSCOPE_AI_MODEL="openai:gpt-4o-mini"
    """
    # Explicit override
    explicit = os.environ.get("FINSCOPE_AI_MODEL")
    if explicit:
        return explicit

    # Auto-detect from env vars
    for env_var, model_string, _ in _PROVIDERS:
        if os.environ.get(env_var):
            return model_string

    return None


def is_ai_available() -> bool:
    """Return ``True`` if at least one LLM provider is configured."""
    return get_ai_model() is not None


def get_ai_status() -> dict[str, str | bool]:
    """Return a status dict describing the active AI provider.

    Useful for CLI ``--status`` and debugging::

        >>> get_ai_status()
        {'available': True, 'model': 'openai:gpt-4o', 'provider': 'OpenAI GPT-4o'}
    """
    explicit = os.environ.get("FINSCOPE_AI_MODEL")
    if explicit:
        return {
            "available": True,
            "model": explicit,
            "provider": f"Custom ({explicit})",
        }

    for env_var, model_string, display_name in _PROVIDERS:
        if os.environ.get(env_var):
            return {
                "available": True,
                "model": model_string,
                "provider": display_name,
            }

    return {"available": False, "model": None, "provider": None}
