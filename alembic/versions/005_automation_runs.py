"""Record every scheduled run, successful or not.

`ingest_runs` answers "is the data current". It cannot answer "is the machinery
still running": the refresher and the Monday memo fail independently, and a
catalogue that keeps refreshing while the memo has been erroring for three weeks
reads as perfectly healthy through `ingest_runs` alone.

The table stores failures as rows rather than as absences. Writing nothing on
failure would make a broken automation indistinguishable from one that is simply
not due yet — the same distinction migration `003` drew between "last checked"
and "last changed", applied one level up.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "005_automation_runs"
down_revision: str | None = "004_reseed_synthetic_dataset"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "automation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("automation", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("error", sa.String(length=512), nullable=True),
        sa.Column("artifact_path", sa.String(length=512), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Composite, in this order: every read is "the latest run of automation X",
    # so the name has to lead for the index to be usable at all.
    op.create_index(
        "ix_automation_runs_name_finished",
        "automation_runs",
        ["automation", "finished_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_automation_runs_name_finished", table_name="automation_runs")
    op.drop_table("automation_runs")
