"""Thin, provider-agnostic LLM client (Part 8: "AI integration").

AbilityOS Core does not depend on any single external AI provider — this is
the one place that knows how to actually call one. Swapping providers means
editing this file only. If the configured provider's SDK is not installed,
or the call fails for any reason, `call()` raises `LLMUnavailableError` and
the AI Decision Engine falls back to deterministic scoring.
"""

from __future__ import annotations

import json
import logging

from django.conf import settings

logger = logging.getLogger("ai_engine")


class LLMUnavailableError(Exception):
    """Raised whenever the configured LLM cannot be reached or is disabled."""


def is_configured() -> bool:
    return bool(settings.AI_AVAILABLE)


def call(system_prompt: str, user_prompt: str) -> str:
    """Returns the raw text content of the model's reply, or raises
    LLMUnavailableError."""

    if not is_configured():
        raise LLMUnavailableError("AI provider not configured (AI_PROVIDER/AI_API_KEY unset).")

    provider = settings.AI_PROVIDER

    try:
        if provider == "openai":
            return _call_openai(system_prompt, user_prompt)
        if provider == "anthropic":
            return _call_anthropic(system_prompt, user_prompt)
        raise LLMUnavailableError(f"Unknown AI_PROVIDER '{provider}'.")
    except LLMUnavailableError:
        raise
    except Exception as exc:  # network errors, SDK errors, timeouts, etc.
        logger.warning("LLM call failed (%s): %s", provider, exc)
        raise LLMUnavailableError(str(exc)) from exc


def _call_openai(system_prompt: str, user_prompt: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMUnavailableError("openai package not installed.") from exc

    client = OpenAI(api_key=settings.AI_API_KEY)
    response = client.chat.completions.create(
        model=settings.AI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def _call_anthropic(system_prompt: str, user_prompt: str) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise LLMUnavailableError("anthropic package not installed.") from exc

    client = anthropic.Anthropic(api_key=settings.AI_API_KEY)
    message = client.messages.create(
        model=settings.AI_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(block.text for block in message.content if hasattr(block, "text"))
    return text
