"""Track refresh cycles, and stamp metric updates.

`video_daily_metrics.created_at` cannot answer "when did we last check?" — a
same-day re-ingest updates the row rather than inserting, and an unchanged
counter emits no UPDATE at all.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_ingest_runs"
down_revision: Union[str, None] = "002_video_classifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "video_daily_metrics",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "ingest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("videos_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metrics_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("classified", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("error", sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingest_runs_finished", "ingest_runs", ["finished_at"])


def downgrade() -> None:
    op.drop_index("ix_ingest_runs_finished", table_name="ingest_runs")
    op.drop_table("ingest_runs")
    op.drop_column("video_daily_metrics", "updated_at")
