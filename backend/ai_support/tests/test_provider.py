from types import SimpleNamespace

import pytest

from ai_support.provider import (
    AIProviderRateLimited,
    AIProviderUnavailable,
    GroqProviderClient,
)


class FakeRateLimitError(Exception):
    pass


class FakeConnectionError(Exception):
    pass


class FakeTimeoutError(Exception):
    pass


class FakeStatusError(Exception):
    pass


class RaisingCompletions:
    def __init__(self, error):
        self.error = error

    def create(self, **_kwargs):
        raise self.error


def provider_raising(error):
    provider = GroqProviderClient.__new__(GroqProviderClient)
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=RaisingCompletions(error)))
    return provider


@pytest.fixture()
def fake_groq_errors(monkeypatch):
    module = SimpleNamespace(
        APIConnectionError=FakeConnectionError,
        APIStatusError=FakeStatusError,
        APITimeoutError=FakeTimeoutError,
        RateLimitError=FakeRateLimitError,
    )
    monkeypatch.setitem(__import__("sys").modules, "groq", module)


def test_provider_maps_rate_limit(fake_groq_errors):
    with pytest.raises(AIProviderRateLimited):
        provider_raising(FakeRateLimitError()).complete([])


@pytest.mark.parametrize("error", [FakeConnectionError(), FakeTimeoutError(), FakeStatusError()])
def test_provider_maps_outages_and_timeouts(fake_groq_errors, error):
    with pytest.raises(AIProviderUnavailable):
        provider_raising(error).complete([])


def test_provider_maps_unknown_failures(fake_groq_errors):
    with pytest.raises(AIProviderUnavailable):
        provider_raising(RuntimeError("secret provider detail")).complete([])
