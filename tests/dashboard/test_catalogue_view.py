"""Tests for the public-catalogue presentation helpers — pure, no Streamlit runtime."""

from __future__ import annotations

import json

import pytest

from app.skills.public_signal_analysis import DimensionStat
from dashboard.catalogue_view import (
    HOOK_FR,
    TOPIC_FR,
    dumbbell,
    empty_state_message,
    fr,
    humanize_age,
    label_of,
    paired_frame,
    pick,
    rank_of,
    scatter,
    table_frame,
)
from dashboard.theme import DARK_TOKENS, LIGHT_TOKENS


def stat(
    value: str,
    *,
    videos: int = 20,
    reach: float = 1.0,
    engagement: float = 0.02,
    share: float = 0.1,
) -> DimensionStat:
    return DimensionStat(
        value=value,
        videos=videos,
        median_reach_index=reach,
        median_engagement_rate=engagement,
        total_views=1000,
        share_of_catalogue=share,
    )


def test_label_falls_back_to_raw_key() -> None:
    assert label_of("crypto") == TOPIC_FR["crypto"]
    assert label_of("autorite") == HOOK_FR["autorite"]
    # A taxonomy value added later must still render, not crash or show blank.
    assert label_of("nouveau_sujet") == "nouveau_sujet"


def test_french_decimal_notation() -> None:
    assert fr(1.33) == "1,33"
    assert fr(0.8) == "0,80"  # trailing zero kept so columns align
    assert fr(2.0, 1) == "2,0"
    assert fr(1.336) == "1,34"  # rounds, not truncates


def test_pick_returns_none_when_absent() -> None:
    rows = [stat("crypto")]
    assert pick(rows, "crypto") is not None
    assert pick(rows, "immobilier") is None


def test_rank_is_one_based_and_none_when_absent() -> None:
    rows = [stat("a", reach=1.5), stat("b", reach=1.2), stat("c", reach=0.9)]
    assert rank_of(rows, "a") == 1
    assert rank_of(rows, "c") == 3
    assert rank_of(rows, "z") is None


def test_paired_frame_keeps_only_values_in_both_formats() -> None:
    shorts = [stat("crypto", reach=1.0), stat("shorts_only", reach=2.0)]
    longs = [stat("crypto", reach=1.4), stat("long_only", reach=0.5)]

    frame = paired_frame(shorts, longs)

    assert frame["cle"].tolist() == ["crypto"]


def test_paired_frame_gap_sign_and_sort() -> None:
    shorts = [stat("gagne", reach=0.8), stat("perd", reach=1.2)]
    longs = [stat("gagne", reach=1.3), stat("perd", reach=0.9)]

    frame = paired_frame(shorts, longs)

    assert frame["cle"].tolist() == ["gagne", "perd"]  # descending gap
    assert frame.loc[0, "ecart"] == 0.5
    assert frame.loc[1, "ecart"] == -0.3


def test_paired_frame_flags_thin_samples() -> None:
    shorts = [stat("mince", videos=4), stat("large", videos=40)]
    longs = [stat("mince", videos=40), stat("large", videos=40)]

    frame = paired_frame(shorts, longs).set_index("cle")

    assert bool(frame.loc["mince", "mince"]) is True
    assert bool(frame.loc["large", "mince"]) is False


def test_paired_frame_handles_no_overlap() -> None:
    frame = paired_frame([stat("a")], [stat("b")])

    assert frame.empty


def test_table_marks_thin_rows_rather_than_hiding_them() -> None:
    rows = [stat("crypto", videos=4), stat("immobilier", videos=40)]

    frame = table_frame(rows, with_share=False)

    assert frame.loc[0, "Catégorie"].endswith(" *")
    assert not frame.loc[1, "Catégorie"].endswith(" *")
    assert len(frame) == 2


def test_table_share_column_is_opt_in() -> None:
    rows = [stat("crypto", share=0.202)]

    assert "Part du corpus %" not in table_frame(rows, with_share=False).columns
    assert table_frame(rows, with_share=True).loc[0, "Part du corpus %"] == 20.2


def test_table_converts_engagement_to_percent() -> None:
    frame = table_frame([stat("crypto", engagement=0.0248)], with_share=False)

    assert frame.loc[0, "Engagement %"] == 2.48


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (None, "—"),
        (-5, "à l'instant"),  # clock skew must not print a negative age
        (0, "à l'instant"),
        (59, "à l'instant"),
        (60, "il y a 1 min"),
        # The reason this helper exists: a 15-minute refresh cadence has to be
        # legible. Hour-only wording rendered every cycle as "moins d'1 h".
        (900, "il y a 15 min"),
        (3599, "il y a 59 min"),
        (3600, "il y a 1 h"),
        (5400, "il y a 1 h 30"),
        (86400, "il y a 1 jour"),
        (180000, "il y a 2 jours"),
    ],
)
def test_humanize_age(seconds: float | None, expected: str) -> None:
    assert humanize_age(seconds) == expected


def test_charts_build_without_error() -> None:
    """Altair validates its own spec on to_dict() — this catches encoding mistakes."""
    shorts = [stat("crypto", reach=1.0), stat("immobilier", reach=1.1)]
    longs = [stat("crypto", reach=1.4), stat("immobilier", reach=0.9)]

    dumbbell_spec = dumbbell(paired_frame(shorts, longs), "titre").to_dict()
    scatter_spec = scatter(longs, "titre").to_dict()

    # The title carries its own typography now, so it is an object rather than
    # a bare string — the text is what this test is actually about.
    assert dumbbell_spec["title"]["text"] == "titre"
    assert scatter_spec["title"]["text"] == "titre"


def test_charts_follow_the_active_theme() -> None:
    """A dark render must use the dark-stepped hues, not the light ones."""
    shorts = [stat("crypto", reach=1.0), stat("immobilier", reach=1.1)]
    longs = [stat("crypto", reach=1.4), stat("immobilier", reach=0.9)]
    frame = paired_frame(shorts, longs)

    light = json.dumps(dumbbell(frame, "titre", LIGHT_TOKENS).to_dict())
    dark = json.dumps(dumbbell(frame, "titre", DARK_TOKENS).to_dict())

    assert LIGHT_TOKENS.categorical[0] in light
    assert DARK_TOKENS.categorical[0] in dark
    assert light != dark


# ---------------------------------------------------- the public empty state
#
# This page answers an unauthenticated URL. When the catalogue is empty the
# analysis skill raises, and an unhandled raise means Streamlit renders a stack
# trace — internal paths included — to whoever holds the link. That regression
# has already shipped once: the handling was written for the old
# `dashboard/pages/` page and lost when it was replaced by `dashboard/views/`.


def test_populated_catalogue_renders_normally() -> None:
    assert empty_state_message(has_report=True, videos=953, classified=953) is None


def test_no_videos_points_at_the_refresher() -> None:
    message = empty_state_message(has_report=False, videos=0, classified=0)
    assert message is not None
    assert "Catalogue vide" in message
    assert "refresh_catalogue.py" in message


def test_unclassified_videos_point_at_the_classifier_instead() -> None:
    """Naming the refresher here would send the reader after the wrong fix."""
    message = empty_state_message(has_report=False, videos=953, classified=0)
    assert message is not None
    assert "ANTHROPIC_API_KEY" in message
    assert "Catalogue vide" not in message
    assert "953" in message


def test_a_report_that_failed_to_build_still_stops_the_page() -> None:
    """has_report=False is the PublicSignalError case, whatever the counts say."""
    assert empty_state_message(has_report=False, videos=953, classified=953) is not None
