"""Tests for the funnel-entry-point presentation helpers — no Streamlit runtime."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from app.skills.cta_analysis import (
    FOLD_LINES,
    WRAP_COLUMNS,
    CtaReport,
    PlacementStat,
    VideoDescription,
    analyse_cta,
)
from dashboard.cta_view import (
    ABSENT,
    FOLDED,
    STATES,
    VISIBLE,
    coverage_frame,
    domain_frame,
    fold_sentence,
    format_gap_sentence,
    headlines,
    missing_frame,
    slice_label,
    state_frame,
    state_stack,
    teaser_sentence,
    thin_note,
    tracking_frame,
    view_weight_sentence,
    wording_frame,
)
from dashboard.theme import DARK_TOKENS, LIGHT_TOKENS

PRODUCT = "https://finary.com"


def video(
    vid: str,
    *,
    description: str = "",
    views: int = 1_000,
    duration: int = 600,
    year: int = 2025,
    title: str | None = None,
) -> VideoDescription:
    return VideoDescription(
        youtube_video_id=vid,
        title=title or f"titre {vid}",
        published_at=datetime(year, 6, 1, tzinfo=UTC),
        duration_seconds=duration,
        views=views,
        description=description,
    )


def report() -> CtaReport:
    """Two Shorts with no door, three long videos with one — one of them buried."""
    return analyse_cta(
        [
            video("s1", duration=30, views=300_000, title="Short très vu"),
            video("s2", duration=30, views=100_000, description="Abonnez-vous"),
            video("l1", description=f"Essayez Finary : {PRODUCT}?utm_source=yt", views=50_000),
            video("l2", description="a" * (WRAP_COLUMNS * 5) + f"\n{PRODUCT}", views=30_000),
            video("l3", description=f"Essayez Finary : {PRODUCT}", views=20_000, year=2024),
        ]
    )


def stat(value: str, **overrides) -> PlacementStat:
    base = {
        "value": value,
        "videos": 20,
        "with_primary": 10,
        "above_fold": 6,
        "tracked": 4,
        "views": 1_000,
        "views_with_primary": 400,
        "views_above_fold": 250,
        "median_offset": 120.0,
    }
    return PlacementStat(**{**base, **overrides})


# ---- headlines --------------------------------------------------------------


def test_headlines_name_the_domain_they_rest_on() -> None:
    cards = headlines(report())

    assert len(cards) == 3
    assert "finary.com" in cards[0].note


def test_headline_share_is_of_videos_not_of_views() -> None:
    cards = headlines(report())

    # 3 of 5 videos carry a link; 100k of 500k views do.
    assert cards[0].value.startswith("60")
    assert cards[1].value.startswith("80")


def test_attribution_card_is_dropped_when_no_link_exists() -> None:
    """A ratio over zero links is not a finding — the card leaves instead."""
    cards = headlines(analyse_cta([video("s1", duration=30)]))

    assert len(cards) == 2
    assert all("attribuable" not in card.label.lower() for card in cards)


# ---- the stack --------------------------------------------------------------


def test_three_states_partition_each_slice() -> None:
    frame = state_frame(report().by_format)

    for tranche in frame["tranche"].unique():
        rows = frame[frame["tranche"] == tranche]
        assert set(rows["etat"]) == set(STATES)
        assert round(rows["part"].sum(), 2) == 100.0


def test_above_fold_is_restated_as_a_share_of_the_slice() -> None:
    """The report stores it against linked videos; the stack needs the whole."""
    frame = state_frame([stat("long")])
    by_state = dict(zip(frame["etat"], frame["part"], strict=True))

    assert by_state[VISIBLE] == 30.0  # 6 of 20, not 6 of 10
    assert by_state[FOLDED] == 20.0
    assert by_state[ABSENT] == 50.0


def test_stack_keeps_absence_off_the_ramp() -> None:
    spec = json.loads(state_stack(report().by_format, "t", LIGHT_TOKENS).to_json())
    colour = spec["layer"][0]["encoding"]["color"]["scale"]

    assert colour["domain"] == list(STATES)
    # The two link states take ramp steps; "no link" takes the de-emphasis grey.
    assert colour["range"][2] == LIGHT_TOKENS.series_muted
    assert colour["range"][2] not in LIGHT_TOKENS.funnel_ramp


def test_stack_renders_in_both_themes() -> None:
    for tokens in (LIGHT_TOKENS, DARK_TOKENS):
        spec = json.loads(state_stack(report().by_year, "t", tokens).to_json())
        assert spec["config"]["axis"]["gridColor"] == tokens.grid


def test_stack_survives_an_empty_slice_list() -> None:
    spec = json.loads(state_stack([], "t", LIGHT_TOKENS).to_json())

    assert spec["layer"]


# ---- tables -----------------------------------------------------------------


def test_coverage_frame_marks_thin_slices_rather_than_hiding_them() -> None:
    frame = coverage_frame([stat("2021", videos=4), stat("2022", videos=40)])

    assert frame.loc[0, "Tranche"].endswith(" *")
    assert not frame.loc[1, "Tranche"].endswith(" *")


def test_coverage_frame_keeps_the_threshold_free_column() -> None:
    frame = coverage_frame([stat("long", median_offset=None)])

    assert frame.loc[0, "Position médiane"] is None


def test_domain_frame_shows_the_rejected_candidates() -> None:
    built = analyse_cta(
        [video("a", description=f"https://instagram.com/x https://youtu.be/y {PRODUCT}")]
    )
    frame = domain_frame(built)
    retained = frame[frame["Retenu"]]["Domaine"].tolist()

    assert retained == ["finary.com"]
    assert set(frame["Domaine"]) == {"finary.com", "instagram.com", "youtu.be"}
    assert set(frame["Type"]) == {"produit", "réseau social", "plateforme"}


def test_tracking_frame_counts_only_videos_carrying_a_link() -> None:
    frame = tracking_frame(report())

    assert frame["Vidéos"].sum() == 3
    assert round(frame["Part %"].sum()) == 100


def test_wording_frame_is_empty_when_no_cta_line_exists() -> None:
    assert wording_frame(analyse_cta([video("s1", duration=30)])).empty


def test_missing_frame_is_ordered_by_audience_not_by_date() -> None:
    frame = missing_frame(report())

    assert frame["Vidéo"].tolist() == ["Short très vu", "titre s2"]
    assert frame["Vues"].tolist() == [300_000, 100_000]
    assert frame.loc[0, "Lien"].endswith("s1")


def test_missing_frame_respects_its_limit() -> None:
    videos = [video(f"v{i}", duration=30, views=i) for i in range(20)]

    assert len(missing_frame(analyse_cta(videos), limit=3)) == 3


# ---- sentences --------------------------------------------------------------


def test_fold_sentence_states_its_own_threshold() -> None:
    sentence = fold_sentence(report())

    assert str(FOLD_LINES) in sentence
    assert "approximation" in sentence


def test_fold_sentence_degrades_when_no_link_exists() -> None:
    sentence = fold_sentence(analyse_cta([video("s1", duration=30)]))

    assert "Aucun lien produit" in sentence


def test_view_weight_sentence_carries_its_caveat() -> None:
    sentence = view_weight_sentence(report())

    assert "80" in sentence  # 400k of 500k views sit on a video with no link
    assert "vues à vie" in sentence


def test_format_gap_sentence_needs_both_formats() -> None:
    only_long = analyse_cta([video("l1", description=PRODUCT)])

    assert format_gap_sentence(only_long) is None


def test_format_gap_closing_claim_is_derived_not_asserted() -> None:
    """It may only appear when the least-linked format is also the most watched."""
    with_gap = format_gap_sentence(report())
    assert "ouvre le moins de portes" in with_gap

    # Shorts are the most watched *and* the best linked: the claim must not fire.
    reversed_case = analyse_cta(
        [
            video("s1", duration=30, views=500_000, description=PRODUCT),
            video("s2", duration=30, views=500_000, description=PRODUCT),
            video("l1", views=10),
            video("l2", views=10),
        ]
    )
    assert "ouvre le moins de portes" not in format_gap_sentence(reversed_case)


def test_teaser_names_the_domain_and_stays_descriptive() -> None:
    teaser = teaser_sentence(report())

    assert "finary.com" in teaser
    assert "80" in teaser  # 400k of 500k views land on a video with no link
    # It must not claim anything about who did or did not sign up.
    assert "conversion" not in teaser.lower()


def test_teaser_is_dropped_when_the_catalogue_has_no_product_link() -> None:
    assert teaser_sentence(analyse_cta([video("s1", duration=30)])) is None


def test_thin_note_is_absent_when_every_slice_is_sound() -> None:
    assert thin_note([stat("2025", videos=40)]) is None
    assert "2021" in thin_note([stat("2021", videos=3), stat("2025", videos=40)])


def test_slice_label_translates_formats_and_leaves_years_alone() -> None:
    assert slice_label("short") == "Shorts"
    assert slice_label("2024") == "2024"
