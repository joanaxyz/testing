from __future__ import annotations

from typing import Protocol

from django.conf import settings


class AIProviderRateLimited(Exception):
    pass


class AIProviderUnavailable(Exception):
    pass


class AIProviderClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...


class GroqProviderClient:
    def __init__(self):
        try:
            from groq import Groq
        except ImportError as exc:  # pragma: no cover - deployment configuration failure
            raise AIProviderUnavailable from exc
        self._client = Groq(
            api_key=settings.GROQ_API_KEY,
            timeout=settings.GROQ_TIMEOUT_SECONDS,
            max_retries=0,
        )

    def complete(self, messages: list[dict[str, str]]) -> str:
        try:
            completion = self._client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=messages,
                max_completion_tokens=settings.AI_CHAT_MAX_OUTPUT_TOKENS,
                temperature=0.2,
            )
        except Exception as exc:
            try:
                from groq import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
            except ImportError:  # pragma: no cover - handled during initialization
                raise AIProviderUnavailable from exc
            if isinstance(exc, RateLimitError):
                raise AIProviderRateLimited from exc
            if isinstance(exc, (APIConnectionError, APITimeoutError, APIStatusError)):
                raise AIProviderUnavailable from exc
            raise AIProviderUnavailable from exc

        content = completion.choices[0].message.content if completion.choices else None
        if not content or not content.strip():
            raise AIProviderUnavailable
        return content.strip()
