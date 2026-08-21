"""Public-signal application service — repos + skill, no UI."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Video, VideoClassification, VideoDailyMetric
from app.skills.content_classification.schemas import CLASSIFICATION_VERSION
from app.skills.public_signal_analysis import (
    PublicSignalReport,
    PublicVideoSignal,
    analyse_public_signals,
)

FALLBACK_BACKEND = "keyword_fallback"


def load_public_signals(
    session: Session,
    *,
    dataset_label: str = "youtube_api",
    version: str = CLASSIFICATION_VERSION,
    include_fallback_labels: bool = False,
) -> list[PublicVideoSignal]:
    """
    Load classified videos with their latest public metric snapshot.

    Fallback-classified rows are excluded by default: their labels come from the
    keyword classifier, which is the thing this analysis exists to replace.
    """
    statement = (
        select(Video, VideoDailyMetric, VideoClassification)
        .join(VideoDailyMetric, VideoDailyMetric.video_id == Video.id)
        .join(VideoClassification, VideoClassification.video_id == Video.id)
        .where(
            Video.dataset_label == dataset_label,
            VideoClassification.version == version,
        )
        .order_by(Video.published_at)
    )
    if not include_fallback_labels:
        statement = statement.where(VideoClassification.classified_by != FALLBACK_BACKEND)

    signals: dict[str, PublicVideoSignal] = {}
    for video, metric, classification in session.execute(statement):
        # One snapshot per video today; keep the freshest if the ingest ever runs daily.
        existing = signals.get(video.youtube_video_id)
        if existing is not None and existing.views >= metric.views:
            continue
        signals[video.youtube_video_id] = PublicVideoSignal(
            youtube_video_id=video.youtube_video_id,
            title=video.title,
            published_at=video.published_at,
            duration_seconds=video.duration_seconds,
            views=metric.views,
            likes=metric.likes,
            comments=metric.comments,
            topic=classification.topic,
            hook_type=classification.hook_type,
        )
    return list(signals.values())


def build_public_signal_report(
    session: Session,
    *,
    dataset_label: str = "youtube_api",
    version: str = CLASSIFICATION_VERSION,
) -> PublicSignalReport:
    """Load, then analyse. All arithmetic lives in the deterministic skill."""
    return analyse_public_signals(
        load_public_signals(session, dataset_label=dataset_label, version=version)
    )
