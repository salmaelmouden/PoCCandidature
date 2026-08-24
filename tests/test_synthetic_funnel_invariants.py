"""
Phase 16 / W1 — funnel rate invariants for the synthetic generator.

These tests exist because `int()` applied at the `day × channel × topic` grain does
not round: it floors. With ~3 activated users per row and a ~12 % premium rate,
`int(3 * 0.13) == 0` on essentially every row, so the terminal stage collapsed to
11 events in 60 days (0.22 % of activations) against a configured ~12 %. Nothing
upstream showed it — those stages carry operands one or two orders of magnitude
above the truncation threshold.

Design note for the implementer: every bound below is derived from module-level
constants, never from a literal copied into the test. That requires the per-channel
rates currently inlined in `_build_acquisitions` to be lifted to module constants:

    _BASE_SIGNUP_RATE, _ACTIVATE_RATE, _BASE_PREMIUM_RATE,
    _VISIT_RATE, _SIGNUP_CHANNEL_MULT, _PREMIUM_CHANNEL_MULT,
    _PREMIUM_YOUTUBE_BASE, _PREMIUM_YOUTUBE_DECLINE,
    _JITTER_VISITS, _JITTER_SIGNUPS, _JITTER_ACTIVATED, _JITTER_PREMIUM

A rate that cannot be read from the module cannot be asserted against without
copying it, and a test that copies the value it checks proves nothing.
"""

from __future__ import annotations

from collections import Counter
from datetime import date

import pytest

from app.db.constants import Channel
from app.db.synthetic import (
    _ACTIVATE_RATE,
    _BASE_PREMIUM_RATE,
    _BASE_SIGNUP_RATE,
    _JITTER_ACTIVATED,
    _JITTER_PREMIUM,
    _JITTER_SIGNUPS,
    _JITTER_VISITS,
    _PREMIUM_CHANNEL_MULT,
    _PREMIUM_YOUTUBE_BASE,
    _PREMIUM_YOUTUBE_DECLINE,
    _SIGNUP_CHANNEL_MULT,
    _TOPIC_CONV,
    _VISIT_RATE,
    generate_synthetic_dataset,
)

# Pinned so the invariant is reproducible; matches the demo window used elsewhere.
SEED = 42
DAYS = 60
AS_OF = date(2026, 8, 20)


@pytest.fixture(scope="module")
def acquisitions():
    return generate_synthetic_dataset(seed=SEED, days=DAYS, as_of=AS_OF).acquisitions


def _totals(rows) -> Counter:
    totals: Counter = Counter()
    for row in rows:
        totals["views"] += row.views
        totals["visits"] += row.visits
        totals["signups"] += row.signups
        totals["activated_users"] += row.activated_users
        totals["premium_users"] += row.premium_users
    return totals


def _visit_rate_bounds() -> tuple[float, float]:
    rates = [_VISIT_RATE[channel] for channel in Channel]
    return min(rates) * _JITTER_VISITS[0], max(rates) * _JITTER_VISITS[1]


def _signup_rate_bounds() -> tuple[float, float]:
    convs = list(_TOPIC_CONV.values())
    mults = [_SIGNUP_CHANNEL_MULT[channel] for channel in Channel]
    low = _BASE_SIGNUP_RATE * min(convs) * min(mults) * _JITTER_SIGNUPS[0]
    high = _BASE_SIGNUP_RATE * max(convs) * max(mults) * _JITTER_SIGNUPS[1]
    return low, high


def _activation_rate_bounds() -> tuple[float, float]:
    return _ACTIVATE_RATE * _JITTER_ACTIVATED[0], _ACTIVATE_RATE * _JITTER_ACTIVATED[1]


def _premium_rate_bounds() -> tuple[float, float]:
    convs = list(_TOPIC_CONV.values())
    mults = [_PREMIUM_CHANNEL_MULT[channel] for channel in Channel]
    # YouTube is multiplied in both regimes; the decline factor is the global floor.
    low = (
        _BASE_PREMIUM_RATE
        * min(convs)
        * min([*mults, _PREMIUM_YOUTUBE_DECLINE])
        * _JITTER_PREMIUM[0]
    )
    high = _BASE_PREMIUM_RATE * max(convs) * max(mults) * _JITTER_PREMIUM[1]
    return low, high


