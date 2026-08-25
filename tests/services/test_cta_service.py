"""Service-level tests for the funnel-entry-point reading — in-memory DB, no network."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.db.models import Video, VideoDailyMetric
from app.services.public_signals import build_cta_report, load_descriptions

PRODUCT = "https://finary.com/app"


def _video(
    session: Session,
    vid: str,
    *,
    description: str = "",
    label: str = "youtube_api",
    duration: int = 600,
    snapshots: tuple[tuple[date, int], ...] = ((date(2026, 8, 20), 1_000),),
) -> Video:
    video = Video(
        youtube_video_id=vid,
        title=f"titre {vid}",
        description=description,
        published_at=datetime(2025, 6, 1, tzinfo=UTC),
        duration_seconds=duration,
        channel_id="UC_test",
        channel_title="Test",
        topic="Crypto",
        is_synthetic=label != "youtube_api",
        dataset_label=label,
    )
    session.add(video)
    session.flush()
    for metric_date, views in snapshots:
        session.add(
            VideoDailyMetric(
                video_id=video.id,
                metric_date=metric_date,
                views=views,
                likes=10,
                comments=2,
                is_synthetic=label != "youtube_api",
                dataset_label=label,
            )
        )
    session.flush()
    return video


def test_empty_catalogue_returns_none_rather_than_raising(session: Session) -> None:
    """A fresh deploy has no rows yet, and that is an ordinary state, not an error."""
    assert build_cta_report(session) is None


def test_synthetic_rows_are_never_read(session: Session) -> None:
    _video(session, "syn", description=PRODUCT, label="synthetic_v1")

    assert load_descriptions(session) == []
    assert build_cta_report(session) is None


def test_freshest_snapshot_wins(session: Session) -> None:
    _video(
        session,
        "a",
        description=PRODUCT,
        snapshots=((date(2026, 8, 1), 500), (date(2026, 8, 20), 900)),
    )

    (loaded,) = load_descriptions(session)

    assert loaded.views == 900


def test_reading_needs_no_classification(session: Session) -> None:
    """The whole point of this reading: no `video_classifications` row exists here."""
    _video(session, "a", description=f"Essayez : {PRODUCT}")
    _video(session, "b", description="", duration=30)

    report = build_cta_report(session)

    assert report is not None
    assert report.coverage.videos_total == 2
    assert report.coverage.with_primary == 1
    assert report.coverage.primary_domain == "finary.com"


def test_missing_description_is_not_a_missing_video(session: Session) -> None:
    _video(session, "a", description="")

    report = build_cta_report(session)

    assert report is not None
    assert report.coverage.videos_total == 1
    assert report.coverage.described == 0


def test_caller_can_pin_the_product_domain(session: Session) -> None:
    _video(session, "a", description="https://autre.example/x")

    report = build_cta_report(session, primary_domain="autre.example")

    assert report is not None
    assert report.coverage.with_primary == 1
