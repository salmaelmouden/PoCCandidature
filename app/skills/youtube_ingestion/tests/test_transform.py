"""Tests for YouTube transform helpers."""

from __future__ import annotations

import pytest

from app.skills.youtube_ingestion.transform import (
    TransformError,
    infer_topic,
    normalize_video_payload,
    parse_iso8601_duration,
)


def test_parse_iso8601_duration() -> None:
    assert parse_iso8601_duration("PT15S") == 15
    assert parse_iso8601_duration("PT1M30S") == 90
    assert parse_iso8601_duration("PT1H2M3S") == 3723
    assert parse_iso8601_duration("P1DT1H") == 90000


def test_parse_iso8601_duration_invalid() -> None:
    with pytest.raises(TransformError):
        parse_iso8601_duration("not-a-duration")


def test_infer_topic_keywords() -> None:
    assert infer_topic("Best ETFs in 2026", "") == "ETFs"
    assert infer_topic("Bitcoin explained", "") == "Crypto"
    assert infer_topic("Random vlog", "hello") == "Personal Finance"


def test_normalize_video_payload_happy_path() -> None:
    item = {
        "id": "abc123",
        "snippet": {
            "title": "ETF portfolio basics",
            "description": "How to invest with ETFs",
            "publishedAt": "2024-01-15T12:00:00Z",
            "channelId": "UCtest",
            "channelTitle": "Demo Channel",
        },
        "contentDetails": {"duration": "PT10M5S"},
        "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "7"},
    }
    video = normalize_video_payload(item)
    assert video.youtube_video_id == "abc123"
    assert video.duration_seconds == 605
    assert video.views == 1000
    assert video.topic == "ETFs"
    assert video.is_synthetic is False
    assert video.dataset_label == "youtube_api"


def test_normalize_video_payload_missing_title() -> None:
    with pytest.raises(TransformError):
        normalize_video_payload(
            {
                "id": "x",
                "snippet": {"publishedAt": "2024-01-15T12:00:00Z", "channelId": "UCtest"},
                "contentDetails": {"duration": "PT1M"},
                "statistics": {},
            }
        )
