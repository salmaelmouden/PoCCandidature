"""Tests for public_signal_analysis — pure functions, no DB, no network."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.skills.public_signal_analysis import (
    MIN_COHORT_SIZE,
    PublicSignalError,
    PublicVideoSignal,
    VideoFormat,
    aggregate_by,
    analyse_public_signals,
    compute_reach_index,
)


def _video(
    vid: str,
    *,
    views: int,
    year: int = 2025,
    month: int = 1,
    duration: int = 600,
    topic: str = "crypto",
    hook: str = "question",
    likes: int = 0,
    comments: int = 0,
) -> PublicVideoSignal:
    return PublicVideoSignal(
        youtube_video_id=vid,
        title=f"titre {vid}",
        published_at=datetime(year, month, 1, tzinfo=timezone.utc),
        duration_seconds=duration,
        views=views,
        likes=likes,
        comments=comments,
        topic=topic,
        hook_type=hook,
    )


def _cohort(prefix: str, views: list[int], **kwargs) -> list[PublicVideoSignal]:
    return [_video(f"{prefix}{i}", views=v, **kwargs) for i, v in enumerate(views)]


def test_short_threshold_is_inclusive() -> None:
    assert _video("a", views=1, duration=60).video_format is VideoFormat.SHORT
    assert _video("b", views=1, duration=61).video_format is VideoFormat.LONG


def test_cohort_key_splits_by_format_and_quarter() -> None:
    short_q1 = _video("a", views=1, duration=30, month=2)
    long_q1 = _video("b", views=1, duration=600, month=2)
    long_q2 = _video("c", views=1, duration=600, month=5)

    assert short_q1.cohort_key != long_q1.cohort_key
    assert long_q1.cohort_key != long_q2.cohort_key
    assert long_q1.cohort_key == "long:2025Q1"


def test_engagement_rate_handles_zero_views() -> None:
    assert _video("a", views=0, likes=5).engagement_rate == 0.0
    assert _video("b", views=100, likes=2, comments=1).engagement_rate == 0.03


def test_reach_index_is_relative_to_cohort_median() -> None:
    videos = _cohort("v", [100, 100, 100, 100, 200])

    index, coverage = compute_reach_index(videos)

    assert index["v4"] == 2.0  # 200 / median(100)
    assert index["v0"] == 1.0
    assert coverage.videos_indexed == 5
    assert coverage.cohorts_dropped == 0


def test_reach_index_neutralises_channel_growth() -> None:
    """A small-audience-era hit must outrank a large-audience-era average video."""
    early = _cohort("e", [1_000, 1_000, 1_000, 1_000, 5_000], year=2021)
    late = _cohort("l", [50_000, 50_000, 50_000, 50_000, 50_000], year=2026)

    index, _ = compute_reach_index(early + late)

    assert index["e4"] == 5.0
    assert index["l4"] == 1.0
    assert index["e4"] > index["l4"]  # despite 10x fewer raw views


def test_small_cohorts_are_dropped_not_trusted() -> None:
    big = _cohort("b", [100] * MIN_COHORT_SIZE, year=2025)
    tiny = _cohort("t", [999_999] * (MIN_COHORT_SIZE - 1), year=2021)

    index, coverage = compute_reach_index(big + tiny)

    assert all(vid.startswith("b") for vid in index)
    assert coverage.cohorts_dropped == 1
    assert coverage.videos_excluded == MIN_COHORT_SIZE - 1


def test_zero_median_cohort_is_dropped() -> None:
    videos = _cohort("z", [0] * MIN_COHORT_SIZE)

    index, coverage = compute_reach_index(videos)

    assert index == {}
    assert coverage.cohorts_dropped == 1


def test_empty_input_raises() -> None:
    with pytest.raises(PublicSignalError):
        compute_reach_index([])


def test_aggregate_omits_thin_dimension_values() -> None:
    videos = _cohort("a", [100] * 6, topic="crypto") + _cohort(
        "b", [100] * 6, topic="immobilier"
    )
    # Two extra videos on a third topic — below the reporting threshold.
    videos += _cohort("c", [100] * 2, topic="retraite")
    index, _ = compute_reach_index(videos)

    stats = aggregate_by(videos, index, "topic")

    assert {row.value for row in stats} == {"crypto", "immobilier"}


def test_aggregate_only_counts_indexed_videos() -> None:
    big = _cohort("b", [100] * 6, year=2025, topic="crypto")
    tiny = _cohort("t", [100] * 2, year=2021, topic="crypto")

    index, _ = compute_reach_index(big + tiny)
    stats = aggregate_by(big + tiny, index, "topic", min_videos=1)

    assert stats[0].videos == 6


def test_aggregate_sorted_by_reach_index_desc() -> None:
    strong = _cohort("s", [300] * 5, topic="crypto")
    weak = _cohort("w", [100] * 5, topic="immobilier")
    index, _ = compute_reach_index(strong + weak)

    stats = aggregate_by(strong + weak, index, "topic", min_videos=1)

    assert [row.value for row in stats] == ["crypto", "immobilier"]


def test_report_separates_formats() -> None:
    shorts = _cohort("s", [100] * 6, duration=30, topic="crypto")
    longs = _cohort("l", [100] * 6, duration=900, topic="immobilier")

    report = analyse_public_signals(shorts + longs)

    assert {row.value for row in report.by_topic_short} == {"crypto"}
    assert {row.value for row in report.by_topic_long} == {"immobilier"}
    assert {row.value for row in report.by_format} == {"short", "long"}


def test_report_coverage_is_reported_not_hidden() -> None:
    big = _cohort("b", [100] * 6, year=2025)
    tiny = _cohort("t", [100] * 2, year=2021)

    report = analyse_public_signals(big + tiny)

    assert report.coverage.videos_total == 8
    assert report.coverage.videos_indexed == 6
    assert report.coverage.videos_excluded == 2
