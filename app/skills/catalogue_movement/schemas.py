"""Schemas for catalogue_movement skill."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

#: A dimension value below this many videos is omitted rather than reported: a share
#: computed over three videos is arithmetic, not a finding. Same threshold and same
#: reasoning as `public_signal_analysis`.
MIN_DIMENSION_VIDEOS = 5

#: Publication-age buckets, measured back from the end of the observed window.
#: Boundaries in days; the last bucket is open-ended.
AGE_BUCKETS: tuple[tuple[str, int], ...] = (
    ("7 derniers jours", 7),
    ("8 à 30 jours", 30),
    ("1 à 3 mois", 90),
)
AGE_BUCKET_OLDEST = "plus de 3 mois"


class VideoSnapshotPair(BaseModel):
    """One video seen at two points in time."""

    youtube_video_id: str
    title: str
    published_at: datetime
    duration_seconds: int = Field(ge=0)
    topic: str | None = None
    hook_type: str | None = None
    views_start: int = Field(ge=0)
    views_end: int = Field(ge=0)

    @property
    def delta_views(self) -> int:
        """Signed on purpose — YouTube revises counters downward often enough."""
        return self.views_end - self.views_start

    @property
    def video_format(self) -> str:
        return "Short" if self.duration_seconds <= 60 else "Long"


class MovementStat(BaseModel):
    dimension_value: str
    videos: int
    videos_moved: int
    delta_views: int
    median_delta_views: float
    share_of_catalogue: float
    #: Share of the window's total movement. Undefined when total movement is zero.
    share_of_movement: float | None


class TopMover(BaseModel):
    youtube_video_id: str
    title: str
    video_format: str
    published_at: date
    delta_views: int
    views_end: int
    topic: str | None = None


class MovementCoverage(BaseModel):
    """What was measured, and at what resolution — never left implicit."""

    videos_paired: int
    videos_moved: int
    videos_unchanged: int
    total_delta_views: int
    period_start: date
    period_end: date
    #: Days between the two snapshots. One day is an observation; it is not a trend,
    #: and the memo is required to say so rather than let the reader assume otherwise.
    resolution_days: int

    @property
    def is_single_day(self) -> bool:
        return self.resolution_days <= 1


class DimensionCoverage(BaseModel):
    """What a dimension could not account for — reported, never silently absorbed."""

    dimension: str
    videos_omitted: int
    delta_views_omitted: int
    reason: str


class MovementReport(BaseModel):
    coverage: MovementCoverage
    by_format: list[MovementStat]
    by_publication_age: list[MovementStat]
    by_topic: list[MovementStat]
    by_hook: list[MovementStat]
    top_movers: list[TopMover]
    #: One entry per dimension that dropped videos, so a reader can tell the
    #: difference between "these shares sum to 81 %" and "these are all the shares".
    omissions: list[DimensionCoverage] = Field(default_factory=list)


class MovementError(ValueError):
    """Raised when movement cannot be computed at all."""


__all__ = [
    "AGE_BUCKETS",
    "AGE_BUCKET_OLDEST",
    "MIN_DIMENSION_VIDEOS",
    "MovementCoverage",
    "MovementError",
    "MovementReport",
    "MovementStat",
    "TopMover",
    "VideoSnapshotPair",
]
