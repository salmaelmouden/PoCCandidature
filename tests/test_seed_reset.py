"""
Re-seeding a database written by an older generator.

The generator fix for the floored funnel does not travel with a deploy: it changes
what `generate_synthetic_dataset` produces, not what is already stored. These tests
cover the mechanism that makes the stored rows catch up — and the boundary that
keeps it from taking the real ingested catalogue with them.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db.loader import load_synthetic_dataset, purge_synthetic_dataset
from app.db.models import (
    Acquisition,
    AnalyticsSnapshot,
    Experiment,
    ExperimentResult,
    User,
    Video,
    VideoClassification,
    VideoDailyMetric,
)
from app.db.repositories import VideoDailyMetricRepository, VideoRepository
from app.db.synthetic import generate_synthetic_dataset

CATALOGUE_LABEL = "youtube_api"


def _count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def _ingest_catalogue_video(session) -> Video:
    """A row as the real YouTube ingestion writes it: not synthetic, other label."""
    video = VideoRepository(session).upsert_by_youtube_id(
        youtube_video_id="real_abc123",
        title="A real uploaded video",
        description="",
        published_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        duration_seconds=421,
        channel_id="UCRCCAnVyzDTcqNYh0pDcq7Q",
        channel_title="Real channel",
        topic="Unclassified",
        is_synthetic=False,
        dataset_label=CATALOGUE_LABEL,
    )
    VideoDailyMetricRepository(session).upsert(
        video_id=video.id,
        metric_date=date(2026, 2, 2),
        views=1000,
        likes=10,
        comments=1,
        is_synthetic=False,
        dataset_label=CATALOGUE_LABEL,
    )
    session.flush()
    return video


def test_purge_empties_every_synthetic_table(session) -> None:
    load_synthetic_dataset(session, generate_synthetic_dataset(seed=42, days=30))
    assert _count(session, Acquisition) > 0

    purge_synthetic_dataset(session)

    for model in (
        Video,
        VideoDailyMetric,
        Acquisition,
        User,
        Experiment,
        ExperimentResult,
        AnalyticsSnapshot,
    ):
        assert _count(session, model) == 0, model.__name__


def test_purge_cascades_to_classifications(session) -> None:
    """`video_classifications` carries no label of its own — it follows its video."""
    load_synthetic_dataset(session, generate_synthetic_dataset(seed=42, days=15))
    video_id = session.scalar(select(Video.id).limit(1))
    session.add(
        VideoClassification(
            video_id=video_id,
            topic="ETFs",
            hook_type="question",
            version="v1",
            classified_by="test",
        )
    )
    session.flush()
    assert _count(session, VideoClassification) == 1

    purge_synthetic_dataset(session)

    assert _count(session, VideoClassification) == 0


def test_purge_spares_the_ingested_catalogue(session) -> None:
    """
    The catalogue shares `videos` and `video_daily_metrics` with the synthetic
    dataset and is the one thing here that is not reproducible from a seed.
    """
    real = _ingest_catalogue_video(session)
    load_synthetic_dataset(session, generate_synthetic_dataset(seed=42, days=15))

    purge_synthetic_dataset(session)

    remaining = list(session.scalars(select(Video)))
    assert [v.id for v in remaining] == [real.id]
    assert _count(session, VideoDailyMetric) == 1


def test_reset_drops_rows_left_outside_a_slid_window(session) -> None:
    """
    `as_of` defaults to today, so a later re-seed generates a later window. Upserting
    alone cannot reach the days that fell off the leading edge: they keep whatever the
    previous generator wrote, which is exactly the floored premium the fix removed.
    """
    first_as_of = date(2026, 6, 1)
    second_as_of = first_as_of + timedelta(days=10)

    load_synthetic_dataset(
        session, generate_synthetic_dataset(seed=42, days=30, as_of=first_as_of)
    )
    oldest = session.scalar(select(func.min(Acquisition.metric_date)))

    # Without the purge the stale leading edge survives the re-seed.
    load_synthetic_dataset(
        session, generate_synthetic_dataset(seed=42, days=30, as_of=second_as_of)
    )
    assert session.scalar(select(func.min(Acquisition.metric_date))) == oldest

    purge_synthetic_dataset(session)
    load_synthetic_dataset(
        session, generate_synthetic_dataset(seed=42, days=30, as_of=second_as_of)
    )

    assert session.scalar(select(func.min(Acquisition.metric_date))) == second_as_of - timedelta(
        days=29
    )
    assert session.scalar(select(func.max(Acquisition.metric_date))) == second_as_of


def test_reset_leaves_no_users_from_the_previous_run(session) -> None:
    """
    `syn_user_*` keys come from a counter over signup volume, so a run that produces
    fewer signups never revisits the tail of the previous run's keys.
    """
    load_synthetic_dataset(session, generate_synthetic_dataset(seed=42, days=60))
    long_run_users = _count(session, User)

    purge_synthetic_dataset(session)
    load_synthetic_dataset(session, generate_synthetic_dataset(seed=42, days=20))
    short_run_users = _count(session, User)

    assert short_run_users < long_run_users


def test_reseed_reports_a_healthy_premium_stage(session) -> None:
    """
    The end state the re-seed exists for: once the stored rows come from the fixed
    generator, `activated → premium` is a real conversion rather than a total leak.
    """
    purge_synthetic_dataset(session)
    load_synthetic_dataset(session, generate_synthetic_dataset(seed=42, days=60))

    activated, premium = session.execute(
        select(func.sum(Acquisition.activated_users), func.sum(Acquisition.premium_users))
    ).one()

    assert activated > 0
    assert premium > 0
    assert 0.05 < premium / activated < 0.25
