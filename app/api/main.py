"""Minimal FastAPI surface for n8n / automation (Phase 9)."""

from __future__ import annotations

import logging
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Growth Intelligence AI API",
    version="0.9.0",
    description="Report endpoints for n8n automation. Not a full public API.",
)

REPORTS_DIR = Path("reports")


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "growth-intelligence-api"


class RootResponse(BaseModel):
    service: str = "growth-intelligence-api"
    version: str
    docs: str = "/docs"
    health: str = "/health"


@app.get("/", response_model=RootResponse)
def root() -> RootResponse:
    """Say what this is.

    Without this, the bare domain 404s — which reads as a broken deploy when the
    service is fine and simply has no route at `/`.
    """
    return RootResponse(version=app.version)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check endpoint - read-only, no DB access."""
    return HealthResponse()


# Import heavy dependencies only when needed
try:
    logger.info("Attempting to import reports module...")
    from app.db.session import session_scope
    from app.services.reports import build_weekly_report, write_report_markdown
    logger.info("Reports module imported successfully")

    class WeeklyReportResponse(BaseModel):
        title: str
        period_start: date
        period_end: date
        channel: str | None
        markdown: str
        provenance_note: str
        saved_path: str | None = None
        generated_at: datetime

    @app.post("/api/reports/weekly", response_model=WeeklyReportResponse)
    def weekly_report(
        days: int = Query(default=7, ge=1, le=90),
        channel: str | None = Query(default=None),
        include_orchestrator: bool = Query(default=True),
        save: bool = Query(default=True, description="Write markdown under ./reports/"),
        question: str = Query(
            default="What should we do about Premium conversion this week?",
            min_length=3,
        ),
    ) -> WeeklyReportResponse:
        """Generate the weekly growth report for n8n HTTP Request nodes.
        
        Using sync context with session_scope() - this avoids async/psycopg3 issues.
        """
        logger.info(f"Weekly report requested: days={days}, channel={channel}")
        with session_scope() as session:
            report = build_weekly_report(
                session,
                days=days,
                channel=channel,
                include_orchestrator=include_orchestrator,
                question=question,
            )

        saved: str | None = None
        if save:
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            path = REPORTS_DIR / f"weekly_{stamp}.md"
            write_report_markdown(report, path)
            saved = str(path)

        return WeeklyReportResponse(
            title=report.title,
            period_start=report.period_start,
            period_end=report.period_end,
            channel=report.channel,
            markdown=report.markdown,
            provenance_note=report.provenance_note,
            saved_path=saved,
            generated_at=datetime.now(UTC),
        )

    class EditorialMemoResponse(BaseModel):
        title: str
        generated_on: date
        period_start: date
        period_end: date
        markdown: str
        provenance: str
        saved_path: str | None = None
        generated_at: datetime

    @app.post("/api/memo/editorial", response_model=EditorialMemoResponse)
    def editorial_memo(
        save: bool = Query(default=True, description="Write markdown under ./reports/"),
        candidate_limit: int = Query(default=5, ge=1, le=20),
    ) -> EditorialMemoResponse:
        """Compose the weekly French editorial memo over the real catalogue.

        Both post-conditions run before the memo leaves this process. A memo
        carrying a figure the composer never emitted, or funnel vocabulary
        outside the section that disowns it, is a 500 rather than a 200 — it
        would otherwise reach a scheduled delivery looking exactly like a sound
        one, which is the failure mode this whole track exists to prevent.
        """
        from app.services.automation import MEMO_AUTOMATION, record_run
        from app.services.memo import build_editorial_memo, write_memo
        from app.skills.memo_generation import (
            MemoError,
            funnel_vocabulary_leaks,
            undeclared_figures,
        )

        logger.info(f"Editorial memo requested: candidate_limit={candidate_limit}")
        started_at = datetime.now(UTC)

        def _record(**fields) -> None:
            """Bookkeeping in its own transaction, and never fatal on its own."""
            try:
                with session_scope() as session:
                    record_run(
                        session,
                        automation=MEMO_AUTOMATION,
                        started_at=started_at,
                        **fields,
                    )
            except Exception:  # pragma: no cover - must not mask the real outcome
                logger.exception("memo_run_record_failed")

        try:
            with session_scope() as session:
                memo = build_editorial_memo(session, candidate_limit=candidate_limit)
        except MemoError as error:
            _record(ok=False, error=f"catalogue insuffisant : {error}")
            raise HTTPException(status_code=409, detail=str(error)) from error

        undeclared = undeclared_figures(memo)
        leaks = funnel_vocabulary_leaks(memo)
        if undeclared or leaks:
            logger.error(
                "memo_rejected undeclared=%s leaks=%s", undeclared, leaks
            )
            _record(
                ok=False,
                error="post-conditions non satisfaites",
                details={
                    "undeclared_figures": list(undeclared),
                    "funnel_vocabulary_leaks": [
                        {"section": key, "term": term} for key, term in leaks
                    ],
                    "rejected": True,
                },
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Memo failed its post-conditions and was not emitted",
                    "undeclared_figures": list(undeclared),
                    "funnel_vocabulary_leaks": [
                        {"section": key, "term": term} for key, term in leaks
                    ],
                },
            )

        saved: str | None = None
        if save:
            saved = str(write_memo(memo, directory=REPORTS_DIR))
        _record(
            ok=True,
            artifact_path=saved,
            details={"sections": len(memo.sections), "figures": len(memo.figures)},
        )

        return EditorialMemoResponse(
            title=memo.title,
            generated_on=memo.generated_on,
            period_start=memo.period_start,
            period_end=memo.period_end,
            markdown=memo.markdown,
            provenance=memo.provenance,
            saved_path=saved,
            generated_at=datetime.now(UTC),
        )

except ImportError as e:
    logger.warning(f"Could not import reports module: {e}", exc_info=True)
except Exception as e:
    logger.error(f"Error setting up reports endpoint: {e}", exc_info=True)

logger.info("FastAPI app initialized successfully - all handlers are sync (no async)")

