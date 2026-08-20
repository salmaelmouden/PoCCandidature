"""API smoke tests (no Postgres required for /health)."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.main import app
from app.skills.report_generation import WeeklyGrowthReport, ReportSection

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_weekly_report_endpoint_uses_service() -> None:
    fake = WeeklyGrowthReport(
        title="Weekly Growth Report",
        period_start=date(2026, 8, 14),
        period_end=date(2026, 8, 20),
        channel=None,
        sections=[ReportSection(title="KPIs", body="ok", bullets=["x"])],
        markdown="# Weekly Growth Report\n",
        provenance_note="synthetic",
    )
    with (
        patch("app.api.main.session_scope") as scope,
        patch("app.api.main.build_weekly_report", return_value=fake),
        patch("app.api.main.write_report_markdown") as write_md,
    ):
        scope.return_value.__enter__.return_value = object()
        scope.return_value.__exit__.return_value = None
        write_md.side_effect = lambda report, path: path
        resp = client.post("/api/reports/weekly?days=7&save=true")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Weekly Growth Report"
    assert "markdown" in body
    assert body["saved_path"]
