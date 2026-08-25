"""Rewrite the synthetic dataset with the corrected funnel generator.

The first data migration in this project, and deliberate. `8921fc2` fixed a
generator that floored the funnel's lower stages, but a deploy ships code, not
rows: the database keeps whatever the old generator wrote, so the deployed demo
goes on reporting a Premium leak that no longer exists anywhere in the codebase.

This runs where the correction is guaranteed to reach every environment without
anyone having to remember: `railway.json` already starts with `alembic upgrade
head`, so the next deploy carries it — no shell on the host, no one-shot service,
no variable to set and unset. `make seed-reset` and `railway.seed.json` remain for
re-seeding on demand afterwards; this exists so the first correction is not
something a human has to think about.

Two things it does NOT do, on purpose:

- It does not pin the generator. A migration is normally frozen against the schema
  of its own revision, and importing live application code breaks that rule. Here
  the intent *is* "make the stored rows match the generator as it stands", so the
  coupling is the feature. The consequence is honest: replay this revision in a
  year and you get that year's dataset, not this one's. Nothing reads the synthetic
  rows as history — they are regenerated from a seed by definition.
- It does not touch the ingested catalogue. `purge_synthetic_dataset` deletes by
  `dataset_label`, so the ~950 real videos under `youtube_api` — the only data here
  that cannot be regenerated — are untouched.

Cost: roughly 20 s against a local Postgres for ~13 600 rows, since the loader
upserts row by row. That lands on the dashboard's boot path ahead of the health
check, which is why `railway.json` widens `healthcheckTimeout` in the same commit.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.loader import load_synthetic_dataset, purge_synthetic_dataset
from app.db.synthetic import generate_synthetic_dataset

revision: str = "004_reseed_synthetic_dataset"
down_revision: Union[str, None] = "003_ingest_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    settings = get_settings()
    dataset = generate_synthetic_dataset(
        seed=settings.synthetic_seed,
        days=settings.synthetic_days,
    )
    # Bound to Alembic's connection rather than a new engine, so the purge and the
    # load land in the migration's own transaction: a failure rolls back to the old
    # dataset instead of leaving the demo with no funnel at all.
    session = Session(bind=op.get_bind())
    purge_synthetic_dataset(session)
    load_synthetic_dataset(session, dataset)
    session.flush()


def downgrade() -> None:
    """
    Nothing to restore.

    The rows this replaced came from a generator that no longer exists in the tree,
    so no honest inverse can be written. Re-running `make seed-reset` reproduces the
    current dataset; that is the only meaningful direction.
    """
