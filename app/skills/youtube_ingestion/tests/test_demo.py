"""Demo channel constants for YouTube ingest docs/CLI."""

from app.skills.youtube_ingestion.demo import (
    DEMO_YOUTUBE_CHANNEL_ID,
    DEMO_YOUTUBE_CHANNEL_NAME,
)


def test_demo_channel_is_public_uc_id() -> None:
    assert DEMO_YOUTUBE_CHANNEL_ID.startswith("UC")
    assert len(DEMO_YOUTUBE_CHANNEL_ID) >= 20
    assert "Two Cents" in DEMO_YOUTUBE_CHANNEL_NAME
