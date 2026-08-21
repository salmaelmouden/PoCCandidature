"""Tests for the public-catalogue presentation helpers — pure, no Streamlit runtime."""

from __future__ import annotations

from app.skills.public_signal_analysis import DimensionStat
from dashboard.catalogue_view import (
    HOOK_FR,
    TOPIC_FR,
    dumbbell,
    fr,
    label_of,
    paired_frame,
    pick,
    rank_of,
    scatter,
    table_frame,
)


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


def test_charts_build_without_error() -> None:
    """Altair validates its own spec on to_dict() — this catches encoding mistakes."""
    shorts = [stat("crypto", reach=1.0), stat("immobilier", reach=1.1)]
    longs = [stat("crypto", reach=1.4), stat("immobilier", reach=0.9)]

    dumbbell_spec = dumbbell(paired_frame(shorts, longs), "titre").to_dict()
    scatter_spec = scatter(longs, "titre").to_dict()

    assert dumbbell_spec["title"] == "titre"
    assert scatter_spec["title"] == "titre"
