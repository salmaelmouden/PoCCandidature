"""Tests for report_generation."""

from __future__ import annotations

from datetime import date

from app.skills.report_generation import generate_weekly_report


def test_weekly_report_markdown_contains_kpis_and_provenance() -> None:
    report = generate_weekly_report(
        {
            "period_start": date(2026, 8, 14),
            "period_end": date(2026, 8, 20),
            "current_counts": {
                "views": 10000,
                "visits": 2000,
                "signups": 400,
                "activated_users": 220,
                "premium_users": 40,
            },
            "previous_counts": {
                "views": 9000,
                "visits": 1800,
                "signups": 380,
                "activated_users": 210,
                "premium_users": 50,
            },
            "relative_deltas": {"views": 0.11, "premium_users": -0.2},
            "bottleneck_from": "activated_users",
            "bottleneck_to": "premium_users",
            "bottleneck_dropoff_rate": 0.82,
            "anomaly_count": 1,
            "top_channels": [
                {"channel": "YouTube", "signups": 200, "premium_rate": 0.04},
                {"channel": "LinkedIn", "signups": 150, "premium_rate": 0.12},
            ],
            "content_gaps": [{"topic": "Crypto", "reach": 5000, "premium_rate": 0.02}],
            "orchestrator_summary": "Driver: YouTube premium_rate lag.",
            "recommendations": ["[P0] Fix Premium leak on weakest channel"],
            "dataset_labels": ["synthetic_v1"],
            "has_synthetic": True,
        }
    )
    assert "Weekly Growth Report" in report.markdown
    assert "YouTube" in report.markdown
    assert "synthetic" in report.provenance_note.lower()
    assert any(s.title == "KPIs" for s in report.sections)
    assert "Premium leak" in report.markdown
