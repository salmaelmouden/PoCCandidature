"""
Phase 16 / W2 — contract tests for the `metric_validation` skill.

The skill answers one question, deterministically and before any LLM sees the data:
is this funnel result a finding, or is it a symptom of broken data?

It exists because the pipeline could not tell the difference. A rounding artefact
emptied the terminal stage, `calculate_funnel` reported a 100 % dropoff, and the
strategist turned that into a confident `[P0] Fix Premium leak on weakest channel`
with an action plan for a phenomenon that never happened.

Per ADR-002 the rule lives in a deterministic skill, not in a prompt: an agent asked
politely not to over-interpret will over-interpret.
"""

from __future__ import annotations

import pytest

from app.skills.funnel_analysis import calculate_funnel
from app.skills.metric_validation import (
    MIN_SIGNIFICANT_UPSTREAM,
    WarningCode,
    validate_funnel,
)


def _funnel(**counts: int):
    """Build a FunnelResult through the real skill — never hand-rolled."""
    return calculate_funnel(
        {
            "views": counts.get("views", 100_000),
            "visits": counts.get("visits", 20_000),
            "signups": counts.get("signups", 1_500),
            "activated_users": counts.get("activated_users", 800),
            "premium_users": counts.get("premium_users", 95),
        }
    )


def test_healthy_funnel_raises_nothing() -> None:
    """A funnel that converts at every stage must pass silently.

    Guards the obvious failure mode of a validator: warning so often that the
    warnings stop being read.
    """
    result = validate_funnel(_funnel())
    assert result.warnings == []
    assert result.has_blocking is False
    assert result.blocking_stages == frozenset()


def test_the_historical_case_is_flagged_and_blocking() -> None:
    """
    The exact shape that shipped: 566 activations, 0 Premium, over the weekly window
    of 2026-08-14 → 08-20. This is the test that would have caught the bug.
    """
    result = validate_funnel(_funnel(activated_users=566, premium_users=0))

    codes = {w.code for w in result.warnings}
    assert WarningCode.TERMINAL_STAGE_EMPTY in codes

    warning = next(w for w in result.warnings if w.code is WarningCode.TERMINAL_STAGE_EMPTY)
    assert warning.stage == "premium_users"
    assert warning.blocking is True
    assert result.has_blocking is True
    assert "premium_users" in result.blocking_stages
    # The numbers that justify the warning travel with it — a warning a human
    # cannot check is a warning a human will dismiss.
    assert warning.numbers["upstream_count"] == 566
    assert warning.numbers["stage_count"] == 0


def test_empty_terminal_stage_on_thin_volume_is_not_blocking() -> None:
    """
    Zero Premium out of 12 activations is ordinary smallness, not broken data.
    Blocking here would make the validator cry wolf on every low-traffic slice and
    train everyone to ignore it.
    """
    result = validate_funnel(
        _funnel(signups=20, activated_users=12, premium_users=0)
    )

    codes = {w.code for w in result.warnings}
    assert WarningCode.COHORT_TOO_SMALL in codes
    assert WarningCode.TERMINAL_STAGE_EMPTY not in codes
    assert result.has_blocking is False


def test_threshold_boundary_is_exact() -> None:
    """Thresholds are documented in the contract, so they are asserted, not implied."""
    just_below = validate_funnel(
        _funnel(activated_users=MIN_SIGNIFICANT_UPSTREAM - 1, premium_users=0)
    )
    at_threshold = validate_funnel(
        _funnel(activated_users=MIN_SIGNIFICANT_UPSTREAM, premium_users=0)
    )
    assert just_below.has_blocking is False
    assert at_threshold.has_blocking is True


def test_mid_funnel_collapse_is_impossible_not_interesting() -> None:
    """
    A mid-funnel stage at zero under significant upstream volume cannot be a real
    growth event — traffic does not convert at exactly 0 % while the stages below it
    still report users. That is a data fault, and it must be named as one.
    """
    result = validate_funnel(
        _funnel(visits=5_000, signups=0, activated_users=0, premium_users=0)
    )

    codes = {w.code for w in result.warnings}
    assert WarningCode.IMPOSSIBLE_DROPOFF in codes
    assert result.has_blocking is True
    assert "signups" in result.blocking_stages


def test_validation_is_pure() -> None:
    """No I/O, no clock, no randomness — same input, same verdict (ADR-002)."""
    funnel = _funnel(activated_users=566, premium_users=0)
    first = validate_funnel(funnel)
    second = validate_funnel(funnel)
    assert first == second


@pytest.mark.parametrize("code", list(WarningCode))
def test_every_warning_code_carries_a_human_sentence(code: WarningCode) -> None:
    """
    Warnings surface at the top of the memo and the weekly report, in front of a
    growth reader. A bare enum name is not a message.
    """
    assert code.message_template
    assert code.message_template.strip() == code.message_template
    assert len(code.message_template) > 20
