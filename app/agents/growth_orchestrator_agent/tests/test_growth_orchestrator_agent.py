"""Tests for growth_orchestrator_agent."""

from __future__ import annotations

from datetime import date

from app.agents.growth_data_analyst_agent.schemas import SemanticLabel
from app.agents.growth_orchestrator_agent import GrowthOrchestratorAgent, OrchestratorQuestion
from app.agents.growth_orchestrator_agent.routing import classify_route
from app.agents.growth_orchestrator_agent.schemas import RouteKind
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


def test_classify_route() -> None:
    assert classify_route("Why did Premium conversion decrease?") == RouteKind.ANALYST_ONLY
    assert classify_route("Where is the funnel bottleneck?") == RouteKind.ANALYST_ONLY
    assert (
        classify_route("What should we do about Premium?")
        == RouteKind.ANALYST_THEN_STRATEGIST
    )
    assert classify_route("Recommend next steps") == RouteKind.ANALYST_THEN_STRATEGIST
    assert classify_route("Did the YouTube CTA experiment work?") == RouteKind.EXPERIMENT
    assert classify_route("How should we test the Premium drop?") == RouteKind.EXPERIMENT


def test_orchestrator_analyst_only_skips_strategist(session) -> None:
    _seed(session)
    resp = GrowthOrchestratorAgent().run(
        session,
        OrchestratorQuestion(
            question="Why did Premium conversion decrease?",
            days=7,
            as_of=date(2026, 8, 20),
        ),
    )
    assert resp.route == RouteKind.ANALYST_ONLY
    assert resp.agents_called == ["growth_data_analyst_agent"]
    assert resp.strategy_report is None
    assert resp.analyst_report is not None
    assert "Primary driver" in resp.summary or "driver" in resp.summary.lower()


def test_orchestrator_runs_strategist_for_action_questions(session) -> None:
    _seed(session)
    resp = GrowthOrchestratorAgent().run(
        session,
        OrchestratorQuestion(
            question="What should we do about the Premium conversion drop?",
            days=7,
            as_of=date(2026, 8, 20),
        ),
    )
    assert resp.route == RouteKind.ANALYST_THEN_STRATEGIST
    assert "growth_strategist_agent" in resp.agents_called
    assert resp.strategy_report is not None
    assert resp.strategy_report.recommendations
    assert any(c.label == SemanticLabel.RECOMMENDATION for c in resp.claims)


def test_orchestrator_routes_experiment_questions(session) -> None:
    _seed(session)
    from decimal import Decimal

    from app.db.repositories import ExperimentRepository

    exp_repo = ExperimentRepository(session)
    exp = exp_repo.upsert_experiment(
        experiment_key="syn_exp_youtube_cta",
        name="[SYNTHETIC] YouTube CTA",
        hypothesis="CTA helps",
        status="completed",
        primary_metric="activated_to_premium_rate",
        is_synthetic=True,
        dataset_label="synthetic_v1",
    )
    exp_repo.upsert_result(
        experiment_id=exp.id,
        variant="control",
        users=4200,
        conversions=378,
        conversion_rate=Decimal("0.090000"),
    )
    exp_repo.upsert_result(
        experiment_id=exp.id,
        variant="treatment",
        users=4180,
        conversions=443,
        conversion_rate=Decimal("0.105980"),
    )
    session.commit()

    resp = GrowthOrchestratorAgent().run(
        session,
        OrchestratorQuestion(question="Did the YouTube CTA experiment work?", days=7),
    )
    assert resp.route == RouteKind.EXPERIMENT
    assert resp.agents_called == ["growth_experiment_analyst_agent"]
    assert resp.experiment_report is not None
    assert resp.strategy_report is None
