"""Tests for catalogue_movement (Phase 16 / W3)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.skills.catalogue_movement import (
    AGE_BUCKET_OLDEST,
    MovementError,
    VideoSnapshotPair,
    analyse_movement,
)

START = date(2026, 8, 20)
END = date(2026, 8, 21)


def _video(
    vid: str,
    *,
    duration: int = 600,
    published: date = date(2026, 1, 1),
    start: int = 1_000,
    end: int = 1_000,
    topic: str | None = "Bourse",
    hook: str | None = "Question",
) -> VideoSnapshotPair:
    return VideoSnapshotPair(
        youtube_video_id=vid,
        title=f"Vidéo {vid}",
        published_at=datetime(published.year, published.month, published.day, tzinfo=UTC),
        duration_seconds=duration,
        topic=topic,
        hook_type=hook,
        views_start=start,
        views_end=end,
    )


def _catalogue(longs: int, shorts: int, *, long_delta: int, short_delta: int):
    rows = [
        _video(f"L{i}", duration=600, start=10_000, end=10_000 + long_delta) for i in range(longs)
    ]
    rows += [
        _video(f"S{i}", duration=45, start=50_000, end=50_000 + short_delta) for i in range(shorts)
    ]
    return rows


def test_format_share_of_movement_can_contradict_share_of_catalogue() -> None:
    """
    The finding this skill exists to express: a format can hold most of the catalogue
    by count and almost none of the movement. Measured on the real Finary catalogue
    between 2026-08-20 and 08-21 — Shorts were 52.3 % of videos and 1.8 % of the
    day's view movement.
    """
    report = analyse_movement(
        _catalogue(48, 52, long_delta=1_000, short_delta=10),
        period_start=START,
        period_end=END,
    )

    by_format = {s.dimension_value: s for s in report.by_format}
    assert by_format["Short"].share_of_catalogue == pytest.approx(0.52)
    assert by_format["Long"].share_of_catalogue == pytest.approx(0.48)
    # 48 × 1000 = 48 000 vs 52 × 10 = 520
    assert by_format["Long"].share_of_movement == pytest.approx(48_000 / 48_520)
    assert by_format["Short"].share_of_movement == pytest.approx(520 / 48_520)


def test_short_threshold_is_sixty_seconds_inclusive() -> None:
    rows = [_video(f"a{i}", duration=60) for i in range(5)]
    rows += [_video(f"b{i}", duration=61) for i in range(5)]
    report = analyse_movement(rows, period_start=START, period_end=END)
    assert {s.dimension_value for s in report.by_format} == {"Short", "Long"}


def test_resolution_is_reported_not_assumed() -> None:
    """
    One day of separation is an observation, not a trend. The consumer cannot tell
    the difference unless the report says so, so `resolution_days` is a first-class
    field and a single day is explicitly flagged.
    """
    report = analyse_movement(
        _catalogue(5, 5, long_delta=1, short_delta=1), period_start=START, period_end=END
    )
    assert report.coverage.resolution_days == 1
    assert report.coverage.is_single_day is True

    weekly = analyse_movement(
        _catalogue(5, 5, long_delta=1, short_delta=1),
        period_start=date(2026, 8, 14),
        period_end=date(2026, 8, 21),
    )
    assert weekly.coverage.resolution_days == 7
    assert weekly.coverage.is_single_day is False


def test_counters_that_go_backwards_are_kept_signed() -> None:
    """
    YouTube revises view counts downward (spam sweeps). Clamping at zero would
    silently inflate the total and make the shares wrong; the honest move is to carry
    the negative and let it net out.
    """
    rows = [_video(f"up{i}", start=100, end=200) for i in range(5)]
    rows += [_video(f"down{i}", start=500, end=400, duration=30) for i in range(5)]
    report = analyse_movement(rows, period_start=START, period_end=END)

    assert report.coverage.total_delta_views == 5 * 100 - 5 * 100 == 0
    assert report.coverage.videos_moved == 5
    by_format = {s.dimension_value: s for s in report.by_format}
    assert by_format["Short"].delta_views == -500


def test_zero_total_movement_leaves_share_undefined_not_zero() -> None:
    """A 0 % share and an unmeasurable share are different statements."""
    rows = [_video(f"f{i}", start=100, end=100) for i in range(6)]
    report = analyse_movement(rows, period_start=START, period_end=END)
    assert report.coverage.total_delta_views == 0
    assert all(s.share_of_movement is None for s in report.by_format)


def test_thin_dimension_values_are_omitted() -> None:
    rows = [_video(f"big{i}", topic="Bourse") for i in range(8)]
    rows += [_video(f"tiny{i}", topic="Crypto") for i in range(3)]
    report = analyse_movement(rows, period_start=START, period_end=END)
    assert {s.dimension_value for s in report.by_topic} == {"Bourse"}


def test_unclassified_videos_do_not_form_a_bucket() -> None:
    """A missing label is not a topic called None."""
    rows = [_video(f"k{i}", topic=None, hook=None) for i in range(6)]
    report = analyse_movement(rows, period_start=START, period_end=END)
    assert report.by_topic == []
    assert report.by_hook == []
    # Format never depends on classification, so it still reports.
    assert report.by_format


def test_newest_age_bucket_survives_the_small_cohort_threshold() -> None:
    """
    A channel publishing twice a week can never put five videos in "last 7 days", so
    applying the topic threshold to publication age would discard the one bucket an
    editorial meeting is about — and silently, since the remaining shares still look
    like a complete table.

    Measured on the real catalogue: 2 videos published that week carried 18.8 % of the
    day's movement, and the age shares summed to 81.2 % without saying so.
    """
    rows = [_video(f"new{i}", published=date(2026, 8, 19), start=0, end=10_000) for i in range(2)]
    rows += [_video(f"old{i}", published=date(2024, 1, 1), start=0, end=1_000) for i in range(20)]

    report = analyse_movement(rows, period_start=START, period_end=END)

    ages = {s.dimension_value: s for s in report.by_publication_age}
    assert "7 derniers jours" in ages
    assert ages["7 derniers jours"].videos == 2
    total_share = sum(s.share_of_movement for s in report.by_publication_age)
    assert total_share == pytest.approx(1.0)


def test_dimensions_that_drop_videos_say_so() -> None:
    """
    Topic and hook keep the threshold, so they *will* omit videos. The reader has to
    be able to tell "these shares sum to 81 %" from "these are all the shares" —
    same discipline as `CohortCoverage` in public_signal_analysis.
    """
    rows = [_video(f"big{i}", topic="Bourse") for i in range(8)]
    rows += [_video(f"tiny{i}", topic="Crypto", start=0, end=500) for i in range(3)]
    rows += [_video(f"none{i}", topic=None, start=0, end=100) for i in range(2)]

    report = analyse_movement(rows, period_start=START, period_end=END)

    topic_omission = next(o for o in report.omissions if o.dimension == "topic")
    assert topic_omission.videos_omitted == 5  # 3 thin + 2 unclassified
    assert topic_omission.delta_views_omitted == 3 * 500 + 2 * 100
    assert topic_omission.reason

    # Format and age are censuses — they omit nothing and report no omission.
    assert not [o for o in report.omissions if o.dimension in ("format", "publication_age")]


def test_publication_age_is_ordinal_not_ranked_by_size() -> None:
    rows = [_video(f"new{i}", published=date(2026, 8, 18)) for i in range(5)]
    rows += [_video(f"mid{i}", published=date(2026, 8, 1)) for i in range(5)]
    rows += [_video(f"old{i}", published=date(2024, 1, 1), start=1, end=99_999) for i in range(5)]
    report = analyse_movement(rows, period_start=START, period_end=END)

    labels = [s.dimension_value for s in report.by_publication_age]
    assert labels == ["7 derniers jours", "8 à 30 jours", AGE_BUCKET_OLDEST]


def test_top_movers_are_ranked_by_delta_not_by_total_views() -> None:
    rows = [_video(f"f{i}") for i in range(5)]
    rows.append(_video("huge_but_flat", start=5_000_000, end=5_000_000))
    rows.append(_video("small_but_moving", start=10, end=9_000))
    report = analyse_movement(rows, period_start=START, period_end=END)
    assert report.top_movers[0].youtube_video_id == "small_but_moving"


def test_empty_input_is_an_error() -> None:
    with pytest.raises(MovementError):
        analyse_movement([], period_start=START, period_end=END)


def test_inverted_period_is_an_error() -> None:
    with pytest.raises(MovementError):
        analyse_movement(
            _catalogue(5, 5, long_delta=1, short_delta=1), period_start=END, period_end=START
        )


def test_analysis_is_pure() -> None:
    rows = _catalogue(6, 6, long_delta=100, short_delta=5)
    once = analyse_movement(rows, period_start=START, period_end=END)
    twice = analyse_movement(rows, period_start=START, period_end=END)
    assert once == twice
