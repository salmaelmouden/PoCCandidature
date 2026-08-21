"""ORM models for Growth Intelligence AI."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    youtube_video_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    channel_title: Mapped[str] = mapped_column(String(256), nullable=False)
    topic: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dataset_label: Mapped[str] = mapped_column(String(64), nullable=False, default="synthetic_v1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    daily_metrics: Mapped[list["VideoDailyMetric"]] = relationship(back_populates="video")
    acquisitions: Mapped[list["Acquisition"]] = relationship(back_populates="video")
    classifications: Mapped[list["VideoClassification"]] = relationship(back_populates="video")


class VideoDailyMetric(Base):
    __tablename__ = "video_daily_metrics"
    __table_args__ = (
        UniqueConstraint("video_id", "metric_date", name="uq_video_daily_metrics_video_date"),
        Index("ix_video_daily_metrics_date", "metric_date"),
    )

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    video_id: Mapped[Any] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    likes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dataset_label: Mapped[str] = mapped_column(String(64), nullable=False, default="synthetic_v1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    video: Mapped[Video] = relationship(back_populates="daily_metrics")


class IngestRun(Base):
    """
    One refresh cycle.

    Needed because the metric upsert cannot answer "when did we last check?": on a
    same-day re-ingest it updates the existing row, and when the counters have not
    moved SQLAlchemy emits no UPDATE at all. Freshness is a property of the run,
    not of the data.
    """

    __tablename__ = "ingest_runs"
    __table_args__ = (Index("ix_ingest_runs_finished", "finished_at"),)

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    videos_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metrics_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    classified: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)


class VideoClassification(Base):
    """
    LLM-assigned editorial labels for a video.

    Kept out of `videos.topic` on purpose: the keyword topic stays as-is, and the
    classification is versioned so a taxonomy change re-runs cleanly instead of
    overwriting history. See ADR-008.
    """

    __tablename__ = "video_classifications"
    __table_args__ = (
        UniqueConstraint("video_id", "version", name="uq_video_classifications_video_version"),
        Index("ix_video_classifications_topic", "topic"),
        Index("ix_video_classifications_hook", "hook_type"),
    )

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    video_id: Mapped[Any] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    topic: Mapped[str] = mapped_column(String(64), nullable=False)
    hook_type: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    classified_by: Mapped[str] = mapped_column(String(64), nullable=False)
    classified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    video: Mapped[Video] = relationship(back_populates="classifications")


class Acquisition(Base):
    """Daily funnel facts by channel / topic / optional video."""

    __tablename__ = "acquisition"
    __table_args__ = (
        UniqueConstraint(
            "metric_date",
            "channel",
            "topic",
            "video_id",
            name="uq_acquisition_date_channel_topic_video",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_acquisition_date_channel", "metric_date", "channel"),
    )

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    topic: Mapped[str] = mapped_column(String(64), nullable=False)
    video_id: Mapped[Optional[Any]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True
    )
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    visits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signups: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activated_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    premium_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dataset_label: Mapped[str] = mapped_column(String(64), nullable=False, default="synthetic_v1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    video: Mapped[Optional[Video]] = relationship(back_populates="acquisitions")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_channel_signup", "channel", "signed_up_at"),
        Index("ix_users_topic", "topic"),
    )

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    signed_up_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    became_premium_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    topic: Mapped[str] = mapped_column(String(64), nullable=False)
    source_video_id: Mapped[Optional[Any]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True
    )
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dataset_label: Mapped[str] = mapped_column(String(64), nullable=False, default="synthetic_v1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    experiment_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    primary_metric: Mapped[str] = mapped_column(String(128), nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dataset_label: Mapped[str] = mapped_column(String(64), nullable=False, default="synthetic_v1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    results: Mapped[list["ExperimentResult"]] = relationship(back_populates="experiment")


class ExperimentResult(Base):
    __tablename__ = "experiment_results"
    __table_args__ = (
        UniqueConstraint("experiment_id", "variant", name="uq_experiment_results_experiment_variant"),
    )

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    experiment_id: Mapped[Any] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    variant: Mapped[str] = mapped_column(String(64), nullable=False)
    users: Mapped[int] = mapped_column(Integer, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, nullable=False)
    conversion_rate: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dataset_label: Mapped[str] = mapped_column(String(64), nullable=False, default="synthetic_v1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    experiment: Mapped[Experiment] = relationship(back_populates="results")


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_date",
            "period_start",
            "period_end",
            "metric_name",
            "dimension_key",
            name="uq_analytics_snapshots_identity",
        ),
        Index("ix_analytics_snapshots_metric", "metric_name", "snapshot_date"),
    )

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False)
    metric_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    dimension_key: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    dimensions: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dataset_label: Mapped[str] = mapped_column(String(64), nullable=False, default="synthetic_v1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
