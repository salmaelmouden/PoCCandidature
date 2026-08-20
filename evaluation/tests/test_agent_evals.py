"""Runnable agent evaluation suite (Phase 10)."""

from __future__ import annotations

from app.agents.growth_data_analyst_agent import AnalystQuestion, GrowthDataAnalystAgent
from app.agents.growth_data_analyst_agent.schemas import SemanticLabel
from app.agents.growth_experiment_analyst_agent import (
    ExperimentAnalystQuestion,
    GrowthExperimentAnalystAgent,
)
from app.agents.growth_orchestrator_agent import GrowthOrchestratorAgent, OrchestratorQuestion
from app.agents.growth_orchestrator_agent.schemas import RouteKind
from app.agents.growth_strategist_agent import GrowthStrategistAgent, StrategistQuestion
from app.skills.experiment_analysis import DecisionHint
from evaluation.datasets.fixtures import (
    EVAL_AS_OF,
    EVAL_DAYS,
    seed_premium_drop_fixture,
    seed_youtube_cta_experiment,
)
from evaluation.evaluators import (
    EvalResult,
    score_hallucination_text,
    score_has_fact_claims,
    score_no_recommendation_from_analyst,
    score_primary_driver_mentions,
    score_recommendations_grounded,
    score_tool_selection,
)


def _assert_passed(result: EvalResult) -> None:
    failed = [s for s in result.scores if not s.passed]
    assert result.passed, "; ".join(f"{s.name}: {s.detail}" for s in failed)


def test_eval_analyst_premium_conversion_drop(session) -> None:
    seed_premium_drop_fixture(session)
    report = GrowthDataAnalystAgent().run(
        session,
        AnalystQuestion(
            question="Why did Premium conversion decrease?",
            days=EVAL_DAYS,
            as_of=EVAL_AS_OF,
        ),
    )
    tools = {t.tool for t in report.tool_calls if t.ok}
    result = EvalResult(case_id="eval_analyst_premium_conversion_drop")
    result.scores.append(
        score_tool_selection(
            tools,
            required={"get_funnel_compare", "get_acquisition_by_channel"},
        )
    )
    result.scores.append(score_has_fact_claims(report.claims))
    result.scores.append(score_no_recommendation_from_analyst(report.claims))
    result.scores.append(score_primary_driver_mentions(report.primary_driver, ["YouTube"]))
    result.scores.append(
        score_hallucination_text(report.primary_driver, *(c.text for c in report.claims))
    )
    _assert_passed(result)


def test_eval_orchestrator_routing(session) -> None:
    seed_premium_drop_fixture(session)
    seed_youtube_cta_experiment(session)
    orch = GrowthOrchestratorAgent()

    diagnostic = orch.run(
        session,
        OrchestratorQuestion(
            question="Why did Premium conversion decrease?",
            days=EVAL_DAYS,
            as_of=EVAL_AS_OF,
        ),
    )
    action = orch.run(
        session,
        OrchestratorQuestion(
            question="What should we do about the Premium conversion drop?",
            days=EVAL_DAYS,
            as_of=EVAL_AS_OF,
        ),
    )
    experiment = orch.run(
        session,
        OrchestratorQuestion(
            question="Did the YouTube CTA experiment work?",
            days=EVAL_DAYS,
            as_of=EVAL_AS_OF,
        ),
    )

    result = EvalResult(case_id="eval_orchestrator_routing")
    result.require(
        "tool_selection",
        diagnostic.route == RouteKind.ANALYST_ONLY
        and "growth_strategist_agent" not in diagnostic.agents_called,
        f"diagnostic route={diagnostic.route} agents={diagnostic.agents_called}",
    )
    result.require(
        "completeness",
        action.route == RouteKind.ANALYST_THEN_STRATEGIST
        and "growth_strategist_agent" in action.agents_called,
        f"action route={action.route} agents={action.agents_called}",
    )
    result.require(
        "tool_selection",
        experiment.route == RouteKind.EXPERIMENT
        and experiment.agents_called == ["growth_experiment_analyst_agent"],
        f"experiment route={experiment.route} agents={experiment.agents_called}",
    )
    _assert_passed(result)


def test_eval_strategist_premium_actions(session) -> None:
    seed_premium_drop_fixture(session)
    report = GrowthStrategistAgent().run(
        session,
        StrategistQuestion(
            question="What should we do about the Premium conversion drop?",
            days=EVAL_DAYS,
            as_of=EVAL_AS_OF,
        ),
    )
    result = EvalResult(case_id="eval_strategist_premium_actions")
    result.scores.append(
        score_recommendations_grounded(
            [r.title for r in report.recommendations],
            report.analyst_primary_driver,
        )
    )
    result.require(
        "factuality",
        any(c.label == SemanticLabel.RECOMMENDATION for c in report.claims),
        "missing RECOMMENDATION claims",
    )
    result.scores.append(
        score_hallucination_text(
            report.analyst_primary_driver,
            *(r.action for r in report.recommendations),
        )
    )
    _assert_passed(result)


def test_eval_experiment_youtube_cta(session) -> None:
    seed_youtube_cta_experiment(session)
    report = GrowthExperimentAnalystAgent().run(
        session,
        ExperimentAnalystQuestion(
            question="Did the YouTube CTA experiment work?",
            experiment_key="syn_exp_youtube_cta",
        ),
    )
    result = EvalResult(case_id="eval_experiment_youtube_cta")
    result.require(
        "numerical_accuracy",
        report.decision_hint == DecisionHint.SHIP_TREATMENT,
        f"decision_hint={report.decision_hint}",
    )
    result.scores.append(score_has_fact_claims(report.claims))
    result.scores.append(
        score_hallucination_text(*(c.text for c in report.claims))
    )
    _assert_passed(result)
