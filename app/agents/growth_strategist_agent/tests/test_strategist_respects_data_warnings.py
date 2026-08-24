"""
Phase 16 / W2 — the strategist must not build strategy on data it was told is broken.

The failure this closes: `[P0] Fix Premium leak on weakest channel`, emitted with a
detailed remediation plan (paywall audit, CTA timing) against a Premium stage that
was empty because of an integer-truncation artefact, and shipped weekly by n8n.

Two mechanisms, deliberately redundant:

1. `data_warnings` reaches the agent through its **input schema**, so the reasoning
   layer has the context.
2. A **deterministic post-condition** rewrites any P0/P1 recommendation aimed at a
   blocked stage. Correctness must not depend on the model complying — ADR-002 puts
   the arithmetic and the rules in Python, and this is a rule.

The tests below target mechanism 2, because that is the one that is supposed to hold
without an LLM in the loop.
"""

from __future__ import annotations

from datetime import date

from app.agents.growth_strategist_agent import GrowthStrategistAgent, StrategistQuestion
from app.agents.growth_strategist_agent.schemas import Priority
from app.db.repositories import AcquisitionRepository
from app.skills.funnel_analysis import calculate_funnel
from app.skills.metric_validation import WarningCode, validate_funnel

AS_OF = date(2026, 8, 20)


def _seed_degenerate_funnel(session) -> None:
    """Significant traffic and activation, terminal stage empty — the shipped shape."""
    repo = AcquisitionRepository(session)
    for metric_date, channel in ((date(2026, 8, 18), "YouTube"), (date(2026, 8, 16), "Paid")):
        repo.upsert(
            metric_date=metric_date,
            channel=channel,
            topic="Crypto",
            video_id=None,
            views=42_000,
            visits=9_000,
            signups=620,
            activated_users=283,
            premium_users=0,
            is_synthetic=True,
            dataset_label="synthetic_v1",
        )
    session.commit()


def _warnings_for_degenerate_funnel():
    return validate_funnel(
        calculate_funnel(
            {
                "views": 84_000,
                "visits": 18_000,
                "signups": 1_240,
                "activated_users": 566,
                "premium_users": 0,
            }
        )
    ).warnings


def test_no_urgent_recommendation_targets_a_blocked_stage(session) -> None:
    """The core post-condition: a warned stage cannot carry a P0 or a P1."""
    _seed_degenerate_funnel(session)

    report = GrowthStrategistAgent().run(
        session,
        StrategistQuestion(
            question="What should we do about Premium conversion this week?",
            days=7,
            as_of=AS_OF,
            data_warnings=_warnings_for_degenerate_funnel(),
        ),
    )

    urgent = [r for r in report.recommendations if r.priority in (Priority.P0, Priority.P1)]
    offending = [r for r in urgent if r.target_stage == "premium_users"]
    assert offending == [], (
        "strategist raised urgent work on a stage flagged as broken data: "
        f"{[r.title for r in offending]}"
    )


def test_it_proposes_verifying_the_data_instead_of_staying_silent(session) -> None:
    """
    Suppression alone would be a regression: the reader loses the signal entirely and
    the pipeline looks healthy. `03-agents.mdc` requires an agent to state when
    evidence is insufficient, so the recommendation is replaced, not dropped.
    """
    _seed_degenerate_funnel(session)

    report = GrowthStrategistAgent().run(
        session,
        StrategistQuestion(
            question="What should we do about Premium conversion this week?",
            days=7,
            as_of=AS_OF,
            data_warnings=_warnings_for_degenerate_funnel(),
        ),
    )

    assert report.recommendations, "report must not be emptied by the post-condition"
    verify = [r for r in report.recommendations if r.target_stage == "premium_users"]
    assert verify, "the blocked stage must still be spoken about"
    assert any(
        WarningCode.TERMINAL_STAGE_EMPTY.value in (r.grounded_in or "") for r in verify
    ), "the replacement must cite the warning that caused it"
    assert report.insufficient_evidence is True


def test_unblocked_recommendations_pass_through_unchanged(session) -> None:
    """
    The post-condition is scoped to warned stages. A warning about Premium must not
    silence advice about anything else — over-suppression would make the guardrail
    more damaging than the bug it prevents.

    Stated as invariance rather than existence: whatever the playbook produces for
    unblocked stages must survive the guardrail byte for byte. Asserting instead that
    *some* other-stage recommendation exists would test the playbook's content, not
    the guardrail's reach, and would break every time the playbook changed.
    """
    _seed_degenerate_funnel(session)
    question = StrategistQuestion(
        question="What should we do about Premium conversion this week?",
        days=7,
        as_of=AS_OF,
    )

    ungated = GrowthStrategistAgent().run(session, question)
    gated = GrowthStrategistAgent().run(
        session,
        question.model_copy(update={"data_warnings": _warnings_for_degenerate_funnel()}),
    )

    def unblocked(report):
        return [
            (r.title, r.priority, r.action)
            for r in report.recommendations
            if r.target_stage != "premium_users"
        ]

    assert unblocked(gated) == unblocked(ungated)


def test_healthy_funnel_is_unchanged_by_the_guardrail(session) -> None:
    """No warnings in, identical behaviour out — the guardrail is inert when it should be."""
    repo = AcquisitionRepository(session)
    repo.upsert(
        metric_date=date(2026, 8, 18),
        channel="YouTube",
        topic="Crypto",
        video_id=None,
        views=42_000,
        visits=9_000,
        signups=620,
        activated_users=283,
        premium_users=31,
        is_synthetic=True,
        dataset_label="synthetic_v1",
    )
    session.commit()

    question = StrategistQuestion(
        question="What should we do about Premium conversion this week?",
        days=7,
        as_of=AS_OF,
    )
    with_empty_warnings = GrowthStrategistAgent().run(
        session, question.model_copy(update={"data_warnings": []})
    )
    baseline = GrowthStrategistAgent().run(session, question)

    assert [r.title for r in with_empty_warnings.recommendations] == [
        r.title for r in baseline.recommendations
    ]
    assert baseline.insufficient_evidence is False
