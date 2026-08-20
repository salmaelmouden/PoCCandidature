"""Tests for deterministic synthetic dataset generation."""

from datetime import date, timedelta

from app.db.constants import DATASET_LABEL, Channel
from app.db.synthetic import generate_synthetic_dataset


def test_generator_is_deterministic() -> None:
    as_of = date(2026, 8, 20)
    a = generate_synthetic_dataset(seed=42, days=30, as_of=as_of)
    b = generate_synthetic_dataset(seed=42, days=30, as_of=as_of)
    assert len(a.videos) == len(b.videos)
    assert a.videos[0].youtube_video_id == b.videos[0].youtube_video_id
    assert a.acquisitions[10].premium_users == b.acquisitions[10].premium_users
    assert a.label == DATASET_LABEL
    assert a.is_synthetic is True


def test_videos_are_labelled_synthetic() -> None:
    dataset = generate_synthetic_dataset(seed=1, days=14, as_of=date(2026, 8, 20))
    assert all(v.title.startswith("[SYNTHETIC]") for v in dataset.videos)
    assert all("SYNTHETIC DATA" in v.description for v in dataset.videos)


def test_youtube_premium_declines_in_recent_window() -> None:
    as_of = date(2026, 8, 20)
    dataset = generate_synthetic_dataset(seed=42, days=60, as_of=as_of)
    current_start = as_of - timedelta(days=13)
    previous_start = as_of - timedelta(days=27)
    previous_end = as_of - timedelta(days=14)

    def rate(start: date, end: date) -> float:
        activated = 0
        premium = 0
        for row in dataset.acquisitions:
            if row.channel != Channel.YOUTUBE.value:
                continue
            if start <= row.metric_date <= end:
                activated += row.activated_users
                premium += row.premium_users
        return premium / activated if activated else 0.0

    current = rate(current_start, as_of)
    previous = rate(previous_start, previous_end)
    assert previous > 0
    assert current < previous


def test_snapshots_include_youtube_and_overall() -> None:
    dataset = generate_synthetic_dataset(seed=42, days=45, as_of=date(2026, 8, 20))
    keys = {s.dimension_key for s in dataset.snapshots}
    assert "overall:current_14d" in keys
    assert "youtube:current_14d" in keys
    assert "overall:previous_14d" in keys
    assert "youtube:previous_14d" in keys
