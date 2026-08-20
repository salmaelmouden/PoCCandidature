"""Tests for growth_data_analyst_agent."""

from __future__ import annotations

from datetime import date

from app.agents.growth_data_analyst_agent import AnalystQuestion, GrowthDataAnalystAgent
from app.agents.growth_data_analyst_agent.schemas import SemanticLabel
from app.db.repositories import AcquisitionRepository


def _seed_premium_drop(session) -> None:
    repo = AcquisitionRepository(session)
    # as_of=2026-08-20, days=7 → current 2026-08-14..20 ; previous 2026-08-07..13
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


def test_analyst_answers_premium_drop_with_facts(session) -> None:
    _seed_premium_drop(session)
    agent = GrowthDataAnalystAgent()
    report = agent.run(
        session,
        AnalystQuestion(
            question="Why did Premium conversion decrease?",
            days=7,
            as_of=date(2026, 8, 20),
        ),
    )
    assert report.insufficient_evidence is False
    assert any(c.label == SemanticLabel.FACT for c in report.claims)
    assert any(c.label == SemanticLabel.INTERPRETATION for c in report.claims)
    assert all(c.label != SemanticLabel.RECOMMENDATION for c in report.claims)
    tools = {t.tool for t in report.tool_calls if t.ok}
    assert "get_funnel_compare" in tools
    assert "get_acquisition_by_channel" in tools
    assert report.primary_driver is not None
    assert "YouTube" in (report.primary_driver or "")


def test_analyst_default_question(session) -> None:
    _seed_premium_drop(session)
    report = GrowthDataAnalystAgent().run(
        session, AnalystQuestion(question="What changed?", days=7, as_of=date(2026, 8, 20))
    )
    assert report.question == "What changed?"
    assert report.tool_calls
