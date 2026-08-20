"""Tests for growth_strategist_agent."""

from __future__ import annotations

from datetime import date

from app.agents.growth_data_analyst_agent.schemas import (
    AnalystReport,
    EvidenceClaim,
    SemanticLabel,
)
from app.agents.growth_strategist_agent import GrowthStrategistAgent, StrategistQuestion
from app.db.repositories import AcquisitionRepository


def _seed(session) -> None:
    repo = AcquisitionRepository(session)
    repo.upsert(
        metric_date=date(2026, 8, 18),
        channel="YouTube",
        topic="Crypto",
        video_id=None,
        views=5000,
        visits=1000,
        signups=100,
        activated_users=80,
        premium_users=4,
    )
    repo.upsert(
        metric_date=date(2026, 8, 18),
        channel="LinkedIn",
        topic="ETFs",
        video_id=None,
        views=800,
        visits=300,
        signups=90,
        activated_users=70,
        premium_users=25,
    )
    repo.upsert(
        metric_date=date(2026, 8, 10),
        channel="YouTube",
        topic="Crypto",
        video_id=None,
        views=4000,
        visits=900,
        signups=120,
        activated_users=90,
        premium_users=18,
    )
    repo.upsert(
        metric_date=date(2026, 8, 10),
        channel="LinkedIn",
        topic="ETFs",
        video_id=None,
        views=700,
        visits=280,
        signups=85,
        activated_users=65,
        premium_users=22,
    )
    session.commit()


def test_strategist_emits_recommendations_from_live_analyst(session) -> None:
    _seed(session)
    report = GrowthStrategistAgent().run(
        session,
        StrategistQuestion(
            question="What should we do about the Premium conversion drop?",
            days=7,
            as_of=date(2026, 8, 20),
        ),
    )
    assert report.insufficient_evidence is False
    assert report.recommendations
    assert any(c.label == SemanticLabel.RECOMMENDATION for c in report.claims)
    assert all(c.label != SemanticLabel.RECOMMENDATION or c.text for c in report.claims)
    assert report.tool_calls and report.tool_calls[0].tool == "get_analyst_report"


def test_strategist_reuses_provided_analyst_report(session) -> None:
    analyst = AnalystReport(
        question="Why?",
        period_start=date(2026, 8, 14),
        period_end=date(2026, 8, 20),
        channel=None,
        primary_driver="YouTube premium_rate lag",
        claims=[
            EvidenceClaim(
                label=SemanticLabel.FACT,
                text="YouTube premium_rate is weakest.",
                source_tool="get_acquisition_by_channel",
                numbers={"premium_rate": 0.04},
            ),
            EvidenceClaim(
                label=SemanticLabel.INTERPRETATION,
                text="YouTube is the primary Premium leak.",
                source_tool=None,
            ),
        ],
        tool_calls=[],
        insufficient_evidence=False,
    )
    report = GrowthStrategistAgent().run(
        session,
        StrategistQuestion(
            question="What should we do?",
            days=7,
            as_of=date(2026, 8, 20),
            analyst_report=analyst,
        ),
    )
    assert report.tool_calls[0].summary.startswith("Used caller-provided")
    assert any("YouTube" in r.action or "channel" in r.action.lower() for r in report.recommendations)
