"""Normalize and validate raw YouTube API video payloads."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.db.constants import Topic
from app.skills.youtube_ingestion.schemas import NormalizedVideo, YOUTUBE_DATASET_LABEL

_ISO_DURATION = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)

_TOPIC_KEYWORDS: tuple[tuple[Topic, tuple[str, ...]], ...] = (
    (Topic.ETFS, ("etf", "etfs", "index fund")),
    (Topic.STOCKS, ("stock", "stocks", "equity", "equities", "bourse")),
    (Topic.CRYPTO, ("crypto", "bitcoin", "ethereum", "btc", "eth")),
    (Topic.REAL_ESTATE, ("real estate", "immobilier", "mortgage", "property")),
    (Topic.BUDGETING, ("budget", "budgeting", "épargne", "saving", "savings")),
    (Topic.PERSONAL_FINANCE, ("finance", "money", "invest", "wealth", "retraite")),
)


class TransformError(ValueError):
    """Raised when a video payload cannot be normalized."""


def parse_iso8601_duration(value: str) -> int:
    """Parse YouTube ISO-8601 duration (e.g. PT1H2M3S) to seconds."""
    match = _ISO_DURATION.match(value or "")
    if not match:
        raise TransformError(f"Invalid duration: {value!r}")
    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def infer_topic(title: str, description: str) -> str:
    """Keyword heuristic topic tag — deterministic, not an LLM."""
    haystack = f"{title}\n{description}".lower()
    for topic, keywords in _TOPIC_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return topic.value
    return Topic.PERSONAL_FINANCE.value


def normalize_video_payload(item: dict[str, Any]) -> NormalizedVideo:
    video_id = item.get("id")
    snippet = item.get("snippet") or {}
    details = item.get("contentDetails") or {}
    stats = item.get("statistics") or {}

    if not video_id or not isinstance(video_id, str):
        raise TransformError("Missing video id")
    title = snippet.get("title")
    if not title:
        raise TransformError(f"Missing title for video {video_id}")
    published_raw = snippet.get("publishedAt")
    if not published_raw:
        raise TransformError(f"Missing publishedAt for video {video_id}")
    duration_raw = details.get("duration")
    if not duration_raw:
        raise TransformError(f"Missing duration for video {video_id}")

    published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    description = snippet.get("description") or ""
    channel_id = snippet.get("channelId") or ""
    channel_title = snippet.get("channelTitle") or ""
    if not channel_id:
        raise TransformError(f"Missing channelId for video {video_id}")

    return NormalizedVideo(
        youtube_video_id=video_id,
        title=title,
        description=description,
        published_at=published_at,
        duration_seconds=parse_iso8601_duration(duration_raw),
        channel_id=channel_id,
        channel_title=channel_title,
        topic=infer_topic(title, description),
        views=int(stats.get("viewCount") or 0),
        likes=int(stats.get("likeCount") or 0),
        comments=int(stats.get("commentCount") or 0),
        is_synthetic=False,
        dataset_label=YOUTUBE_DATASET_LABEL,
    )
