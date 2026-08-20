"""Tests for growth_experiment_analyst_agent."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.agents.growth_experiment_analyst_agent import (
    ExperimentAnalystQuestion,
    ExperimentMode,
    GrowthExperimentAnalystAgent,
    classify_experiment_mode,
)
from app.agents.growth_data_analyst_agent.schemas import SemanticLabel
from app.db.repositories import AcquisitionRepository, ExperimentRepository
from app.skills.experiment_analysis import DecisionHint


def _seed(session) -> None:
    exp_repo = ExperimentRepository(session)
    exp = exp_repo.upsert_experiment(
        experiment_key="syn_exp_youtube_cta",
        name="[SYNTHETIC] YouTube contextual Premium CTA",
        hypothesis="CTA improves activated→premium",
        status="completed",
        primary_metric="activated_to_premium_rate",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 8, 1),
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
    # Minimal acquisition so propose mode analyst can run
    acq = AcquisitionRepository(session)
    acq.upsert(
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
    acq.upsert(
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
    session.commit()


def test_classify_mode() -> None:
    assert classify_experiment_mode("Did the CTA experiment work?") == ExperimentMode.ANALYZE
    assert (
        classify_experiment_mode("How should we test the Premium drop?")
        == ExperimentMode.PROPOSE
    )


def test_analyze_youtube_cta(session) -> None:
    _seed(session)
    report = GrowthExperimentAnalystAgent().run(
        session,
        ExperimentAnalystQuestion(
            question="Did the YouTube CTA experiment work?",
            experiment_key="syn_exp_youtube_cta",
        ),
    )
    assert report.mode == ExperimentMode.ANALYZE
    assert report.decision_hint == DecisionHint.SHIP_TREATMENT
    assert any(c.label == SemanticLabel.FACT for c in report.claims)
    assert any(c.label == SemanticLabel.RECOMMENDATION for c in report.claims)
    assert report.insufficient_evidence is False


def test_propose_design(session) -> None:
    _seed(session)
    report = GrowthExperimentAnalystAgent().run(
        session,
        ExperimentAnalystQuestion(
            question="How should we test the Premium conversion drop?",
            days=7,
            as_of=date(2026, 8, 20),
        ),
    )
    assert report.mode == ExperimentMode.PROPOSE
    assert report.design is not None
    assert report.design.primary_metric
    assert any(c.label == SemanticLabel.RECOMMENDATION for c in report.claims)
