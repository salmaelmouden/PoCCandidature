"""Unit tests for dashboard application service."""

from __future__ import annotations

from datetime import date

from app.db.repositories import AcquisitionRepository
from app.services.dashboard import (
    get_acquisition,
    get_content,
    get_funnel,
    get_overview,
    resolve_period,
)


def _seed(session) -> None:
    repo = AcquisitionRepository(session)
    # current window relative to as_of=2026-08-20, days=7 → 2026-08-14..20
    repo.upsert(
        metric_date=date(2026, 8, 18),
        channel="YouTube",
        topic="Crypto",
        video_id=None,
        views=1000,
        visits=200,
        signups=20,
        activated_users=10,
        premium_users=1,
    )
    repo.upsert(
        metric_date=date(2026, 8, 18),
        channel="LinkedIn",
        topic="ETFs",
        video_id=None,
        views=200,
        visits=80,
        signups=40,
        activated_users=30,
        premium_users=12,
    )
    # previous window for days=7: 2026-08-07..13
    repo.upsert(
        metric_date=date(2026, 8, 10),
        channel="YouTube",
        topic="Crypto",
        video_id=None,
        views=800,
        visits=160,
        signups=24,
        activated_users=12,
        premium_users=3,
    )
    session.commit()


def test_resolve_period() -> None:
    period = resolve_period(7, as_of=date(2026, 8, 20))
    assert period.start == date(2026, 8, 14)
    assert period.end == date(2026, 8, 20)
    assert period.previous_end == date(2026, 8, 13)
    assert period.previous_start == date(2026, 8, 7)


def test_get_overview(session) -> None:
    _seed(session)
    snap = get_overview(session, days=7, as_of=date(2026, 8, 20))
    assert snap.current_counts["views"] == 1200
    assert snap.current_counts["premium_users"] == 13
    assert snap.has_synthetic is True
    assert "synthetic_v1" in snap.dataset_labels
    assert snap.funnel.bottleneck_from_stage is not None


def test_get_overview_channel_filter(session) -> None:
    _seed(session)
    snap = get_overview(session, days=7, channel="YouTube", as_of=date(2026, 8, 20))
    assert snap.current_counts["views"] == 1000
    assert snap.channel == "YouTube"


def test_get_acquisition(session) -> None:
    _seed(session)
    snap = get_acquisition(session, days=7, as_of=date(2026, 8, 20))
    channels = {row.channel for row in snap.rows}
    assert channels == {"YouTube", "LinkedIn"}
    linkedin = next(row for row in snap.rows if row.channel == "LinkedIn")
    assert linkedin.signups == 40


def test_get_content_and_funnel(session) -> None:
    _seed(session)
    content = get_content(session, days=7, as_of=date(2026, 8, 20))
    assert content.ranked
    assert content.topics
    funnel = get_funnel(session, days=7, channel="YouTube", as_of=date(2026, 8, 20))
    assert funnel.comparison.current.counts.views == 1000
    assert "activated_users_to_premium_users" in funnel.comparison.conversion_rate_deltas
