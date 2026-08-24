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
from scripts.refresh_catalogue import _suppressed_by_backoff, backoff_delay


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
