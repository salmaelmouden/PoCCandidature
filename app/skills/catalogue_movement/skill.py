"""
catalogue_movement — what is still accumulating views, and what has stopped.

`public_signal_analysis` measures a **stock**: cumulative counters at one instant,
normalised against comparable cohorts. Its contract is explicit that it cannot do more
— "There is no history. The API returns counters as of the fetch, so a single ingest
yields one point per video."

Phase 14 put the ingest on a schedule, so there are now several dated snapshots per
video. That makes a different quantity measurable: the **flow**. Which formats, topics
and vintages are still earning views today, as opposed to having earned them once.

The two disagree, and the disagreement is the point. A format can hold half the
catalogue by count and contribute almost nothing to this week's movement.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date
from statistics import median

from app.skills.catalogue_movement.schemas import (
    AGE_BUCKET_OLDEST,
    AGE_BUCKETS,
    MIN_DIMENSION_VIDEOS,
    DimensionCoverage,
    MovementCoverage,
    MovementError,
    MovementReport,
    MovementStat,
    TopMover,
    VideoSnapshotPair,
)


def analyse_movement(
    videos: Iterable[VideoSnapshotPair],
    *,
    period_start: date,
    period_end: date,
    min_dimension_videos: int = MIN_DIMENSION_VIDEOS,
    top_movers: int = 10,
) -> MovementReport:
    """Aggregate per-video view deltas across editorial dimensions.

    Deterministic and pure: no I/O, no clock, no randomness.
    """
    rows = list(videos)
    if not rows:
        raise MovementError("no paired snapshots to compare")
    if period_end < period_start:
        raise MovementError(f"period_end {period_end} precedes period_start {period_start}")

    total_delta = sum(row.delta_views for row in rows)
    coverage = MovementCoverage(
        videos_paired=len(rows),
        videos_moved=sum(1 for row in rows if row.delta_views > 0),
        videos_unchanged=sum(1 for row in rows if row.delta_views == 0),
        total_delta_views=total_delta,
        period_start=period_start,
        period_end=period_end,
        resolution_days=(period_end - period_start).days,
    )

    omissions: list[DimensionCoverage] = []

    def stats(
        name: str,
        key: Callable[[VideoSnapshotPair], str | None],
        *,
        threshold: int,
        reason: str,
    ) -> list[MovementStat]:
        kept, dropped = _aggregate(rows, key, total_delta, threshold)
        if dropped:
            omissions.append(
                DimensionCoverage(
                    dimension=name,
                    videos_omitted=len(dropped),
                    delta_views_omitted=sum(row.delta_views for row in dropped),
                    reason=reason,
                )
            )
        return kept

    # Publication age is a census, not a sample: the buckets are fixed in advance and
    # every video lands in exactly one. The small-cohort threshold exists to stop
    # unstable medians on data-derived categories like topic — applying it here would
    # discard the newest bucket, which is both the smallest by construction (a channel
    # publishing twice a week can never fill it) and the one an editorial meeting is
    # actually about.
    by_age = _ordered_ages(
        stats(
            "publication_age",
            lambda r: _age_bucket(r.published_at.date(), period_end),
            threshold=1,
            reason="",
        )
    )

    return MovementReport(
        coverage=coverage,
        by_format=stats("format", lambda r: r.video_format, threshold=1, reason=""),
        by_publication_age=by_age,
        by_topic=stats(
            "topic",
            lambda r: r.topic,
            threshold=min_dimension_videos,
            reason=(
                f"non classées, ou moins de {min_dimension_videos} vidéos "
                "pour ce sujet"
            ),
        ),
        by_hook=stats(
            "hook_type",
            lambda r: r.hook_type,
            threshold=min_dimension_videos,
            reason=(
                f"non classées, ou moins de {min_dimension_videos} vidéos "
                "pour ce type d'accroche"
            ),
        ),
        top_movers=[
            TopMover(
                youtube_video_id=row.youtube_video_id,
                title=row.title,
                video_format=row.video_format,
                published_at=row.published_at.date(),
                delta_views=row.delta_views,
                views_end=row.views_end,
                topic=row.topic,
            )
            for row in sorted(rows, key=lambda r: -r.delta_views)[:top_movers]
        ],
        omissions=omissions,
    )


def _age_bucket(published: date, as_of: date) -> str:
    age_days = (as_of - published).days
    for label, upper in AGE_BUCKETS:
        if age_days <= upper:
            return label
    return AGE_BUCKET_OLDEST


def _ordered_ages(stats: list[MovementStat]) -> list[MovementStat]:
    """Age is ordinal — report it youngest-first rather than by magnitude."""
    order = [label for label, _ in AGE_BUCKETS] + [AGE_BUCKET_OLDEST]
    return sorted(stats, key=lambda s: order.index(s.dimension_value))


def _aggregate(
    rows: list[VideoSnapshotPair],
    key: Callable[[VideoSnapshotPair], str | None],
    total_delta: int,
    min_dimension_videos: int,
) -> tuple[list[MovementStat], list[VideoSnapshotPair]]:
    """Returns the reportable stats and the rows that did not make it into any of them."""
    grouped: dict[str, list[VideoSnapshotPair]] = {}
    dropped: list[VideoSnapshotPair] = []
    for row in rows:
        value = key(row)
        if value is None:
            dropped.append(row)  # unlabelled is not a category
            continue
        grouped.setdefault(value, []).append(row)

    out: list[MovementStat] = []
    for value, group in grouped.items():
        if len(group) < min_dimension_videos:
            dropped.extend(group)
            continue
        deltas = [row.delta_views for row in group]
        group_delta = sum(deltas)
        out.append(
            MovementStat(
                dimension_value=value,
                videos=len(group),
                videos_moved=sum(1 for d in deltas if d > 0),
                delta_views=group_delta,
                median_delta_views=float(median(deltas)),
                share_of_catalogue=len(group) / len(rows),
                # Undefined rather than zero when nothing moved: a 0 % share and an
                # unmeasurable one are different statements.
                share_of_movement=(group_delta / total_delta if total_delta else None),
            )
        )
    return sorted(out, key=lambda s: -s.delta_views), dropped


__all__ = ["analyse_movement"]
