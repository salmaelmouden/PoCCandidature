"""Shared eval fixtures — pinned synthetic window for reproducible agent scores."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.repositories import AcquisitionRepository, ExperimentRepository

# Pinned demo window (matches earlier agent unit tests)
EVAL_AS_OF = date(2026, 8, 20)
EVAL_DAYS = 7
DATASET_LABEL = "synthetic_v1"


def seed_premium_drop_fixture(session: Session) -> None:
    """YouTube Premium weakness vs LinkedIn in current window."""
    repo = AcquisitionRepository(session)
    rows = [
        (date(2026, 8, 18), "YouTube", "Crypto", 5000, 1000, 100, 80, 4),
        (date(2026, 8, 18), "LinkedIn", "ETFs", 800, 300, 90, 70, 25),
        (date(2026, 8, 10), "YouTube", "Crypto", 4000, 900, 120, 90, 18),
        (date(2026, 8, 10), "LinkedIn", "ETFs", 700, 280, 85, 65, 22),
    ]
    for metric_date, channel, topic, views, visits, signups, activated, premium in rows:
        repo.upsert(
            metric_date=metric_date,
            channel=channel,
            topic=topic,
            video_id=None,
            views=views,
            visits=visits,
            signups=signups,
            activated_users=activated,
            premium_users=premium,
            is_synthetic=True,
            dataset_label=DATASET_LABEL,
        )
    session.commit()


def seed_degenerate_funnel_fixture(session: Session) -> None:
    """
    Significant traffic and activation, terminal stage empty (Phase 16 / W2).

    Every other fixture in this module pins a *healthy* terminal stage — 4, 25, 18,
    22 Premium conversions. That is why the eval suite stayed green while the
    pipeline shipped `[P0] Fix Premium leak on weakest channel` off an integer
    truncation artefact: the agents had never been scored against an empty stage.

    The numbers below reproduce the shape that actually shipped in
    `reports/weekly_20260820T133352Z.md` — 566 activations, 0 Premium, across the
    two channels that carried the most volume.
    """
    repo = AcquisitionRepository(session)
    rows = [
        (date(2026, 8, 18), "YouTube", "Crypto", 42_000, 9_000, 620, 283, 0),
        (date(2026, 8, 16), "Paid", "Stocks", 31_000, 8_600, 590, 283, 0),
        (date(2026, 8, 10), "YouTube", "Crypto", 38_000, 8_200, 570, 260, 24),
        (date(2026, 8, 10), "Paid", "Stocks", 29_000, 8_000, 540, 250, 21),
    ]
    for metric_date, channel, topic, views, visits, signups, activated, premium in rows:
        repo.upsert(
            metric_date=metric_date,
            channel=channel,
            topic=topic,
            video_id=None,
            views=views,
            visits=visits,
            signups=signups,
            activated_users=activated,
            premium_users=premium,
            is_synthetic=True,
            dataset_label=DATASET_LABEL,
        )
    session.commit()


def seed_youtube_cta_experiment(session: Session) -> None:
    exp_repo = ExperimentRepository(session)
    exp = exp_repo.upsert_experiment(
        experiment_key="syn_exp_youtube_cta",
        name="[SYNTHETIC] YouTube contextual Premium CTA",
        hypothesis="CTA improves activated→premium",
        status="completed",
        primary_metric="activated_to_premium_rate",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 8, 1),
        is_synthetic=True,
        dataset_label=DATASET_LABEL,
    )
    exp_repo.upsert_result(
        experiment_id=exp.id,
        variant="control",
        users=4200,
        conversions=378,
        conversion_rate=Decimal("0.090000"),
    )
    exp_repo.upsert_result(
        experiment_id=exp.id,
        variant="treatment",
        users=4180,
        conversions=443,
        conversion_rate=Decimal("0.105980"),
    )
    session.commit()
