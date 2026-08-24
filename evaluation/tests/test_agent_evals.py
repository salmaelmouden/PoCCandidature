"""Runnable agent evaluation suite (Phase 10; degenerate-funnel case added Phase 16)."""

from __future__ import annotations

from datetime import timedelta

from app.agents.growth_data_analyst_agent import AnalystQuestion, GrowthDataAnalystAgent
from app.agents.growth_data_analyst_agent.schemas import SemanticLabel
from app.agents.growth_experiment_analyst_agent import (
    ExperimentAnalystQuestion,
    GrowthExperimentAnalystAgent,
)
from app.agents.growth_orchestrator_agent import GrowthOrchestratorAgent, OrchestratorQuestion
from app.agents.growth_orchestrator_agent.schemas import RouteKind
from app.agents.growth_strategist_agent import GrowthStrategistAgent, StrategistQuestion
from app.agents.growth_strategist_agent.schemas import Priority
from app.db.repositories import AcquisitionRepository
from app.skills.experiment_analysis import DecisionHint
from app.skills.funnel_analysis import calculate_funnel
from app.skills.metric_validation import WarningCode, validate_funnel
from evaluation.datasets.fixtures import (
    EVAL_AS_OF,
    EVAL_DAYS,
    seed_degenerate_funnel_fixture,
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


def test_eval_strategist_degenerate_funnel(session) -> None:
    """Broken data must produce a data question, never a growth strategy (Phase 16 / W2).

    Case doc: `evaluation/cases/eval_strategist_degenerate_funnel.md`.
    """
    seed_degenerate_funnel_fixture(session)
    warnings = validate_funnel(
        calculate_funnel(
            AcquisitionRepository(session).sum_funnel(
                start=EVAL_AS_OF - timedelta(days=EVAL_DAYS - 1), end=EVAL_AS_OF
            )
        )
    ).warnings

    report = GrowthStrategistAgent().run(
        session,
        StrategistQuestion(
            question="What should we do about Premium conversion this week?",
            days=EVAL_DAYS,
            as_of=EVAL_AS_OF,
            data_warnings=warnings,
        ),
    )

    result = EvalResult(case_id="eval_strategist_degenerate_funnel")
    result.require(
        "guardrail",
        not [
            r
            for r in report.recommendations
            if r.target_stage == "premium_users"
            and r.priority in (Priority.P0, Priority.P1)
        ],
        "urgent recommendation raised on a stage flagged as broken data",
    )
    blocked_items = [r for r in report.recommendations if r.target_stage == "premium_users"]
    result.require(
        "non_suppression",
        bool(blocked_items),
        "blocked stage vanished from the report — silence reads as health",
    )
    result.require(
        "attribution",
        any(
            WarningCode.TERMINAL_STAGE_EMPTY.value in (r.grounded_in or "")
            for r in blocked_items
        ),
        "replacement item does not cite the warning that caused it",
    )
    ungated = GrowthStrategistAgent().run(
        session,
        StrategistQuestion(
            question="What should we do about Premium conversion this week?",
            days=EVAL_DAYS,
            as_of=EVAL_AS_OF,
        ),
    )

    def _unblocked(rep):
        return [
            (r.title, r.priority, r.action)
            for r in rep.recommendations
            if r.target_stage != "premium_users"
        ]

    result.require(
        "scope",
        _unblocked(report) == _unblocked(ungated),
        "recommendations on unwarned stages were altered by the guardrail",
    )
    # A causal story about an empty stage is the exact hallucination that shipped.
    forbidden = ("paywall", "pricing", "cta", "onboarding")
    result.require(
        "hallucination",
        not [
            r
            for r in blocked_items
            if any(word in f"{r.action} {r.rationale}".lower() for word in forbidden)
        ],
        "explained an empty stage with a growth narrative",
    )
    _assert_passed(result)
