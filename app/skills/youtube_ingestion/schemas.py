"""Typed contracts for youtube_ingestion."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


YOUTUBE_DATASET_LABEL = "youtube_api"


class YouTubeIngestRequest(BaseModel):
    channel_id: str = Field(min_length=1)
    metric_date: date | None = None
    max_pages: int = Field(default=10, ge=1, le=50)


class NormalizedVideo(BaseModel):
    youtube_video_id: str
    title: str
    description: str
    published_at: datetime
    duration_seconds: int = Field(ge=0)
    channel_id: str
    channel_title: str
    topic: str
    views: int = Field(ge=0)
    likes: int = Field(ge=0)
    comments: int = Field(ge=0)
    is_synthetic: bool = False
    dataset_label: str = YOUTUBE_DATASET_LABEL


class IngestYouTubeResult(BaseModel):
    channel_id: str
    metric_date: date
    videos_seen: int
    videos_upserted: int
    metrics_upserted: int
    skipped_invalid: int
    dataset_label: str = YOUTUBE_DATASET_LABEL
    notes: str = (
        "Statistics from YouTube Data API are cumulative lifetime totals snapshotted "
        "for metric_date; not true daily increments."
    )
