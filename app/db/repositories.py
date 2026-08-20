"""Repository layer — all persistence goes through these classes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Acquisition,
    AnalyticsSnapshot,
    Experiment,
    ExperimentResult,
    User,
    Video,
    VideoDailyMetric,
)


class VideoRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_by_youtube_id(self, **fields: Any) -> Video:
        youtube_video_id = fields["youtube_video_id"]
        existing = self._session.scalar(
            select(Video).where(Video.youtube_video_id == youtube_video_id)
        )
        if existing is None:
            video = Video(**fields)
            self._session.add(video)
            self._session.flush()
            return video
        for key, value in fields.items():
            if key == "youtube_video_id":
                continue
            setattr(existing, key, value)
        self._session.flush()
        return existing

    def get_by_youtube_id(self, youtube_video_id: str) -> Video | None:
        return self._session.scalar(
            select(Video).where(Video.youtube_video_id == youtube_video_id)
        )

    def list_all(self) -> Sequence[Video]:
        return self._session.scalars(select(Video).order_by(Video.published_at)).all()


class VideoDailyMetricRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(self, video_id: UUID, metric_date: date, **metrics: Any) -> VideoDailyMetric:
        existing = self._session.scalar(
            select(VideoDailyMetric).where(
                VideoDailyMetric.video_id == video_id,
                VideoDailyMetric.metric_date == metric_date,
            )
        )
        if existing is None:
            row = VideoDailyMetric(video_id=video_id, metric_date=metric_date, **metrics)
            self._session.add(row)
            self._session.flush()
            return row
        for key, value in metrics.items():
            setattr(existing, key, value)
        self._session.flush()
        return existing


class AcquisitionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(
        self,
        *,
        metric_date: date,
        channel: str,
        topic: str,
        video_id: UUID | None,
        views: int,
        visits: int,
        signups: int,
        activated_users: int,
        premium_users: int,
        is_synthetic: bool = True,
        dataset_label: str = "synthetic_v1",
    ) -> Acquisition:
        stmt = select(Acquisition).where(
            Acquisition.metric_date == metric_date,
            Acquisition.channel == channel,
            Acquisition.topic == topic,
        )
        if video_id is None:
            stmt = stmt.where(Acquisition.video_id.is_(None))
        else:
            stmt = stmt.where(Acquisition.video_id == video_id)

        existing = self._session.scalar(stmt)
        payload = {
            "views": views,
            "visits": visits,
            "signups": signups,
            "activated_users": activated_users,
            "premium_users": premium_users,
            "is_synthetic": is_synthetic,
            "dataset_label": dataset_label,
        }
        if existing is None:
            row = Acquisition(
                metric_date=metric_date,
                channel=channel,
                topic=topic,
                video_id=video_id,
                **payload,
            )
            self._session.add(row)
            self._session.flush()
            return row
        for key, value in payload.items():
            setattr(existing, key, value)
        self._session.flush()
        return existing

    def list_between(
        self,
        *,
        start: date,
        end: date,
        channel: str | None = None,
    ) -> Sequence[Acquisition]:
        rows = self._session.scalars(
            select(Acquisition)
            .where(
                Acquisition.metric_date >= start,
                Acquisition.metric_date <= end,
            )
            .order_by(Acquisition.metric_date)
        ).all()
        if channel is None:
            return rows
        return [row for row in rows if row.channel == channel]

    def sum_funnel(
        self, *, start: date, end: date, channel: str | None = None
    ) -> dict[str, int]:
        totals = {
            "views": 0,
            "visits": 0,
            "signups": 0,
            "activated_users": 0,
            "premium_users": 0,
        }
        for row in self.list_between(start=start, end=end, channel=channel):
            totals["views"] += row.views
            totals["visits"] += row.visits
            totals["signups"] += row.signups
            totals["activated_users"] += row.activated_users
            totals["premium_users"] += row.premium_users
        return totals

    def daily_metric_series(
        self,
        *,
        start: date,
        end: date,
        metric: str,
        channel: str | None = None,
    ) -> list[tuple[date, int]]:
        """Sum one funnel metric per day (ordered)."""
        allowed = {"views", "visits", "signups", "activated_users", "premium_users"}
        if metric not in allowed:
            raise ValueError(f"Unsupported metric: {metric}")
        by_day: dict[date, int] = {}
        for row in self.list_between(start=start, end=end, channel=channel):
            by_day[row.metric_date] = by_day.get(row.metric_date, 0) + int(
                getattr(row, metric)
            )
        return sorted(by_day.items(), key=lambda item: item[0])


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_by_key(self, **fields: Any) -> User:
        user_key = fields["user_key"]
        existing = self._session.scalar(select(User).where(User.user_key == user_key))
        if existing is None:
            user = User(**fields)
            self._session.add(user)
            self._session.flush()
            return user
        for key, value in fields.items():
            if key == "user_key":
                continue
            setattr(existing, key, value)
        self._session.flush()
        return existing


class ExperimentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_experiment(self, **fields: Any) -> Experiment:
        key = fields["experiment_key"]
        existing = self._session.scalar(
            select(Experiment).where(Experiment.experiment_key == key)
        )
        if existing is None:
            experiment = Experiment(**fields)
            self._session.add(experiment)
            self._session.flush()
            return experiment
        for field, value in fields.items():
            if field == "experiment_key":
                continue
            setattr(existing, field, value)
        self._session.flush()
        return existing

    def upsert_result(
        self,
        *,
        experiment_id: UUID,
        variant: str,
        users: int,
        conversions: int,
        conversion_rate: Decimal,
        is_synthetic: bool = True,
        dataset_label: str = "synthetic_v1",
    ) -> ExperimentResult:
        existing = self._session.scalar(
            select(ExperimentResult).where(
                ExperimentResult.experiment_id == experiment_id,
                ExperimentResult.variant == variant,
            )
        )
        payload = {
            "users": users,
            "conversions": conversions,
            "conversion_rate": conversion_rate,
            "is_synthetic": is_synthetic,
            "dataset_label": dataset_label,
        }
        if existing is None:
            row = ExperimentResult(experiment_id=experiment_id, variant=variant, **payload)
            self._session.add(row)
            self._session.flush()
            return row
        for key, value in payload.items():
            setattr(existing, key, value)
        self._session.flush()
        return existing


class AnalyticsSnapshotRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(
        self,
        *,
        snapshot_date: date,
        period_start: date,
        period_end: date,
        metric_name: str,
        metric_value: Decimal,
        dimension_key: str = "",
        dimensions: dict | None = None,
        is_synthetic: bool = True,
        dataset_label: str = "synthetic_v1",
    ) -> AnalyticsSnapshot:
        existing = self._session.scalar(
            select(AnalyticsSnapshot).where(
                AnalyticsSnapshot.snapshot_date == snapshot_date,
                AnalyticsSnapshot.period_start == period_start,
                AnalyticsSnapshot.period_end == period_end,
                AnalyticsSnapshot.metric_name == metric_name,
                AnalyticsSnapshot.dimension_key == dimension_key,
            )
        )
        dims = dimensions or {}
        if existing is None:
            row = AnalyticsSnapshot(
                snapshot_date=snapshot_date,
                period_start=period_start,
                period_end=period_end,
                metric_name=metric_name,
                metric_value=metric_value,
                dimension_key=dimension_key,
                dimensions=dims,
                is_synthetic=is_synthetic,
                dataset_label=dataset_label,
            )
            self._session.add(row)
            self._session.flush()
            return row
        existing.metric_value = metric_value
        existing.dimensions = dims
        existing.is_synthetic = is_synthetic
        existing.dataset_label = dataset_label
        self._session.flush()
        return existing