@pytest.mark.parametrize(
    "from_stage,to_stage,bounds_fn",
    [
        ("views", "visits", _visit_rate_bounds),
        ("visits", "signups", _signup_rate_bounds),
        ("signups", "activated_users", _activation_rate_bounds),
        ("activated_users", "premium_users", _premium_rate_bounds),
    ],
)
def test_stage_rate_stays_inside_its_configured_band(
    acquisitions, from_stage, to_stage, bounds_fn
) -> None:
    """
    An aggregate rate is a volume-weighted mean of per-row rates, so it must land
    inside the band those per-row rates span. Truncation at the row grain pushes it
    below the floor — which is exactly how the Premium stage failed while every
    upstream stage stayed plausible.

    Parametrised across all four transitions on purpose: the defect is a property of
    operand magnitude, not of the Premium stage, so it can resurface anywhere a
    multiplier shrinks.
    """
    totals = _totals(acquisitions)
    upstream = totals[from_stage]
    assert upstream > 0, f"no {from_stage} generated — fixture is degenerate"

    observed = totals[to_stage] / upstream
    low, high = bounds_fn()
    assert low <= observed <= high, (
        f"{from_stage}→{to_stage} rate {observed:.4%} outside configured band "
        f"[{low:.4%}, {high:.4%}] over {DAYS}d "
        f"({totals[to_stage]:,} / {upstream:,})"
    )


def test_premium_is_not_systematically_floored(acquisitions) -> None:
    """
    The band test above catches the magnitude of the collapse; this one catches its
    shape. Flooring does not shave the terminal stage evenly — it empties almost
    every row and leaves a handful of survivors where activation happened to be
    large enough to round up. Measured before the fix: 11 of 2 160 rows (0.5 %).

    The floor is deliberately loose. Correct rounding puts this near 20–35 % given
    the observed activation distribution; asserting 10 % keeps the test insensitive
    to tuning while staying an order of magnitude above the failure.
    """
    rows_with_premium = sum(1 for row in acquisitions if row.premium_users > 0)
    share = rows_with_premium / len(acquisitions)
    assert share >= 0.10, (
        f"only {rows_with_premium}/{len(acquisitions)} rows ({share:.1%}) carry a "
        "premium conversion — the terminal stage is being floored, not rounded"
    )


def test_youtube_decline_matches_its_configured_ratio(acquisitions) -> None:
    """
    The generator's narrative is a YouTube Premium decline in the recent window.
    The existing test only asserts *some* decline, which a broken terminal stage can
    satisfy by accident (0 vs 0 is not a decline, but near-zero noise can be). Pin
    the ratio to the configured factors instead, so the narrative is falsifiable.
    """
    current_start = AS_OF.toordinal() - 13
    previous_start, previous_end = AS_OF.toordinal() - 27, AS_OF.toordinal() - 14

    def rate(start_ord: int, end_ord: int) -> float:
        activated = premium = 0
        for row in acquisitions:
            if row.channel != Channel.YOUTUBE.value:
                continue
            if start_ord <= row.metric_date.toordinal() <= end_ord:
                activated += row.activated_users
                premium += row.premium_users
        assert activated > 0, "no YouTube activations in window"
        return premium / activated

    current = rate(current_start, AS_OF.toordinal())
    previous = rate(previous_start, previous_end)

    assert previous > 0, "baseline window has no Premium conversions at all"
    expected_ratio = _PREMIUM_YOUTUBE_DECLINE / _PREMIUM_YOUTUBE_BASE
    observed_ratio = current / previous
    assert observed_ratio == pytest.approx(expected_ratio, rel=0.35), (
        f"decline ratio {observed_ratio:.3f} does not match configured "
        f"{expected_ratio:.3f} (current {current:.4%}, previous {previous:.4%})"
    )


def test_generator_stays_deterministic_under_stochastic_rounding() -> None:
    """
    Stochastic rounding draws from the seeded Random, so reproducibility must be
    re-proved: the fix trades an exact per-row value for an unbiased one, and that
    is only acceptable if the same seed still yields the same dataset.
    """
    a = generate_synthetic_dataset(seed=SEED, days=DAYS, as_of=AS_OF).acquisitions
    b = generate_synthetic_dataset(seed=SEED, days=DAYS, as_of=AS_OF).acquisitions
    assert _totals(a) == _totals(b)
    assert [r.premium_users for r in a] == [r.premium_users for r in b]
