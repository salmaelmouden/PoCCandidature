"""Tests for the automation run history.

The property under test is not "runs are stored". It is that the history can
tell apart the three ways a scheduled job stops being trustworthy: it errored,
it silently stopped being invoked, or it never ran at all. A surface that
collapses those into "no memo today" is the thing this table exists to replace.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.db.models import Base
from app.services.automation import (
    MEMO_AUTOMATION,
    get_automation_health,
    record_run,
)


@pytest.fixture
def session(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(f"sqlite:///{tmp_path/'automation.db'}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as opened:
        yield opened


def add(session, *, ok: bool, ago: timedelta, error: str | None = None, **fields):
    finished = datetime.now(UTC) - ago
    summary = record_run(
        session,
        automation=MEMO_AUTOMATION,
        started_at=finished - timedelta(seconds=1),
        ok=ok,
        error=error,
        **fields,
    )
    # `finished_at` defaults to now() server-side; rewrite it so a test can place
    # a run in the past without waiting for time to pass.
    from sqlalchemy import select

    from app.db.models import AutomationRun

    row = session.scalar(
        select(AutomationRun).order_by(AutomationRun.finished_at.desc()).limit(1)
    )
    row.finished_at = finished
    session.flush()
    return summary


# ---- the three failure modes ------------------------------------------------


def test_never_run_is_its_own_state(session):
    health = get_automation_health(session)

    assert health.status == "never"
    assert health.last_run is None
    assert health.success_rate is None


def test_a_failing_run_is_recorded_not_omitted(session):
    add(session, ok=False, ago=timedelta(hours=1), error="post-conditions non satisfaites")
    health = get_automation_health(session)

    assert health.status == "failing"
    assert health.last_run is not None and health.last_run.ok is False
    assert "post-conditions" in (health.last_run.error or "")


def test_silence_after_a_success_reads_as_stale_not_healthy(session):
    """The failure mode with no error message: nobody invoked the job."""
    add(session, ok=True, ago=timedelta(days=30))
    health = get_automation_health(session)

    assert health.status == "stale"
    assert health.consecutive_failures == 0


def test_recent_success_is_healthy(session):
    add(session, ok=True, ago=timedelta(days=1))

    assert get_automation_health(session).status == "ok"


# ---- last run vs last success -----------------------------------------------


def test_last_run_and_last_success_are_reported_separately(session):
    add(session, ok=True, ago=timedelta(days=8))
    add(session, ok=False, ago=timedelta(days=1), error="boom")
    health = get_automation_health(session)

    assert health.last_run is not None and health.last_run.ok is False
    assert health.last_success is not None and health.last_success.ok is True
    assert health.last_success.finished_at < health.last_run.finished_at
    assert health.status == "failing"


def test_consecutive_failures_counts_only_since_the_last_success(session):
    add(session, ok=False, ago=timedelta(days=20))
    add(session, ok=True, ago=timedelta(days=10))
    add(session, ok=False, ago=timedelta(days=2))
    add(session, ok=False, ago=timedelta(days=1))

    assert get_automation_health(session).consecutive_failures == 2


def test_success_rate_is_over_the_loaded_window(session):
    add(session, ok=True, ago=timedelta(days=4))
    add(session, ok=False, ago=timedelta(days=3))
    add(session, ok=True, ago=timedelta(days=2))
    add(session, ok=True, ago=timedelta(days=1))
    health = get_automation_health(session)

    assert health.success_rate == pytest.approx(0.75)
    assert len(health.runs) == 4


# ---- what a run carries -----------------------------------------------------


def test_a_successful_run_keeps_where_the_artifact_landed(session):
    add(
        session,
        ok=True,
        ago=timedelta(minutes=5),
        artifact_path="reports/memo_editorial_20260825T124513Z.md",
        details={"sections": 6, "figures": 114},
    )
    run = get_automation_health(session).last_run

    assert run is not None
    assert run.artifact_path.endswith(".md")
    assert run.details["sections"] == 6


def test_runs_of_other_automations_are_not_mixed_in(session):
    add(session, ok=True, ago=timedelta(hours=2))
    record_run(
        session,
        automation="some_other_job",
        started_at=datetime.now(UTC),
        ok=False,
        error="unrelated",
    )
    health = get_automation_health(session)

    assert len(health.runs) == 1
    assert health.status == "ok"


def test_runs_are_ordered_newest_first(session):
    add(session, ok=True, ago=timedelta(days=3))
    add(session, ok=False, ago=timedelta(days=1), error="recent")
    runs = get_automation_health(session).runs

    assert runs[0].finished_at > runs[1].finished_at
