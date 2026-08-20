"""Repository upsert and funnel aggregation behavior."""

from datetime import date, datetime, timezone
from decimal import Decimal

from app.db.loader import load_synthetic_dataset
from app.db.repositories import AcquisitionRepository, VideoRepository
from app.db.synthetic import generate_synthetic_dataset


def test_video_upsert_is_idempotent(session) -> None:
    repo = VideoRepository(session)
    first = repo.upsert_by_youtube_id(
        youtube_video_id="syn0001",
        title="[SYNTHETIC] one",
        description="SYNTHETIC DATA",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        duration_seconds=600,
        channel_id="SYNTHETIC_CHANNEL",
        channel_title="Demo",
        topic="ETFs",
        is_synthetic=True,
        dataset_label="synthetic_v1",
    )
    second = repo.upsert_by_youtube_id(
        youtube_video_id="syn0001",
        title="[SYNTHETIC] one updated",
        description="SYNTHETIC DATA",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        duration_seconds=600,
        channel_id="SYNTHETIC_CHANNEL",
        channel_title="Demo",
        topic="ETFs",
        is_synthetic=True,
        dataset_label="synthetic_v1",
    )
    assert first.id == second.id
    assert second.title == "[SYNTHETIC] one updated"
    assert len(repo.list_all()) == 1


def test_acquisition_upsert_and_sum(session) -> None:
    video_repo = VideoRepository(session)
    video = video_repo.upsert_by_youtube_id(
        youtube_video_id="syn0099",
        title="[SYNTHETIC] funnel",
        description="SYNTHETIC DATA",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        duration_seconds=300,
        channel_id="SYNTHETIC_CHANNEL",
        channel_title="Demo",
        topic="Budgeting",
        is_synthetic=True,
        dataset_label="synthetic_v1",
    )
    repo = AcquisitionRepository(session)
    repo.upsert(
        metric_date=date(2026, 8, 1),
        channel="YouTube",
        topic="Budgeting",
        video_id=video.id,
        views=1000,
        visits=200,
        signups=40,
        activated_users=20,
        premium_users=4,
    )
    repo.upsert(
        metric_date=date(2026, 8, 1),
        channel="YouTube",
        topic="Budgeting",
        video_id=video.id,
        views=1100,
        visits=220,
        signups=44,
        activated_users=22,
        premium_users=5,
    )
    totals = repo.sum_funnel(start=date(2026, 8, 1), end=date(2026, 8, 1), channel="YouTube")
    assert totals["views"] == 1100
    assert totals["premium_users"] == 5


def test_load_synthetic_dataset_twice(session) -> None:
    dataset = generate_synthetic_dataset(seed=7, days=5, as_of=date(2026, 8, 20))
    counts_1 = load_synthetic_dataset(session, dataset)
    session.commit()
    counts_2 = load_synthetic_dataset(session, dataset)
    session.commit()
    assert counts_1 == counts_2
    assert counts_1["videos"] == len(dataset.videos)
    videos = VideoRepository(session).list_all()
    assert len(videos) == counts_1["videos"]
    assert all(v.is_synthetic for v in videos)


def test_experiment_conversion_rate_decimal(session) -> None:
    dataset = generate_synthetic_dataset(seed=3, days=10, as_of=date(2026, 8, 20))
    load_synthetic_dataset(session, dataset)
    session.commit()
    assert dataset.experiments[0].results[0].conversion_rate == Decimal("0.090000")
