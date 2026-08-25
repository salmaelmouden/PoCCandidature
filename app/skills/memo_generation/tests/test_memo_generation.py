"""Tests for the weekly editorial memo.

The memo is prose, so the assertions worth writing are not about wording. They
are about the three properties that make prose safe to schedule: every figure is
derived, funnel vocabulary stays where it belongs, and a missing input degrades
into a sentence saying so rather than into a confident zero.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.skills.catalogue_movement import (
    MovementCoverage,
    MovementReport,
    MovementStat,
    TopMover,
)
from app.skills.memo_generation import (
    FUNNEL_VOCABULARY,
    LIMITS_SECTION_KEY,
    MemoCandidate,
    MemoError,
    MemoInput,
    funnel_vocabulary_leaks,
    generate_editorial_memo,
    memo_filename,
    undeclared_figures,
)
from app.skills.public_signal_analysis import (
    CohortCoverage,
    DimensionStat,
    PublicSignalReport,
)


def stat(
    value: str, *, videos: int = 20, reach: float = 1.0, engagement: float = 0.02
) -> DimensionStat:
    return DimensionStat(
        value=value,
        videos=videos,
        median_reach_index=reach,
        median_engagement_rate=engagement,
        total_views=100_000,
        share_of_catalogue=0.25,
    )


def report(**overrides) -> PublicSignalReport:
    base = {
        "period_start": datetime(2021, 1, 1, tzinfo=UTC),
        "period_end": datetime(2026, 8, 1, tzinfo=UTC),
        "coverage": CohortCoverage(
            videos_total=952,
            videos_indexed=927,
            videos_excluded=25,
            cohorts_used=30,
            cohorts_dropped=4,
        ),
        "by_format": [
            stat("short", videos=490, reach=1.0, engagement=0.018),
            stat("long", videos=437, reach=1.0, engagement=0.043),
        ],
        "by_topic": [stat("epargne_placements")],
        "by_hook": [stat("question", videos=74)],
        "by_topic_short": [stat("crypto", videos=30)],
        "by_topic_long": [
            stat("portrait_histoire", videos=40, reach=1.60),
            stat("epargne_placements", videos=95, reach=0.70),
        ],
        "by_hook_short": [stat("contrarian", videos=30)],
        "by_hook_long": [
            stat("autorite", videos=62, reach=1.39),
            stat("question", videos=74, reach=0.93),
        ],
    }
    return PublicSignalReport(**{**base, **overrides})


def movement() -> MovementReport:
    return MovementReport(
        coverage=MovementCoverage(
            videos_paired=900,
            videos_moved=640,
            videos_unchanged=260,
            total_delta_views=1_240_000,
            period_start=date(2026, 8, 18),
            period_end=date(2026, 8, 25),
            resolution_days=7,
        ),
        by_format=[],
        by_publication_age=[
            MovementStat(
                dimension_value="7 derniers jours",
                videos=12,
                videos_moved=12,
                delta_views=620_000,
                median_delta_views=42_000,
                share_of_catalogue=0.013,
                share_of_movement=0.5,
            )
        ],
        by_topic=[],
        by_hook=[],
        top_movers=[
            TopMover(
                youtube_video_id="abc123",
                title="Qu'arrive-t-il au Japon ?",
                video_format="Long",
                published_at=date(2026, 2, 10),
                delta_views=120_000,
                views_end=890_000,
            )
        ],
    )


def memo_input(**overrides) -> MemoInput:
    base = {
        "report": report(),
        "movement": movement(),
        "videos": 953,
        "classified": 927,
        "last_checked_at": datetime(2026, 8, 25, 7, 0, tzinfo=UTC),
        "last_changed_at": datetime(2026, 8, 24, 3, 0, tzinfo=UTC),
        "candidates": [
            MemoCandidate(
                title="Cheminot aisé de 48 ans : est-ce trop tard ?",
                reach_index=0.43,
                published_year=2025,
            )
        ],
        "generated_on": date(2026, 8, 25),
    }
    return MemoInput(**{**base, **overrides})


# ---- the post-conditions ----------------------------------------------------


def test_every_printed_figure_is_declared_by_the_composer():
    """The property that makes a scheduled memo safe: no number was typed."""
    memo = generate_editorial_memo(memo_input())

    assert undeclared_figures(memo) == ()


def test_undeclared_figures_catches_a_hand_written_number():
    """The guard has to be able to fail, or it is decoration."""
    memo = generate_editorial_memo(memo_input())
    invented = "88,8"
    assert invented not in set(memo.figures), "pick a value the fixture cannot emit"

    tampered = memo.model_copy(
        update={"markdown": memo.markdown + f"\n\nEnviron {invented} % des vues.\n"}
    )

    assert undeclared_figures(tampered) == (invented,)


def test_funnel_vocabulary_stays_inside_the_limits_section():
    memo = generate_editorial_memo(memo_input())

    assert funnel_vocabulary_leaks(memo) == ()

    limits = next(s for s in memo.sections if s.key == LIMITS_SECTION_KEY)
    body = limits.body.lower()
    assert any(term in body for term in FUNNEL_VOCABULARY), (
        "the limits section must actually name what it disowns"
    )


def test_funnel_vocabulary_leak_is_reported_with_its_section():
    memo = generate_editorial_memo(memo_input())
    leaked = memo.sections[1].model_copy(
        update={"body": "Les inscriptions ont progressé cette semaine."}
    )
    tampered = memo.model_copy(
        update={"sections": [memo.sections[0], leaked, *memo.sections[2:]]}
    )

    leaks = funnel_vocabulary_leaks(tampered)
    assert leaks and leaks[0][0] == leaked.key
    assert leaks[0][1] == "inscription"


# ---- degradation ------------------------------------------------------------


def test_missing_history_is_stated_not_rendered_as_zero():
    memo = generate_editorial_memo(memo_input(movement=None))
    section = next(s for s in memo.sections if s.key == "mouvement")

    assert section.kind == "limit"
    assert "pas encore mesurable" in section.body.lower()
    assert "0" not in section.body
    assert undeclared_figures(memo) == ()


def test_single_day_resolution_is_flagged_as_an_observation():
    tight = movement()
    tight = tight.model_copy(
        update={
            "coverage": tight.coverage.model_copy(
                update={"resolution_days": 1, "period_start": date(2026, 8, 24)}
            )
        }
    )
    memo = generate_editorial_memo(memo_input(movement=tight))
    section = next(s for s in memo.sections if s.key == "mouvement")

    assert "pas une tendance" in section.body


def test_missing_refresh_run_warns_instead_of_implying_freshness():
    memo = generate_editorial_memo(memo_input(last_checked_at=None, last_changed_at=None))
    section = next(s for s in memo.sections if s.key == "fraicheur")

    assert "aucun cycle de rafraîchissement" in section.body.lower()


def test_no_candidates_drops_the_titles_section_rather_than_emptying_it():
    memo = generate_editorial_memo(memo_input(candidates=[]))

    assert all(section.key != "titres" for section in memo.sections)


def test_thin_dimension_rows_are_not_given_a_sentence():
    """A median over four videos must not become 'the best performing topic'."""
    memo = generate_editorial_memo(
        memo_input(
            report=report(
                by_topic_long=[
                    stat("interview", videos=4, reach=9.9),
                    stat("epargne_placements", videos=95, reach=0.70),
                ]
            )
        )
    )
    section = next(s for s in memo.sections if s.key == "editorial")

    assert "Interview" not in section.body
    assert "9,9" not in section.body


def test_empty_catalogue_refuses_to_produce_a_memo():
    empty = report(
        coverage=CohortCoverage(
            videos_total=0,
            videos_indexed=0,
            videos_excluded=0,
            cohorts_used=0,
            cohorts_dropped=0,
        )
    )
    with pytest.raises(MemoError):
        generate_editorial_memo(memo_input(report=empty))


# ---- composition ------------------------------------------------------------


def test_memo_is_french_and_carries_its_provenance():
    memo = generate_editorial_memo(memo_input())

    assert memo.markdown.startswith("# Mémo éditorial — semaine du 25/08/2026")
    assert "sans affiliation" in memo.provenance
    assert "lecture seule" in memo.provenance
    assert memo.provenance in memo.markdown


def test_sections_arrive_in_reading_order_with_freshness_first():
    memo = generate_editorial_memo(memo_input())

    assert [section.key for section in memo.sections] == [
        "fraicheur",
        "mouvement",
        "format",
        "editorial",
        "titres",
        LIMITS_SECTION_KEY,
    ]


def test_filename_is_dated_and_sortable():
    memo = generate_editorial_memo(memo_input())
    name = memo_filename(memo, moment=datetime(2026, 8, 25, 6, 30, tzinfo=UTC))

    assert name == "memo_editorial_20260825T063000Z.md"
