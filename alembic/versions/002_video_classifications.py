"""Add video_classifications (LLM editorial labels, versioned)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_video_classifications"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "video_classifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.String(length=64), nullable=False),
        sa.Column("hook_type", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=16), nullable=False),
        sa.Column("classified_by", sa.String(length=64), nullable=False),
        sa.Column(
            "classified_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "version", name="uq_video_classifications_video_version"),
    )
    op.create_index("ix_video_classifications_topic", "video_classifications", ["topic"])
    op.create_index("ix_video_classifications_hook", "video_classifications", ["hook_type"])


def downgrade() -> None:
    op.drop_index("ix_video_classifications_hook", table_name="video_classifications")
    op.drop_index("ix_video_classifications_topic", table_name="video_classifications")
    op.drop_table("video_classifications")
