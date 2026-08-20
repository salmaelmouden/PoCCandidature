"""Extract → transform → load YouTube channel videos into repositories."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.db.repositories import VideoDailyMetricRepository, VideoRepository
from app.skills.youtube_ingestion.client import YouTubeClient
from app.skills.youtube_ingestion.schemas import (
    IngestYouTubeResult,
    YouTubeIngestRequest,
    YOUTUBE_DATASET_LABEL,
)
from app.skills.youtube_ingestion.transform import TransformError, normalize_video_payload

logger = logging.getLogger(__name__)


def ingest_youtube_channel(
    session: Session,
    client: YouTubeClient,
    request: YouTubeIngestRequest,
) -> IngestYouTubeResult:
    """
    Idempotently ingest videos + cumulative metric snapshots for a channel.

    Does not invent acquisition/funnel facts — metadata and public stats only.
    """
    metric_date = request.metric_date or datetime.now(timezone.utc).date()
    video_repo = VideoRepository(session)
    metric_repo = VideoDailyMetricRepository(session)

    uploads_playlist = client.get_uploads_playlist_id(request.channel_id)
    video_ids = client.list_playlist_video_ids(
        uploads_playlist, max_pages=request.max_pages
    )
    raw_items = client.get_videos(video_ids)

    videos_upserted = 0
    metrics_upserted = 0
    skipped_invalid = 0

    for item in raw_items:
        try:
            normalized = normalize_video_payload(item)
        except TransformError as exc:
            skipped_invalid += 1
            logger.warning("youtube_transform_skip error=%s", exc)
            continue

        video = video_repo.upsert_by_youtube_id(
            youtube_video_id=normalized.youtube_video_id,
            title=normalized.title,
            description=normalized.description,
            published_at=normalized.published_at,
            duration_seconds=normalized.duration_seconds,
            channel_id=normalized.channel_id,
            channel_title=normalized.channel_title,
            topic=normalized.topic,
            is_synthetic=False,
            dataset_label=YOUTUBE_DATASET_LABEL,
        )
        videos_upserted += 1

        metric_repo.upsert(
            video.id,
            metric_date,
            views=normalized.views,
            likes=normalized.likes,
            comments=normalized.comments,
            is_synthetic=False,
            dataset_label=YOUTUBE_DATASET_LABEL,
        )
        metrics_upserted += 1

    session.flush()
    result = IngestYouTubeResult(
        channel_id=request.channel_id,
        metric_date=metric_date,
        videos_seen=len(raw_items),
        videos_upserted=videos_upserted,
        metrics_upserted=metrics_upserted,
        skipped_invalid=skipped_invalid,
    )
    logger.info(
        "youtube_ingest_complete channel_id=%s videos_upserted=%s metrics_upserted=%s skipped=%s",
        result.channel_id,
        result.videos_upserted,
        result.metrics_upserted,
        result.skipped_invalid,
    )
    return result
