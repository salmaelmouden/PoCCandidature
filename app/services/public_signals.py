"""Public-signal application service — repos + skill, no UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Video, VideoClassification, VideoDailyMetric
from app.db.repositories import IngestRunRepository
from app.skills.catalogue_movement import (
    MovementReport,
    VideoSnapshotPair,
    analyse_movement,
)
from app.skills.content_classification.schemas import CLASSIFICATION_VERSION
from app.skills.public_signal_analysis import (
    PublicSignalReport,
    PublicVideoSignal,
    analyse_public_signals,
)

FALLBACK_BACKEND = "keyword_fallback"


@dataclass(frozen=True)
class CatalogueFreshness:
    """
    How current the underlying snapshot is — shown, not assumed.

    `last_checked_at` and `last_changed_at` are deliberately separate. A refresh
    that finds identical counters writes nothing, so "when did the data last
    change" is not the same question as "when did we last look". Conflating them
    makes a live page look stale, or a stale page look live.
    """

    videos: int
    classified: int
    last_metric_date: date | None
    last_checked_at: datetime | None
    last_changed_at: datetime | None
    last_classified_at: datetime | None
    last_run_ok: bool | None
    last_run_error: str | None

    @property
    def unclassified(self) -> int:
        return max(0, self.videos - self.classified)


def get_catalogue_freshness(
    session: Session,
    *,
    dataset_label: str = "youtube_api",
    version: str = CLASSIFICATION_VERSION,
) -> CatalogueFreshness:
    """Read the ingest/classification watermarks so the page can show its own age."""
    videos = (
        session.scalar(
            select(func.count(Video.id)).where(Video.dataset_label == dataset_label)
        )
        or 0
    )
    classified = (
        session.scalar(
            select(func.count(VideoClassification.id))
            .join(Video, Video.id == VideoClassification.video_id)
            .where(
                Video.dataset_label == dataset_label,
                VideoClassification.version == version,
            )
        )
        or 0
    )
    last_metric_date = session.scalar(
        select(func.max(VideoDailyMetric.metric_date))
        .join(Video, Video.id == VideoDailyMetric.video_id)
        .where(Video.dataset_label == dataset_label)
    )
    last_changed_at = session.scalar(
        select(func.max(VideoDailyMetric.updated_at))
        .join(Video, Video.id == VideoDailyMetric.video_id)
        .where(Video.dataset_label == dataset_label)
    )
    last_classified_at = session.scalar(
        select(func.max(VideoClassification.classified_at)).where(
            VideoClassification.version == version
        )
    )
    last_run = IngestRunRepository(session).latest()
    return CatalogueFreshness(
        videos=videos,
        classified=classified,
        last_metric_date=last_metric_date,
        last_checked_at=last_run.finished_at if last_run else None,
        last_changed_at=last_changed_at,
        last_classified_at=last_classified_at,
        last_run_ok=last_run.ok if last_run else None,
        last_run_error=last_run.error if last_run else None,
    )


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


def load_snapshot_pair(
    session: Session,
    *,
    dataset_label: str = "youtube_api",
    version: str = CLASSIFICATION_VERSION,
) -> tuple[list[VideoSnapshotPair], date, date] | None:
    """
    Load each video's views at the two most recent snapshot dates.

    Returns `None` when fewer than two dates exist — the caller must be able to say
    "first measurement point" rather than fabricate a comparison.

    Unlike `load_public_signals`, videos are **not** dropped for carrying a
    keyword-fallback label. Format and publication age do not depend on
    classification, and they carry the headline movement finding; excluding rows
    would shrink that coverage for a reason irrelevant to it. Instead the untrusted
    labels are nulled out, so topic and hook aggregate over trusted labels only while
    format and age see the whole catalogue.
    """
    dates = list(
        session.scalars(
            select(VideoDailyMetric.metric_date)
            .join(Video, Video.id == VideoDailyMetric.video_id)
            .where(Video.dataset_label == dataset_label)
            .distinct()
            .order_by(VideoDailyMetric.metric_date.desc())
            .limit(2)
        )
    )
    if len(dates) < 2:
        return None
    period_end, period_start = dates[0], dates[1]

    rows = session.execute(
        select(Video, VideoDailyMetric, VideoClassification)
        .join(VideoDailyMetric, VideoDailyMetric.video_id == Video.id)
        .outerjoin(
            VideoClassification,
            (VideoClassification.video_id == Video.id)
            & (VideoClassification.version == version),
        )
        .where(
            Video.dataset_label == dataset_label,
            VideoDailyMetric.metric_date.in_((period_start, period_end)),
        )
    )

    seen: dict[str, dict] = {}
    for video, metric, classification in rows:
        entry = seen.setdefault(
            video.youtube_video_id,
            {"video": video, "classification": classification, "start": None, "end": None},
        )
        entry["start" if metric.metric_date == period_start else "end"] = metric.views

    pairs: list[VideoSnapshotPair] = []
    for entry in seen.values():
        if entry["start"] is None or entry["end"] is None:
            continue  # published between snapshots — no movement to measure yet
        video, classification = entry["video"], entry["classification"]
        trusted = classification is not None and classification.classified_by != FALLBACK_BACKEND
        pairs.append(
            VideoSnapshotPair(
                youtube_video_id=video.youtube_video_id,
                title=video.title,
                published_at=video.published_at,
                duration_seconds=video.duration_seconds,
                topic=classification.topic if trusted else None,
                hook_type=classification.hook_type if trusted else None,
                views_start=entry["start"],
                views_end=entry["end"],
            )
        )
    return pairs, period_start, period_end


def build_movement_report(
    session: Session,
    *,
    dataset_label: str = "youtube_api",
    version: str = CLASSIFICATION_VERSION,
) -> MovementReport | None:
    """Load two snapshots, then analyse. `None` when there is no history yet."""
    loaded = load_snapshot_pair(session, dataset_label=dataset_label, version=version)
    if loaded is None:
        return None
    pairs, period_start, period_end = loaded
    if not pairs:
        return None
    return analyse_movement(pairs, period_start=period_start, period_end=period_end)


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
