"""Automation run history — recording, and judging whether it is still healthy.

The dashboard shows this; it does not compute it. The distinction that matters
here is the same one Phase 14 drew for the catalogue: *when did it last run* and
*when did it last work* are different questions, and a surface that answers only
one of them lies in one direction or the other. Showing the last run alone hides
that it failed after months of success; showing the last success alone hides that
it has been failing ever since.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AutomationRun
from app.db.repositories import AutomationRunRepository

MEMO_AUTOMATION = "editorial_memo"

#: How long a weekly job may go without a success before the page stops calling
#: it healthy. Deliberately more than a week: a Monday job that slips to Tuesday
#: is late, not broken, and an alert that fires on lateness gets ignored.
MEMO_STALE_AFTER = timedelta(days=9)


@dataclass(frozen=True)
class RunSummary:
    """One run, flattened for display. No ORM object reaches a page."""

    finished_at: datetime
    ok: bool
    error: str | None
    artifact_path: str | None
    details: dict[str, Any]
    duration_seconds: float


@dataclass(frozen=True)
class AutomationHealth:
    """What the run history says about one job."""

    automation: str
    last_run: RunSummary | None
    last_success: RunSummary | None
    consecutive_failures: int
    runs: tuple[RunSummary, ...]
    stale_after: timedelta

    @property
    def status(self) -> str:
        """`never` | `ok` | `failing` | `stale`.

        `stale` is separate from `failing` on purpose. A job that errors tells
        you what went wrong; a job that simply stopped being invoked leaves no
        row at all, and that silence is the failure mode a run table exists to
        make visible.
        """
        if self.last_run is None:
            return "never"
        if not self.last_run.ok:
            return "failing"
        if self.last_success is None:
            return "failing"
        age = datetime.now(UTC) - self.last_success.finished_at.astimezone(UTC)
        return "stale" if age > self.stale_after else "ok"

    @property
    def success_rate(self) -> float | None:
        """Over the runs loaded, not over all history. `None` when there are none."""
        if not self.runs:
            return None
        return sum(1 for run in self.runs if run.ok) / len(self.runs)

    @property
    def last_artifact(self) -> str | None:
        """The markdown of the last successful run, when it was kept.

        Read from the run record rather than from `artifact_path`: in production
        this job is a cron container whose filesystem is discarded on exit, so
        the file the path names is gone by the time anyone opens the page. Runs
        written before the markdown was stored return `None` and the page says
        so instead of rendering an empty document.
        """
        if self.last_success is None:
            return None
        markdown = self.last_success.details.get("markdown")
        return markdown if isinstance(markdown, str) and markdown.strip() else None


def _aware(moment: datetime) -> datetime:
    """Guarantee an aware UTC datetime.

    `DateTime(timezone=True)` round-trips the offset on PostgreSQL and drops it
    on SQLite, which the tests run against. Everything stored here is written in
    UTC, so a naive value read back is UTC that lost its label — attaching it is
    a correction, not an assumption. Without this, arithmetic on these
    timestamps raises on one backend and works on the other, which is the worst
    of the two possible outcomes.
    """
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def _summarise(row: AutomationRun) -> RunSummary:
    finished, started = _aware(row.finished_at), _aware(row.started_at)
    return RunSummary(
        finished_at=finished,
        ok=row.ok,
        error=row.error,
        artifact_path=row.artifact_path,
        details=dict(row.details or {}),
        duration_seconds=max(0.0, (finished - started).total_seconds()),
    )


def record_run(
    session: Session,
    *,
    automation: str,
    started_at: datetime,
    ok: bool,
    error: str | None = None,
    artifact_path: str | None = None,
    details: dict[str, Any] | None = None,
) -> RunSummary:
    """Write one run. Called on success *and* on failure — that is the point."""
    row = AutomationRunRepository(session).record(
        automation=automation,
        started_at=started_at,
        ok=ok,
        error=error,
        artifact_path=artifact_path,
        details=details,
    )
    return _summarise(row)


def get_automation_health(
    session: Session,
    *,
    automation: str = MEMO_AUTOMATION,
    limit: int = 10,
    stale_after: timedelta = MEMO_STALE_AFTER,
) -> AutomationHealth:
    """Read the run history and decide what it means. All logic lives here."""
    repo = AutomationRunRepository(session)
    runs = repo.recent(automation, limit=limit)
    last_success = repo.latest(automation, only_successful=True)
    return AutomationHealth(
        automation=automation,
        last_run=_summarise(runs[0]) if runs else None,
        last_success=_summarise(last_success) if last_success else None,
        consecutive_failures=repo.consecutive_failures(automation),
        runs=tuple(_summarise(row) for row in runs),
        stale_after=stale_after,
    )
