"""Langfuse-backed observability with safe no-op when disabled."""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

_SECRET_KEY_RE = re.compile(
    r"(password|secret|api[_-]?key|token|authorization|credential)",
    re.IGNORECASE,
)


class NullObservation:
    """No-op span used when Langfuse is disabled or unavailable."""

    def update(self, **kwargs: Any) -> None:
        return None

    def update_trace(self, **kwargs: Any) -> None:
        return None


def is_tracing_enabled() -> bool:
    """True when Langfuse keys are configured and the SDK imports cleanly."""
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return False
    try:
        import langfuse  # noqa: F401
    except ImportError:
        return False
    return True


def _ensure_base_url_env() -> None:
    settings = get_settings()
    host = (settings.langfuse_host or "").strip()
    if host and not os.environ.get("LANGFUSE_BASE_URL"):
        os.environ["LANGFUSE_BASE_URL"] = host
    if settings.langfuse_public_key and not os.environ.get("LANGFUSE_PUBLIC_KEY"):
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
    if settings.langfuse_secret_key and not os.environ.get("LANGFUSE_SECRET_KEY"):
        os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key


def get_langfuse_client():
    """Return Langfuse client or None."""
    if not is_tracing_enabled():
        return None
    _ensure_base_url_env()
    from langfuse import get_client

    return get_client()


def sanitize(value: Any, *, max_str: int = 500) -> Any:
    """Drop secret-like keys and truncate long strings for safe span metadata."""
    if value is None:
        return None
    if isinstance(value, str):
        return value[:max_str]
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if _SECRET_KEY_RE.search(str(key)):
                out[str(key)] = "[redacted]"
                continue
            out[str(key)] = sanitize(item, max_str=max_str)
        return out
    if isinstance(value, (list, tuple)):
        return [sanitize(v, max_str=max_str) for v in value[:50]]
    return str(value)[:max_str]


@contextmanager
def observation(
    name: str,
    *,
    as_type: str = "span",
    input: Any = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Iterator[Any]:
    """
    Create a Langfuse observation, or a NullObservation when tracing is off.

    Always set explicit `input` (e.g. user question) — never dump full kwargs.
    """
    client = get_langfuse_client()
    if client is None:
        yield NullObservation()
        return

    try:
        with client.start_as_current_observation(as_type=as_type, name=name) as span:
            payload: dict[str, Any] = {}
            if input is not None:
                payload["input"] = sanitize(input)
            if metadata:
                payload["metadata"] = sanitize(metadata)
            if tags:
                # tags may be supported via update_trace on root; set metadata mirror too
                payload.setdefault("metadata", {})
                if isinstance(payload["metadata"], dict):
                    payload["metadata"]["tags"] = tags
            if payload:
                span.update(**payload)
            if tags:
                try:
                    span.update_trace(tags=tags)
                except Exception:  # noqa: BLE001 — SDK version variance
                    pass
            yield span
    except Exception as exc:  # noqa: BLE001 — never break the app
        logger.warning("Langfuse observation failed (%s); continuing without trace", exc)
        yield NullObservation()


def flush_tracing() -> None:
    """Flush pending events (short-lived processes / Streamlit runs)."""
    client = get_langfuse_client()
    if client is None:
        return
    try:
        client.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Langfuse flush failed: %s", exc)
