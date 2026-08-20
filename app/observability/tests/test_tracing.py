"""Tests for observability helpers (noop path; no Langfuse required)."""

from __future__ import annotations

import pytest

from app.config.settings import get_settings
from app.observability import flush_tracing, is_tracing_enabled, observation, sanitize
from app.observability.tracing import NullObservation


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_sanitize_redacts_secret_keys() -> None:
    cleaned = sanitize(
        {
            "question": "Why did Premium drop?",
            "api_key": "sk-secret",
            "nested": {"password": "x", "ok": 1},
        }
    )
    assert cleaned["api_key"] == "[redacted]"
    assert cleaned["nested"]["password"] == "[redacted]"
    assert cleaned["nested"]["ok"] == 1
    assert cleaned["question"].startswith("Why")


def test_sanitize_truncates_long_strings() -> None:
    assert len(sanitize("a" * 2000, max_str=50)) == 50


def test_tracing_disabled_without_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    get_settings.cache_clear()
    assert is_tracing_enabled() is False
    with observation("test-span", input={"question": "hi"}) as span:
        assert isinstance(span, NullObservation)
        span.update(output="ok")
    flush_tracing()  # no-op


def test_observation_noop_does_not_require_langfuse() -> None:
    with observation("agent-run", input="q", metadata={"api_key": "nope"}) as span:
        span.update(output={"done": True})
        span.update_trace(tags=["x"])
