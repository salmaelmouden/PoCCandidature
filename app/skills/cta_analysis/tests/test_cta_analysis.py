"""Tests for cta_analysis — pure functions, no DB, no network."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.skills.cta_analysis import (
    FOLD_LINES,
    WRAP_COLUMNS,
    CtaAnalysisError,
    LinkKind,
    TrackingState,
    VideoDescription,
    analyse_cta,
    classify_domain,
    cta_template,
    extract_links,
    normalise_domain,
    pick_primary_domain,
    rendered_line_of,
    tracking_state,
)
from app.skills.public_signal_analysis import VideoFormat


def _video(
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


# ---- extraction -------------------------------------------------------------


def test_extracts_scheme_and_www_links() -> None:
    links = extract_links("Voir https://finary.com/app et www.finary.com/blog")

    assert [link.domain for link in links] == ["finary.com", "finary.com"]
    assert links[0].offset < links[1].offset


def test_bare_domain_is_not_a_link() -> None:
    """YouTube does not linkify it either — counting it would overstate the CTA."""
    assert extract_links("rendez-vous sur finary.com pour tester") == []


def test_trailing_punctuation_is_not_part_of_the_url() -> None:
    (link,) = extract_links("Ici : https://finary.com/app.")

    assert link.url == "https://finary.com/app"


def test_parenthesised_url_keeps_its_closing_bracket_out() -> None:
    (link,) = extract_links("(https://finary.com/app) plus bas")

    assert link.url == "https://finary.com/app"


def test_offset_is_the_position_in_the_source_text() -> None:
    text = "abc https://finary.com"
    (link,) = extract_links(text)

    assert text[link.offset :].startswith("https://finary.com")


# ---- domains ----------------------------------------------------------------


def test_domain_is_normalised() -> None:
    assert normalise_domain("HTTPS://WWW.Finary.com:443/app") == "finary.com"
    assert normalise_domain("www.finary.com/app") == "finary.com"


def test_platform_and_social_domains_are_not_product_candidates() -> None:
    assert classify_domain("youtu.be") is LinkKind.PLATFORM
    assert classify_domain("m.youtube.com") is LinkKind.PLATFORM
    assert classify_domain("instagram.com") is LinkKind.SOCIAL
    assert classify_domain("finary.com") is LinkKind.PRODUCT


# ---- tracking ---------------------------------------------------------------


def test_utm_and_named_parameters_read_as_tracked() -> None:
    assert tracking_state("https://finary.com?utm_source=youtube") is TrackingState.TRACKED
    assert tracking_state("https://finary.com?ref=chaine") is TrackingState.TRACKED


def test_plain_link_reads_as_untracked() -> None:
    assert tracking_state("https://finary.com/app") is TrackingState.UNTRACKED
    assert tracking_state("https://finary.com/app?lang=fr") is TrackingState.UNTRACKED


def test_redirector_is_opaque_rather_than_untracked() -> None:
    """It may append a campaign after the hop — the URL text cannot settle it."""
    assert tracking_state("https://bit.ly/xyz") is TrackingState.OPAQUE
    assert tracking_state("https://go.finary.com/yt") is TrackingState.OPAQUE


# ---- the fold ---------------------------------------------------------------


def test_rendered_line_counts_newlines() -> None:
    text = "l1\nl2\nl3\nhttps://finary.com"

    assert rendered_line_of(text, text.index("https")) == 3


def test_rendered_line_counts_wrapping_not_only_newlines() -> None:
    """A single long paragraph buries a link even without a newline."""
    text = "a" * (WRAP_COLUMNS * 4) + " https://finary.com"

    assert rendered_line_of(text, text.index("https")) == 4


def test_link_at_the_top_is_above_the_fold() -> None:
    assert rendered_line_of("https://finary.com — le reste ensuite", 0) == 0


# ---- CTA wording ------------------------------------------------------------


def test_template_replaces_the_url_so_variants_group() -> None:
    first = cta_template("Essayez Finary : https://finary.com?ref=a", 17)
    second = cta_template("Essayez Finary : https://finary.com?ref=b", 17)

    assert first == second == "Essayez Finary : ‹lien›"


def test_template_is_the_line_not_the_whole_description() -> None:
    text = "intro\nEssayez   Finary : https://finary.com\noutro"

    assert cta_template(text, text.index("https")) == "Essayez Finary : ‹lien›"


# ---- primary domain ---------------------------------------------------------


def test_primary_domain_ignores_platform_and_social_links() -> None:
    videos = [
        _video("a", description="https://instagram.com/x https://youtu.be/y https://finary.com"),
        _video("b", description="https://instagram.com/x https://finary.com"),
        _video("c", description="https://instagram.com/x"),
    ]
    links = {v.youtube_video_id: extract_links(v.description) for v in videos}

    domain, reason = pick_primary_domain(videos, links)

    assert domain == "finary.com"
    assert "2 vidéos sur 3" in reason


def test_primary_domain_counts_videos_not_occurrences() -> None:
    """Ten links in one description must not outweigh two videos linking once."""
    videos = [
        _video("a", description=" ".join(["https://spam.example"] * 10)),
        _video("b", description="https://finary.com"),
        _video("c", description="https://finary.com"),
    ]
    links = {v.youtube_video_id: extract_links(v.description) for v in videos}

    domain, _ = pick_primary_domain(videos, links)

    assert domain == "finary.com"


def test_primary_domain_tie_is_broken_deterministically() -> None:
    videos = [_video("a", description="https://alpha.example https://beta.example")]
    links = {v.youtube_video_id: extract_links(v.description) for v in videos}

    assert pick_primary_domain(videos, links)[0] == "alpha.example"


def test_catalogue_without_product_links_says_so() -> None:
    videos = [_video("a", description="https://youtu.be/x")]
    links = {v.youtube_video_id: extract_links(v.description) for v in videos}

    domain, reason = pick_primary_domain(videos, links)

    assert domain is None
    assert "aucun domaine" in reason


# ---- the report -------------------------------------------------------------


def _catalogue() -> list[VideoDescription]:
    """Two Shorts without an entry point, three long videos with one."""
    return [
        _video("s1", description="", duration=30, views=100_000),
        _video("s2", description="Abonnez-vous !", duration=45, views=200_000),
        _video("l1", description="https://finary.com?utm_source=yt\nle reste", views=10_000),
        _video("l2", description="a" * (WRAP_COLUMNS * 5) + "\nhttps://finary.com", views=20_000),
        _video("l3", description="Essayez : https://finary.com", views=30_000, year=2024),
    ]


def test_empty_input_raises() -> None:
    with pytest.raises(CtaAnalysisError):
        analyse_cta([])


def test_coverage_separates_no_description_from_no_link() -> None:
    report = analyse_cta(_catalogue())

    assert report.coverage.videos_total == 5
    assert report.coverage.described == 4  # s1 has none at all
    assert report.coverage.with_any_link == 3
    assert report.coverage.with_primary == 3
    assert report.coverage.primary_domain == "finary.com"


def test_format_split_isolates_the_shorts_gap() -> None:
    report = analyse_cta(_catalogue())
    by_value = {row.value: row for row in report.by_format}

    assert by_value[VideoFormat.SHORT.value].with_primary == 0
    assert by_value[VideoFormat.SHORT.value].share_with_primary == 0.0
    assert by_value[VideoFormat.LONG.value].share_with_primary == 1.0


def test_above_fold_is_a_share_of_videos_carrying_a_link() -> None:
    report = analyse_cta(_catalogue())
    long_row = next(row for row in report.by_format if row.value == VideoFormat.LONG.value)

    # l2 pushes its link past the fold with a five-line paragraph; l1 and l3 do not.
    assert long_row.above_fold == 2
    assert long_row.share_above_fold == pytest.approx(2 / 3)


def test_view_weighting_reports_audience_not_video_count() -> None:
    report = analyse_cta(_catalogue())

    # 60k views on videos carrying a link, out of 360k in the catalogue.
    assert report.overall.views == 360_000
    assert report.overall.views_with_primary == 60_000
    assert report.overall.view_share_with_primary == pytest.approx(1 / 6)


def test_tracking_states_are_counted_separately() -> None:
    report = analyse_cta(_catalogue())

    assert report.overall.tracked == 1  # only l1 carries utm_source
    assert report.overall.share_tracked == pytest.approx(1 / 3)


def test_ratios_are_zero_rather_than_undefined_on_an_empty_slice() -> None:
    report = analyse_cta([_video("s1", description="", duration=30)])

    assert report.overall.share_with_primary == 0.0
    assert report.overall.share_above_fold == 0.0
    assert report.overall.median_offset is None


def test_year_slices_expose_drift() -> None:
    report = analyse_cta(_catalogue())

    assert [row.value for row in report.by_year] == ["2024", "2025"]


def test_domain_table_keeps_excluded_domains_visible() -> None:
    videos = [_video("a", description="https://instagram.com/x https://finary.com")]

    report = analyse_cta(videos)
    kinds = {row.domain: row.kind for row in report.domains}

    assert kinds["instagram.com"] is LinkKind.SOCIAL
    assert kinds["finary.com"] is LinkKind.PRODUCT


def test_cta_wordings_are_grouped_by_template() -> None:
    videos = [
        _video("a", description="Essayez Finary : https://finary.com?ref=1"),
        _video("b", description="Essayez Finary : https://finary.com?ref=2"),
        _video("c", description="Autre phrase https://finary.com"),
    ]

    report = analyse_cta(videos)

    assert report.cta_lines[0].template == "Essayez Finary : ‹lien›"
    assert report.cta_lines[0].videos == 2


def test_caller_can_pin_the_primary_domain() -> None:
    videos = [_video("a", description="https://finary.com https://autre.example")]

    report = analyse_cta(videos, primary_domain="autre.example")

    assert report.coverage.primary_domain == "autre.example"
    assert report.coverage.primary_domain_reason == "domaine fourni par l'appelant"


def test_subdomain_of_the_primary_domain_counts_as_the_product() -> None:
    videos = [_video("a", description="https://app.finary.com/x"), _video("b", description="https://finary.com")]

    report = analyse_cta(videos, primary_domain="finary.com")

    assert report.coverage.with_primary == 2


def test_fold_threshold_is_the_documented_one() -> None:
    """Guards the constant the page cites: a change must be a decision, not a drift."""
    assert FOLD_LINES == 3
