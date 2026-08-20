"""Tests for growth_data_analyst_agent."""

from __future__ import annotations

from datetime import date

from app.agents.growth_data_analyst_agent import AnalystQuestion, GrowthDataAnalystAgent
from app.agents.growth_data_analyst_agent.routing import AnalystIntent, classify_intent
from app.agents.growth_data_analyst_agent.schemas import SemanticLabel
from app.db.repositories import AcquisitionRepository


def _seed_premium_drop(session) -> None:
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


def test_classify_intent() -> None:
    assert classify_intent("Why did Premium conversion decrease?") == AnalystIntent.PREMIUM
    assert classify_intent("Where is the funnel bottleneck?") == AnalystIntent.BOTTLENECK
    assert classify_intent("Which channel performs worst?") == AnalystIntent.CHANNEL
    assert classify_intent("Which topics have high reach but low conversion?") == AnalystIntent.CONTENT
    assert classify_intent("Any traffic anomalies?") == AnalystIntent.ANOMALY
    assert classify_intent("What changed vs last period?") == AnalystIntent.PERIOD_CHANGE


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


def test_different_questions_use_different_tools_and_answers(session) -> None:
    _seed_premium_drop(session)
    agent = GrowthDataAnalystAgent()
    as_of = date(2026, 8, 20)
    bottleneck = agent.run(
        session,
        AnalystQuestion(question="Where is the funnel bottleneck?", days=7, as_of=as_of),
    )
    content = agent.run(
        session,
        AnalystQuestion(
            question="Which topics have high reach but low conversion?",
            days=7,
            as_of=as_of,
        ),
    )
    anomaly = agent.run(
        session,
        AnalystQuestion(question="Any traffic anomalies this period?", days=7, as_of=as_of),
    )

    assert {t.tool for t in bottleneck.tool_calls} == {"get_overview", "get_funnel_compare"}
    assert "get_content_gaps" in {t.tool for t in content.tool_calls}
    assert "get_funnel_compare" not in {t.tool for t in content.tool_calls}
    assert {t.tool for t in anomaly.tool_calls} == {"get_overview"}

    assert bottleneck.primary_driver != content.primary_driver
    assert "bottleneck" in (bottleneck.primary_driver or "")
    assert "content gap" in (content.primary_driver or "") or "topic=" in (
        content.primary_driver or ""
    )
    assert anomaly.claims[-1].label == SemanticLabel.INTERPRETATION
    assert "anomal" in anomaly.claims[-1].text.lower() or "No traffic" in anomaly.claims[-1].text
