"""
Phase 16 / W2 — the weekly report service must run the data-quality gate itself.

The guardrail lives in the agent's output, but the *decision to run it* lives here.
ADR-009 puts the `validate_funnel` call in the application service rather than in an
agent precisely so that a report built with no agent in the loop still carries the
warning — otherwise `include_orchestrator=False` would quietly produce the same
untrustworthy report that started all of this.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.db.repositories import AcquisitionRepository
from app.services.reports import build_weekly_report

AS_OF = date(2026, 8, 20)


def _seed(session, *, premium: int) -> None:
    repo = AcquisitionRepository(session)
    for day, channel in ((date(2026, 8, 18), "YouTube"), (date(2026, 8, 16), "Paid")):
        repo.upsert(
            metric_date=day,
            channel=channel,
            topic="Crypto",
            video_id=None,
            views=42_000,
            visits=9_000,
            signups=620,
            activated_users=283,
            premium_users=premium,
            is_synthetic=True,
            dataset_label="synthetic_v1",
        )
    session.commit()


def _section(report, title: str):
    return next((s for s in report.sections if s.title == title), None)


@pytest.mark.parametrize("include_orchestrator", [True, False])
def test_degenerate_funnel_is_flagged_with_or_without_an_agent(
    session, include_orchestrator: bool
) -> None:
    """The caveat cannot depend on whether an agent happened to be invoked."""
    _seed(session, premium=0)

    report = build_weekly_report(
        session, days=7, as_of=AS_OF, include_orchestrator=include_orchestrator
    )

    quality = _section(report, "⚠ Data quality")
    assert quality is not None, "no data-quality section on a funnel with an empty terminal stage"
    assert "premium_users" in quality.body
    assert quality.bullets, "warning section rendered without the warning text"


def test_the_caveat_leads_the_report(session) -> None:
    """
    Reading order is belief order. A caveat printed under the numbers arrives after
    the reader has already acted on them.
    """
    _seed(session, premium=0)

    report = build_weekly_report(session, days=7, as_of=AS_OF, include_orchestrator=False)

    assert report.sections[0].title == "⚠ Data quality"
    assert report.markdown.index("Data quality") < report.markdown.index("## KPIs")


def test_healthy_funnel_carries_no_caveat(session) -> None:
    """The gate stays invisible when there is nothing to distrust."""
    _seed(session, premium=31)

    report = build_weekly_report(session, days=7, as_of=AS_OF, include_orchestrator=False)

    assert _section(report, "⚠ Data quality") is None
    assert report.sections[0].title == "KPIs"


def test_no_urgent_recommendation_survives_into_the_report(session) -> None:
    """
    End of the chain: service → orchestrator → strategist → post-condition → markdown.
    The string that must never reappear is the one that shipped weekly for a rounding
    artefact.
    """
    _seed(session, premium=0)

    report = build_weekly_report(session, days=7, as_of=AS_OF, include_orchestrator=True)

    assert "[P0] Fix Premium leak" not in report.markdown
    assert "[P1] Fix Premium leak" not in report.markdown
