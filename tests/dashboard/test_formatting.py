"""Tests for French number, date and vocabulary formatting."""

from __future__ import annotations

from datetime import date

import pytest

from dashboard.formatting import (
    NBSP,
    THIN_SPACE,
    channel_label,
    fmt_compact,
    fmt_date,
    fmt_delta,
    fmt_int,
    fmt_pct,
    fmt_period,
    fmt_points,
    stage_short,
    topic_label,
    transition_label,
)


def test_thousands_use_a_narrow_no_break_space() -> None:
    """A comma here would read as a decimal point to a French reader."""
    assert fmt_int(128402) == f"128{THIN_SPACE}402"
    assert fmt_int(999) == "999"
    assert fmt_int(1_000_000) == f"1{THIN_SPACE}000{THIN_SPACE}000"


def test_missing_values_are_a_dash_not_a_zero() -> None:
    assert fmt_int(None) == "—"
    assert fmt_compact(None) == "—"
    assert fmt_date(None) == "—"
    assert fmt_period(None, date(2026, 5, 1)) == "—"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0"),
        (842, "842"),
        (999, "999"),
        (1_000, f"1,0{NBSP}k"),
        (128_402, f"128,4{NBSP}k"),
        (1_300_000, f"1,3{NBSP}M"),
        (-2_400, f"-2,4{NBSP}k"),
    ],
)
def test_compact_form(value: int, expected: str) -> None:
    assert fmt_compact(value) == expected


def test_percentages_are_french_and_unbreakable() -> None:
    assert fmt_pct(0.1234) == f"12,3{NBSP}%"
    assert fmt_pct(0.031, 2) == f"3,10{NBSP}%"
    assert fmt_pct(None) == "n/a"


def test_delta_is_none_when_there_is_no_base() -> None:
    """Streamlit hides the delta row on None — the honest rendering of "no base"."""
    assert fmt_delta(None) is None
    assert fmt_delta(0.124) == f"+12,4{NBSP}%"
    assert fmt_delta(-0.02) == f"−2,0{NBSP}%"


def test_points_are_distinct_from_percentages() -> None:
    """A rate difference is points, never a percentage of a percentage."""
    assert fmt_points(0.012) == f"+1,2{NBSP}pt"
    assert fmt_points(-0.004) == f"−0,4{NBSP}pt"
    assert fmt_points(None) == "n/a"


def test_period_appends_the_year_once_when_it_does_not_cross() -> None:
    assert fmt_period(date(2026, 5, 12), date(2026, 6, 10)) == (
        f"12{NBSP}mai → 10{NBSP}juin{NBSP}2026"
    )


def test_period_carries_both_years_when_it_crosses_one() -> None:
    assert fmt_period(date(2025, 12, 20), date(2026, 1, 18)) == (
        f"20{NBSP}déc.{NBSP}2025 → 18{NBSP}janv.{NBSP}2026"
    )


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("views_to_visits", "Vues → Visites"),
        ("activated_users_to_premium_users", "Activés → Premium"),
        ("signups_to_activated_users", "Inscr. → Activés"),
        ("views->visits", "Vues → Visites"),
    ],
)
def test_transition_labels(key: str, expected: str) -> None:
    assert transition_label(key) == expected


def test_unknown_shapes_are_left_alone_rather_than_mangled() -> None:
    """A key the mapping has not seen must still render, not vanish or crash."""
    assert transition_label("quelque_chose") == "quelque_chose"
    assert stage_short("nouvelle_etape") == "nouvelle_etape"
    assert topic_label("Nouveau Sujet") == "Nouveau Sujet"
    assert channel_label("TikTok") == "TikTok"


def test_no_channel_means_all_channels() -> None:
    assert channel_label(None) == "Tous les canaux"
