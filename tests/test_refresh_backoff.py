"""Backoff that survives the process, so cron can pace itself.

A long-lived loop keeps its failure counter in memory. Cron cannot: every run is
a fresh container. These tests pin the reconstruction from run history, because
getting it wrong is silent — the refresher would retry a dead key at full cadence
and burn the daily YouTube quota on calls that cannot succeed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.db.repositories import IngestRunRepository
from scripts.refresh_catalogue import (
    _suppressed_by_backoff,
    backoff_delay,
    cycle_ok,
    redact_credentials,
)


def _run(session, *, ok: bool, finished_at: datetime) -> None:
    """Record a cycle with an explicit finish time.

    SQLite's CURRENT_TIMESTAMP only has second granularity, so rows written in
    one test would tie and the ordering under test would be arbitrary.
    """
    repo = IngestRunRepository(session)
    row = repo.record(
        channel_id="UCTEST",
        started_at=finished_at - timedelta(seconds=8),
        videos_upserted=0,
        metrics_upserted=0,
        classified=0,
        ok=ok,
        error=None if ok else "boom",
    )
    row.finished_at = finished_at
    session.flush()


NOW = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)


# ------------------------------------------ credentials must not reach the page


def test_youtube_key_is_stripped_from_an_httpx_error() -> None:
    """The realistic leak: httpx puts the whole request URL in its message, and
    ingest_runs.error is rendered verbatim on a public, unauthenticated page."""
    raw = (
        "ingest: Client error '403 Forbidden' for url "
        "'https://www.googleapis.com/youtube/v3/search?part=id"
        "&channelId=UCRCC&key=AIzaSyD-REAL-LOOKING-SECRET-VALUE'"
    )
    cleaned = redact_credentials(raw)
    assert "AIzaSyD-REAL-LOOKING-SECRET-VALUE" not in cleaned
    assert "key=[redacted]" in cleaned
    # The diagnostic value has to survive the redaction, or nobody will use it.
    assert "403 Forbidden" in cleaned
    assert "channelId=UCRCC" in cleaned


def test_other_credential_parameter_names_are_covered() -> None:
    for param in ("api_key", "apikey", "access_token", "token", "password"):
        cleaned = redact_credentials(f"boom https://x.test/a?{param}=SUPERSECRET&b=1")
        assert "SUPERSECRET" not in cleaned, param
        assert "b=1" in cleaned, param


def test_redaction_is_case_insensitive() -> None:
    assert "SECRET" not in redact_credentials("https://x.test/a?KEY=SECRET")


def test_ordinary_errors_pass_through_untouched() -> None:
    assert redact_credentials("classify: rate limited") == "classify: rate limited"


def test_none_and_empty_survive() -> None:
    assert redact_credentials(None) is None
    assert redact_credentials("") == ""


# -------------------------------------------------------- is a cycle healthy?


def test_nothing_pending_is_a_healthy_cycle() -> None:
    """No new videos to classify is the steady state, not a failure."""
    assert cycle_ok(classified=0, failed=0) is True


def test_everything_classified_is_healthy() -> None:
    assert cycle_ok(classified=353, failed=0) is True


def test_partial_progress_is_healthy() -> None:
    """Some batches landing means the classifier works; the rest follow next cycle."""
    assert cycle_ok(classified=80, failed=273) is True


def test_every_batch_failing_is_not_healthy() -> None:
    """The case that was silent: the skill absorbs batch failures and returns
    normally, so this used to record ok=True and disengage the backoff."""
    assert cycle_ok(classified=0, failed=273) is False


# ---------------------------------------------------------------- delay curve


def test_no_failures_uses_the_plain_interval() -> None:
    assert backoff_delay(600, 0) == 600


def test_delay_doubles_per_failure() -> None:
    assert backoff_delay(600, 1) == 1200
    assert backoff_delay(600, 2) == 2400
    assert backoff_delay(600, 3) == 4800


def test_delay_is_capped_at_eight_times() -> None:
    """Unbounded growth would park a recovered service for days."""
    assert backoff_delay(600, 4) == 4800
    assert backoff_delay(600, 50) == 4800


# ------------------------------------------------- counting from run history


def test_no_runs_means_no_failures(session) -> None:
    assert IngestRunRepository(session).consecutive_failures() == 0


def test_successful_runs_count_as_zero(session) -> None:
    _run(session, ok=True, finished_at=NOW - timedelta(minutes=20))
    _run(session, ok=True, finished_at=NOW - timedelta(minutes=10))
    assert IngestRunRepository(session).consecutive_failures() == 0


def test_counts_only_failures_since_the_last_success(session) -> None:
    _run(session, ok=False, finished_at=NOW - timedelta(minutes=50))
    _run(session, ok=True, finished_at=NOW - timedelta(minutes=40))
    _run(session, ok=False, finished_at=NOW - timedelta(minutes=20))
    _run(session, ok=False, finished_at=NOW - timedelta(minutes=10))
    assert IngestRunRepository(session).consecutive_failures() == 2


def test_counts_every_failure_when_nothing_ever_succeeded(session) -> None:
    for minutes in (30, 20, 10):
        _run(session, ok=False, finished_at=NOW - timedelta(minutes=minutes))
    assert IngestRunRepository(session).consecutive_failures() == 3


# ------------------------------------------------------------- the cron gate


def _gate(session, interval: int) -> bool:
    """Run the gate against this session, as the cron entrypoint would."""
    from contextlib import contextmanager

    @contextmanager
    def fake_scope():
        yield session

    with patch("scripts.refresh_catalogue.session_scope", fake_scope):
        return _suppressed_by_backoff(interval)


def test_healthy_history_does_not_suppress(session) -> None:
    _run(session, ok=True, finished_at=datetime.now(timezone.utc) - timedelta(minutes=30))
    assert _gate(session, 600) is False


def test_recent_failure_suppresses_the_run(session) -> None:
    """One failure widens the window to 20 min; only 2 have passed."""
    _run(
        session,
        ok=False,
        finished_at=datetime.now(timezone.utc) - timedelta(minutes=2),
    )
    assert _gate(session, 600) is True


def test_run_proceeds_once_the_widened_window_has_elapsed(session) -> None:
    _run(
        session,
        ok=False,
        finished_at=datetime.now(timezone.utc) - timedelta(minutes=25),
    )
    assert _gate(session, 600) is False


def test_empty_history_never_suppresses(session) -> None:
    """A first-ever run must not be skipped — that would never populate."""
    assert _gate(session, 600) is False


def test_unreadable_database_does_not_block_the_refresh(session) -> None:
    """Pacing is an optimisation; it must never be the reason nothing refreshes."""
    with patch(
        "scripts.refresh_catalogue.session_scope", side_effect=RuntimeError("no db")
    ):
        assert _suppressed_by_backoff(600) is False
