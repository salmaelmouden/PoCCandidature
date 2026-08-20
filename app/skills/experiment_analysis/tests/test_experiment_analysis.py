"""Tests for experiment_analysis skill."""

from __future__ import annotations

import pytest

from app.skills.experiment_analysis import (
    DecisionHint,
    compare_variants,
    propose_experiment_design,
)


def test_synthetic_youtube_cta_is_significant_positive() -> None:
    # Matches synthetic seed syn_exp_youtube_cta
    result = compare_variants(
        {"variant": "control", "users": 4200, "conversions": 378},
        {"variant": "treatment", "users": 4180, "conversions": 443},
    )
    assert result.control.conversion_rate == pytest.approx(0.09, abs=1e-6)
    assert result.absolute_lift > 0
    assert result.relative_lift is not None and result.relative_lift > 0
    assert result.significant is True
    assert result.decision_hint == DecisionHint.SHIP_TREATMENT
    assert result.ci_low < result.absolute_lift < result.ci_high


def test_equal_rates_inconclusive() -> None:
    result = compare_variants(
        {"variant": "control", "users": 1000, "conversions": 100},
        {"variant": "treatment", "users": 1000, "conversions": 100},
    )
    assert result.absolute_lift == 0.0
    assert result.significant is False
    assert result.decision_hint == DecisionHint.INCONCLUSIVE


def test_underpowered_small_n() -> None:
    result = compare_variants(
        {"variant": "control", "users": 20, "conversions": 2},
        {"variant": "treatment", "users": 20, "conversions": 5},
        min_users_per_variant=100,
    )
    assert result.decision_hint == DecisionHint.UNDERPOWERED


def test_rejects_conversions_gt_users() -> None:
    with pytest.raises(Exception):
        compare_variants(
            {"variant": "control", "users": 10, "conversions": 11},
            {"variant": "treatment", "users": 10, "conversions": 1},
        )


def test_propose_design_grounds_driver() -> None:
    proposal = propose_experiment_design(driver="YouTube premium_rate lag", channel_or_topic="YouTube")
    assert "YouTube" in proposal.hypothesis
    assert proposal.grounded_in == "YouTube premium_rate lag"
    assert proposal.primary_metric
