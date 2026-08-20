"""Initial schema for Growth Intelligence AI."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("youtube_video_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("channel_title", sa.String(length=256), nullable=False),
        sa.Column("topic", sa.String(length=64), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("dataset_label", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("youtube_video_id"),
    )
    op.create_index("ix_videos_topic", "videos", ["topic"])

    op.create_table(
        "experiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("experiment_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("primary_metric", sa.String(length=128), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("dataset_label", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_key"),
    )

    op.create_table(
        "analytics_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("metric_value", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("dimension_key", sa.String(length=256), nullable=False),
        sa.Column("dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("dataset_label", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_date",
            "period_start",
            "period_end",
            "metric_name",
            "dimension_key",
            name="uq_analytics_snapshots_identity",
        ),
    )
    op.create_index(
        "ix_analytics_snapshots_metric",
        "analytics_snapshots",
        ["metric_name", "snapshot_date"],
    )

    op.create_table(
        "video_daily_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("likes", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Integer(), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("dataset_label", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "metric_date", name="uq_video_daily_metrics_video_date"),
    )
    op.create_index("ix_video_daily_metrics_date", "video_daily_metrics", ["metric_date"])

    op.create_table(
        "acquisition",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.String(length=64), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("visits", sa.Integer(), nullable=False),
        sa.Column("signups", sa.Integer(), nullable=False),
        sa.Column("activated_users", sa.Integer(), nullable=False),
        sa.Column("premium_users", sa.Integer(), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("dataset_label", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "metric_date",
            "channel",
            "topic",
            "video_id",
            name="uq_acquisition_date_channel_topic_video",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index("ix_acquisition_date_channel", "acquisition", ["metric_date", "channel"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_key", sa.String(length=64), nullable=False),
        sa.Column("signed_up_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("became_premium_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.String(length=64), nullable=False),
        sa.Column("source_video_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("dataset_label", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_video_id"], ["videos.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_key"),
    )
    op.create_index("ix_users_channel_signup", "users", ["channel", "signed_up_at"])
    op.create_index("ix_users_topic", "users", ["topic"])

    op.create_table(
        "experiment_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("variant", sa.String(length=64), nullable=False),
        sa.Column("users", sa.Integer(), nullable=False),
        sa.Column("conversions", sa.Integer(), nullable=False),
        sa.Column("conversion_rate", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("dataset_label", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "experiment_id", "variant", name="uq_experiment_results_experiment_variant"
        ),
    )


def downgrade() -> None:
    op.drop_table("experiment_results")
    op.drop_index("ix_users_topic", table_name="users")
    op.drop_index("ix_users_channel_signup", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_acquisition_date_channel", table_name="acquisition")
    op.drop_table("acquisition")
    op.drop_index("ix_video_daily_metrics_date", table_name="video_daily_metrics")
    op.drop_table("video_daily_metrics")
    op.drop_index("ix_analytics_snapshots_metric", table_name="analytics_snapshots")
    op.drop_table("analytics_snapshots")
    op.drop_table("experiments")
    op.drop_index("ix_videos_topic", table_name="videos")
    op.drop_table("videos")
