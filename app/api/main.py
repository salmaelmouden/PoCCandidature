"""Minimal FastAPI surface for n8n / automation (Phase 9)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

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
    return HealthResponse()


@app.get("/")
def root():
    return {"message": "API is running"}


# Import heavy dependencies only when needed
try:
    from app.db.session import session_scope
    from app.services.reports import build_weekly_report, write_report_markdown

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
        """Generate the weekly growth report for n8n HTTP Request nodes."""
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
    print(f"Warning: Could not import reports module: {e}")

