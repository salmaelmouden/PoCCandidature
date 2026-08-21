"""Deterministic analysis of publicly observable video signals."""

from __future__ import annotations

from collections import defaultdict
from statistics import median

from app.skills.public_signal_analysis.schemas import (
    MIN_COHORT_SIZE,
    CohortCoverage,
    DimensionStat,
    PublicSignalReport,
    PublicVideoSignal,
    VideoFormat,
)


class PublicSignalError(ValueError):
    """Raised when the input set cannot be analysed."""


def compute_reach_index(
    videos: list[PublicVideoSignal],
) -> tuple[dict[str, float], CohortCoverage]:
    """
    Relative reach of each video against its own cohort.

    A video's raw view count is not comparable across the catalogue: the channel
    grew roughly 10x between 2021 and 2026, so a 2021 video with five years of
    accumulation still trails a 2026 video with eight months. Comparing raw views
    by topic would measure *when* a subject was covered, not how it performed.

    The index divides each video's views by the median views of videos published
    in the same quarter and the same format, so 1.0 means "typical for its cohort".
    Cohorts below MIN_COHORT_SIZE are dropped rather than trusted.
    """
    if not videos:
        raise PublicSignalError("No videos to analyse")

    cohorts: dict[str, list[PublicVideoSignal]] = defaultdict(list)
    for video in videos:
        cohorts[video.cohort_key].append(video)

    index: dict[str, float] = {}
    cohorts_used = 0
    cohorts_dropped = 0
    for members in cohorts.values():
        if len(members) < MIN_COHORT_SIZE:
            cohorts_dropped += 1
            continue
        cohort_median = median(member.views for member in members)
        if cohort_median <= 0:
            cohorts_dropped += 1
            continue
        cohorts_used += 1
        for member in members:
            index[member.youtube_video_id] = member.views / cohort_median

    coverage = CohortCoverage(
        videos_total=len(videos),
        videos_indexed=len(index),
        videos_excluded=len(videos) - len(index),
        cohorts_used=cohorts_used,
        cohorts_dropped=cohorts_dropped,
    )
    return index, coverage


def aggregate_by(
    videos: list[PublicVideoSignal],
    index: dict[str, float],
    key: str,
    *,
    min_videos: int = MIN_COHORT_SIZE,
) -> list[DimensionStat]:
    """
    Aggregate indexed videos by an attribute name (`topic`, `hook_type`, ...).

    Only videos carrying a reach index are counted, so every row is comparable.
    Values with fewer than `min_videos` are omitted — a median over three videos
    is not a finding.
    """
    indexed = [video for video in videos if video.youtube_video_id in index]
    if not indexed:
        return []
    total_indexed = len(indexed)

    grouped: dict[str, list[PublicVideoSignal]] = defaultdict(list)
    for video in indexed:
        grouped[str(getattr(video, key))].append(video)

    stats = [
        DimensionStat(
            value=value,
            videos=len(members),
            median_reach_index=round(
                median(index[member.youtube_video_id] for member in members), 4
            ),
            median_engagement_rate=round(
                median(member.engagement_rate for member in members), 5
            ),
            total_views=sum(member.views for member in members),
            share_of_catalogue=round(len(members) / total_indexed, 4),
        )
        for value, members in grouped.items()
        if len(members) >= min_videos
    ]
    return sorted(stats, key=lambda row: row.median_reach_index, reverse=True)


def analyse_public_signals(videos: list[PublicVideoSignal]) -> PublicSignalReport:
    """Build the full evidence table. Facts only — no interpretation, by design."""
    index, coverage = compute_reach_index(videos)
    shorts = [video for video in videos if video.video_format is VideoFormat.SHORT]
    longs = [video for video in videos if video.video_format is VideoFormat.LONG]

    return PublicSignalReport(
        period_start=min(video.published_at for video in videos),
        period_end=max(video.published_at for video in videos),
        coverage=coverage,
        by_format=aggregate_by(videos, index, "video_format"),
        by_topic=aggregate_by(videos, index, "topic"),
        by_hook=aggregate_by(videos, index, "hook_type"),
        by_topic_short=aggregate_by(shorts, index, "topic"),
        by_topic_long=aggregate_by(longs, index, "topic"),
        by_hook_short=aggregate_by(shorts, index, "hook_type"),
        by_hook_long=aggregate_by(longs, index, "hook_type"),
    )
