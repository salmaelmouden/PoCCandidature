"""Load a SyntheticDataset into the database via repositories (idempotent)."""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.repositories import (
    AcquisitionRepository,
    AnalyticsSnapshotRepository,
    ExperimentRepository,
    UserRepository,
    VideoDailyMetricRepository,
    VideoRepository,
)
from app.db.synthetic import SyntheticDataset

logger = logging.getLogger(__name__)


def load_synthetic_dataset(session: Session, dataset: SyntheticDataset) -> dict[str, int]:
    """Upsert synthetic rows. Safe to re-run."""
    video_repo = VideoRepository(session)
    metric_repo = VideoDailyMetricRepository(session)
    acquisition_repo = AcquisitionRepository(session)
    user_repo = UserRepository(session)
    experiment_repo = ExperimentRepository(session)
    snapshot_repo = AnalyticsSnapshotRepository(session)

    video_ids: dict[str, object] = {}
    for video in dataset.videos:
        row = video_repo.upsert_by_youtube_id(
            youtube_video_id=video.youtube_video_id,
            title=video.title,
            description=video.description,
            published_at=video.published_at,
            duration_seconds=video.duration_seconds,
            channel_id=video.channel_id,
            channel_title=video.channel_title,
            topic=video.topic,
            is_synthetic=dataset.is_synthetic,
            dataset_label=dataset.label,
        )
        video_ids[video.youtube_video_id] = row.id

    for metric in dataset.daily_metrics:
        metric_repo.upsert(
            video_id=video_ids[metric.youtube_video_id],  # type: ignore[arg-type]
            metric_date=metric.metric_date,
            views=metric.views,
            likes=metric.likes,
            comments=metric.comments,
            is_synthetic=dataset.is_synthetic,
            dataset_label=dataset.label,
        )

    for row in dataset.acquisitions:
        video_id = video_ids.get(row.youtube_video_id) if row.youtube_video_id else None
        acquisition_repo.upsert(
            metric_date=row.metric_date,
            channel=row.channel,
            topic=row.topic,
            video_id=video_id,  # type: ignore[arg-type]
            views=row.views,
            visits=row.visits,
            signups=row.signups,
            activated_users=row.activated_users,
            premium_users=row.premium_users,
            is_synthetic=dataset.is_synthetic,
            dataset_label=dataset.label,
        )

    for user in dataset.users:
        source_video_id = (
            video_ids.get(user.youtube_video_id) if user.youtube_video_id else None
        )
        user_repo.upsert_by_key(
            user_key=user.user_key,
            signed_up_at=user.signed_up_at,
            activated_at=user.activated_at,
            became_premium_at=user.became_premium_at,
            channel=user.channel,
            topic=user.topic,
            source_video_id=source_video_id,
            is_synthetic=dataset.is_synthetic,
            dataset_label=dataset.label,
        )

    for experiment in dataset.experiments:
        exp = experiment_repo.upsert_experiment(
            experiment_key=experiment.experiment_key,
            name=experiment.name,
            hypothesis=experiment.hypothesis,
            status=experiment.status,
            primary_metric=experiment.primary_metric,
            start_date=experiment.start_date,
            end_date=experiment.end_date,
            is_synthetic=dataset.is_synthetic,
            dataset_label=dataset.label,
        )
        for result in experiment.results:
            experiment_repo.upsert_result(
                experiment_id=exp.id,
                variant=result.variant,
                users=result.users,
                conversions=result.conversions,
                conversion_rate=result.conversion_rate,
                is_synthetic=dataset.is_synthetic,
                dataset_label=dataset.label,
            )

    for snap in dataset.snapshots:
        snapshot_repo.upsert(
            snapshot_date=snap.snapshot_date,
            period_start=snap.period_start,
            period_end=snap.period_end,
            metric_name=snap.metric_name,
            metric_value=Decimal(snap.metric_value),
            dimension_key=snap.dimension_key,
            dimensions=snap.dimensions,
            is_synthetic=dataset.is_synthetic,
            dataset_label=dataset.label,
        )

    counts = {
        "videos": len(dataset.videos),
        "daily_metrics": len(dataset.daily_metrics),
        "acquisitions": len(dataset.acquisitions),
        "users": len(dataset.users),
        "experiments": len(dataset.experiments),
        "snapshots": len(dataset.snapshots),
    }
    logger.info(
        "synthetic_load_complete",
        extra={"dataset_label": dataset.label, "counts": counts},
    )
    return counts
