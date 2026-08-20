"""Typed tools for the data analyst — wrap services/skills, never SQL."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.services.dashboard import get_acquisition, get_content, get_funnel, get_overview


def tool_get_overview(
    session: Session,
    *,
    days: int,
    channel: str | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    snap = get_overview(session, days=days, channel=channel, as_of=as_of)
    return {
        "period_start": snap.period.start.isoformat(),
        "period_end": snap.period.end.isoformat(),
        "previous_start": snap.period.previous_start.isoformat(),
        "previous_end": snap.period.previous_end.isoformat(),
        "channel": snap.channel,
        "current_counts": snap.current_counts,
        "previous_counts": snap.previous_counts,
        "relative_deltas": snap.relative_deltas,
        "bottleneck_from": snap.funnel.bottleneck_from_stage,
        "bottleneck_to": snap.funnel.bottleneck_to_stage,
        "bottleneck_dropoff_rate": snap.funnel.bottleneck_dropoff_rate,
        "anomaly_count": len(snap.traffic_anomalies.anomalies),
        "anomaly_labels": [a.label for a in snap.traffic_anomalies.anomalies[:10]],
        "dataset_labels": sorted(snap.dataset_labels),
        "has_synthetic": snap.has_synthetic,
    }


def tool_get_funnel_compare(
    session: Session,
    *,
    days: int,
    channel: str | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    snap = get_funnel(session, days=days, channel=channel, as_of=as_of)
    current = snap.comparison.current
    previous = snap.comparison.previous
    return {
        "period_start": snap.period.start.isoformat(),
        "period_end": snap.period.end.isoformat(),
        "channel": snap.channel,
        "current_counts": current.counts.model_dump(),
        "previous_counts": previous.counts.model_dump(),
        "conversion_rate_deltas": snap.comparison.conversion_rate_deltas,
        "current_bottleneck": {
            "from": current.bottleneck_from_stage,
            "to": current.bottleneck_to_stage,
            "dropoff_rate": current.bottleneck_dropoff_rate,
        },
        "absolute_deltas": snap.comparison.absolute_deltas,
        "dataset_labels": sorted(snap.dataset_labels),
        "has_synthetic": snap.has_synthetic,
    }


def tool_get_acquisition_by_channel(
    session: Session,
    *,
    days: int,
    as_of: date | None = None,
) -> dict[str, Any]:
    snap = get_acquisition(session, days=days, as_of=as_of)
    rows = [
        {
            "channel": row.channel,
            "views": row.views,
            "visits": row.visits,
            "signups": row.signups,
            "activated_users": row.activated_users,
            "premium_users": row.premium_users,
            "premium_rate": row.premium_rate,
            "signup_rate": row.signup_rate,
        }
        for row in snap.rows
    ]
    return {
        "period_start": snap.period.start.isoformat(),
        "period_end": snap.period.end.isoformat(),
        "channels": rows,
        "dataset_labels": sorted(snap.dataset_labels),
        "has_synthetic": snap.has_synthetic,
    }


def tool_get_content_gaps(
    session: Session,
    *,
    days: int,
    channel: str | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    snap = get_content(session, days=days, channel=channel, as_of=as_of, top_n=10)
    return {
        "period_start": snap.period.start.isoformat(),
        "period_end": snap.period.end.isoformat(),
        "channel": snap.channel,
        "top_content": [
            {
                "content_id": row.content_id,
                "title": row.title,
                "topic": row.topic,
                "score": row.score,
                "reach": row.reach,
                "premium_rate": row.premium_rate,
            }
            for row in snap.ranked[:5]
        ],
        "reach_conversion_gaps": [
            {
                "content_id": g.content_id,
                "title": g.title,
                "topic": g.topic,
                "reach": g.reach,
                "premium_rate": g.premium_rate,
                "reason": g.reason,
            }
            for g in snap.reach_conversion_gaps[:8]
        ],
        "topics": [
            {
                "topic": t.topic,
                "reach": t.total_reach,
                "premium_users": t.total_premium_users,
                "premium_rate": t.premium_rate,
                "avg_cvs": t.avg_content_value_score,
            }
            for t in snap.topics[:8]
        ],
        "dataset_labels": sorted(snap.dataset_labels),
        "has_synthetic": snap.has_synthetic,
    }
