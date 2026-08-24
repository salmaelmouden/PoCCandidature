"""Dashboard application service — repos + skills, no UI."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db.constants import FUNNEL_STAGES
from app.db.models import Acquisition
from app.db.repositories import AcquisitionRepository
from app.skills.anomaly_detection import detect_traffic_anomalies
from app.skills.anomaly_detection.schemas import AnomalyDetectionResult, TimeSeriesPoint
from app.skills.content_analysis import (
    compare_topics,
    identify_high_reach_low_conversion,
    rank_content,
)
from app.skills.content_analysis.schemas import ContentGapItem, ContentMetrics, ContentValueScore, TopicComparison
from app.skills.funnel_analysis import calculate_funnel, compare_funnel_periods
from app.skills.funnel_analysis.schemas import FunnelPeriodComparison, FunnelResult


@dataclass(frozen=True)
class PeriodWindow:
    start: date
    end: date
    previous_start: date
    previous_end: date
    days: int


@dataclass(frozen=True)
class OverviewSnapshot:
    period: PeriodWindow
    channel: str | None
    current_counts: dict[str, int]
    previous_counts: dict[str, int]
    relative_deltas: dict[str, float | None]
    funnel: FunnelResult
    traffic_anomalies: AnomalyDetectionResult
    dataset_labels: frozenset[str]
    has_synthetic: bool
    #: One entry per funnel stage, ordered by day. A KPI tile is only readable
    #: with its trend beside it, and the shape of the period is not derivable
    #: from two totals — so the service returns it rather than leaving the page
    #: to query the repository itself.
    daily_series: dict[str, list[tuple[date, int]]]


@dataclass(frozen=True)
class ChannelBreakdownRow:
    channel: str
    views: int
    visits: int
    signups: int
    activated_users: int
    premium_users: int
    visit_rate: float
    signup_rate: float
    premium_rate: float


@dataclass(frozen=True)
class AcquisitionSnapshot:
    period: PeriodWindow
    rows: list[ChannelBreakdownRow]
    dataset_labels: frozenset[str]
    has_synthetic: bool


@dataclass(frozen=True)
class ContentSnapshot:
    period: PeriodWindow
    channel: str | None
    ranked: list[ContentValueScore]
    topics: list[TopicComparison]
    reach_conversion_gaps: list[ContentGapItem]
    dataset_labels: frozenset[str]
    has_synthetic: bool


@dataclass(frozen=True)
class FunnelSnapshot:
    period: PeriodWindow
    channel: str | None
    comparison: FunnelPeriodComparison
    dataset_labels: frozenset[str]
    has_synthetic: bool


def resolve_period(days: int, *, as_of: date | None = None) -> PeriodWindow:
    if days < 1:
        raise ValueError("days must be >= 1")
    end = as_of or date.today()
    start = end - timedelta(days=days - 1)
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)
    return PeriodWindow(
        start=start,
        end=end,
        previous_start=previous_start,
        previous_end=previous_end,
        days=days,
    )


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _labels_from_rows(rows: list[Acquisition]) -> tuple[frozenset[str], bool]:
    labels = frozenset(row.dataset_label for row in rows)
    has_synthetic = any(row.is_synthetic for row in rows)
    return labels, has_synthetic


def get_overview(
    session: Session,
    *,
    days: int = 30,
    channel: str | None = None,
    as_of: date | None = None,
) -> OverviewSnapshot:
    period = resolve_period(days, as_of=as_of)
    repo = AcquisitionRepository(session)
    current = repo.sum_funnel(start=period.start, end=period.end, channel=channel)
    previous = repo.sum_funnel(
        start=period.previous_start, end=period.previous_end, channel=channel
    )
    relative: dict[str, float | None] = {}
    for stage in FUNNEL_STAGES:
        prev = previous[stage]
        relative[stage] = ((current[stage] - prev) / prev) if prev > 0 else None

    daily_series = {
        stage: repo.daily_metric_series(
            start=period.start, end=period.end, metric=stage, channel=channel
        )
        for stage in FUNNEL_STAGES
    }
    anomalies = detect_traffic_anomalies(
        [
            TimeSeriesPoint(label=day.isoformat(), value=float(value))
            for day, value in daily_series["views"]
        ]
    )
    rows = list(repo.list_between(start=period.start, end=period.end, channel=channel))
    labels, has_synthetic = _labels_from_rows(rows)
    return OverviewSnapshot(
        period=period,
        channel=channel,
        current_counts=current,
        previous_counts=previous,
        relative_deltas=relative,
        funnel=calculate_funnel(current),
        traffic_anomalies=anomalies,
        dataset_labels=labels,
        has_synthetic=has_synthetic,
        daily_series=daily_series,
    )


def get_acquisition(
    session: Session,
    *,
    days: int = 30,
    as_of: date | None = None,
) -> AcquisitionSnapshot:
    period = resolve_period(days, as_of=as_of)
    repo = AcquisitionRepository(session)
    rows = list(repo.list_between(start=period.start, end=period.end))
    buckets: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "views": 0,
            "visits": 0,
            "signups": 0,
            "activated_users": 0,
            "premium_users": 0,
        }
    )
    for row in rows:
        bucket = buckets[row.channel]
        bucket["views"] += row.views
        bucket["visits"] += row.visits
        bucket["signups"] += row.signups
        bucket["activated_users"] += row.activated_users
        bucket["premium_users"] += row.premium_users

    breakdown: list[ChannelBreakdownRow] = []
    for channel_name, counts in buckets.items():
        breakdown.append(
            ChannelBreakdownRow(
                channel=channel_name,
                views=counts["views"],
                visits=counts["visits"],
                signups=counts["signups"],
                activated_users=counts["activated_users"],
                premium_users=counts["premium_users"],
                visit_rate=_safe_rate(counts["visits"], counts["views"]),
                signup_rate=_safe_rate(counts["signups"], counts["visits"]),
                premium_rate=_safe_rate(counts["premium_users"], counts["activated_users"]),
            )
        )
    breakdown.sort(key=lambda item: (-item.signups, item.channel))
    labels, has_synthetic = _labels_from_rows(rows)
    return AcquisitionSnapshot(
        period=period,
        rows=breakdown,
        dataset_labels=labels,
        has_synthetic=has_synthetic,
    )


def _content_units_from_acquisition(rows: list[Acquisition]) -> list[ContentMetrics]:
    buckets: dict[str, dict[str, object]] = {}
    for row in rows:
        if row.video_id is not None:
            key = f"video:{row.video_id}"
            title = f"Video {str(row.video_id)[:8]}"
        else:
            key = f"topic:{row.topic}:{row.channel}"
            title = f"{row.topic} ({row.channel})"
        existing = buckets.get(key)
        if existing is None:
            buckets[key] = {
                "content_id": key,
                "title": title,
                "topic": row.topic,
                "reach": row.views,
                "engagement": 0,
                "signups": row.signups,
                "premium_users": row.premium_users,
            }
        else:
            existing["reach"] = int(existing["reach"]) + row.views
            existing["signups"] = int(existing["signups"]) + row.signups
            existing["premium_users"] = int(existing["premium_users"]) + row.premium_users
    return [ContentMetrics.model_validate(item) for item in buckets.values()]


def get_content(
    session: Session,
    *,
    days: int = 30,
    channel: str | None = None,
    top_n: int = 15,
    as_of: date | None = None,
) -> ContentSnapshot:
    period = resolve_period(days, as_of=as_of)
    repo = AcquisitionRepository(session)
    rows = list(repo.list_between(start=period.start, end=period.end, channel=channel))
    units = _content_units_from_acquisition(rows)
    ranked = rank_content(units, limit=top_n)
    topics = compare_topics(units)
    gaps = identify_high_reach_low_conversion(units)
    labels, has_synthetic = _labels_from_rows(rows)
    return ContentSnapshot(
        period=period,
        channel=channel,
        ranked=ranked,
        topics=topics,
        reach_conversion_gaps=gaps,
        dataset_labels=labels,
        has_synthetic=has_synthetic,
    )


def get_funnel(
    session: Session,
    *,
    days: int = 30,
    channel: str | None = None,
    as_of: date | None = None,
) -> FunnelSnapshot:
    period = resolve_period(days, as_of=as_of)
    repo = AcquisitionRepository(session)
    current = repo.sum_funnel(start=period.start, end=period.end, channel=channel)
    previous = repo.sum_funnel(
        start=period.previous_start, end=period.previous_end, channel=channel
    )
    rows = list(repo.list_between(start=period.start, end=period.end, channel=channel))
    labels, has_synthetic = _labels_from_rows(rows)
    return FunnelSnapshot(
        period=period,
        channel=channel,
        comparison=compare_funnel_periods(current, previous),
        dataset_labels=labels,
        has_synthetic=has_synthetic,
    )
