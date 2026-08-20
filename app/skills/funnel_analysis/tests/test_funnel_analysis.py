"""Tests for funnel_analysis skill."""

import pytest
from pydantic import ValidationError

from app.skills.funnel_analysis import (
    calculate_conversion_rates,
    calculate_dropoffs,
    calculate_funnel,
    compare_funnel_periods,
    identify_bottleneck,
)


SAMPLE = {
    "views": 10000,
    "visits": 2000,
    "signups": 400,
    "activated_users": 200,
    "premium_users": 40,
}


def test_calculate_funnel_happy_path() -> None:
    result = calculate_funnel(SAMPLE)
    assert result.counts.views == 10000
    assert result.conversions[0].from_stage == "views"
    assert result.conversions[0].rate == pytest.approx(0.2)
    assert result.dropoffs[0].dropoff_count == 8000
    assert result.bottleneck_from_stage == "views"
    assert result.bottleneck_dropoff_rate == pytest.approx(0.8)


def test_rejects_increasing_funnel() -> None:
    with pytest.raises(ValidationError):
        calculate_funnel(
            {
                "views": 100,
                "visits": 200,
                "signups": 50,
                "activated_users": 20,
                "premium_users": 5,
            }
        )


def test_empty_zero_funnel() -> None:
    result = calculate_funnel(
        {
            "views": 0,
            "visits": 0,
            "signups": 0,
            "activated_users": 0,
            "premium_users": 0,
        }
    )
    assert all(c.rate == 0.0 for c in result.conversions)
    assert result.bottleneck_dropoff_rate == 0.0


def test_identify_bottleneck_prefers_highest_dropoff() -> None:
    dropoffs = calculate_dropoffs(SAMPLE)
    bottleneck = identify_bottleneck(dropoffs)
    assert bottleneck is not None
    assert bottleneck.from_stage == "views"


def test_compare_funnel_periods() -> None:
    previous = {
        "views": 10000,
        "visits": 2000,
        "signups": 400,
        "activated_users": 200,
        "premium_users": 50,
    }
    current = {
        "views": 10000,
        "visits": 2000,
        "signups": 400,
        "activated_users": 200,
        "premium_users": 40,
    }
    comparison = compare_funnel_periods(current, previous)
    assert comparison.absolute_deltas["premium_users"] == -10
    assert comparison.relative_deltas["premium_users"] == pytest.approx(-0.2)
    key = "activated_users_to_premium_users"
    assert comparison.conversion_rate_deltas[key] == pytest.approx(-0.05)


def test_conversion_rates_length() -> None:
    assert len(calculate_conversion_rates(SAMPLE)) == 4
