"""Minimal FastAPI surface for n8n / automation (Phase 9)."""

from __future__ import annotations

import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

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


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check endpoint - read-only, no DB access."""
    return HealthResponse()


@app.get("/")
def root():
    """Simple test endpoint with no database access."""
    return {"message": "API is running", "version": "0.9.0"}


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
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
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
            generated_at=datetime.now(timezone.utc),
        )

except ImportError as e:
    logger.warning(f"Could not import reports module: {e}", exc_info=True)
except Exception as e:
    logger.error(f"Error setting up reports endpoint: {e}", exc_info=True)

logger.info("FastAPI app initialized successfully - all handlers are sync (no async)")

