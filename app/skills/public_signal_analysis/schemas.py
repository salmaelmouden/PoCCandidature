"""Contracts for analysis built only on publicly observable YouTube signals."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

SHORT_MAX_SECONDS = 60
"""YouTube Shorts threshold. 52% of the Finary catalogue sits at or under it."""

MIN_COHORT_SIZE = 5
"""Below this, a cohort median is noise — those videos are excluded and reported."""


class VideoFormat(StrEnum):
    SHORT = "short"
    LONG = "long"


class PublicVideoSignal(BaseModel):
    """One video, restricted to what the public Data API actually returns."""

    youtube_video_id: str
    title: str
    published_at: datetime
    duration_seconds: int = Field(ge=0)
    views: int = Field(ge=0)
    likes: int = Field(ge=0)
    comments: int = Field(ge=0)
    topic: str
    hook_type: str

    @property
    def video_format(self) -> VideoFormat:
        return (
            VideoFormat.SHORT
            if self.duration_seconds <= SHORT_MAX_SECONDS
            else VideoFormat.LONG
        )

    @property
    def cohort_key(self) -> str:
        """Format × publication quarter — the unit view counts are comparable within."""
        quarter = (self.published_at.month - 1) // 3 + 1
        return f"{self.video_format.value}:{self.published_at.year}Q{quarter}"

    @property
    def engagement_rate(self) -> float:
        """(likes + comments) / views. Far less growth-confounded than raw views."""
        if self.views <= 0:
            return 0.0
        return (self.likes + self.comments) / self.views


class DimensionStat(BaseModel):
    """Aggregate for one value of a dimension (a topic, a hook, a format)."""

    value: str
    videos: int
    median_reach_index: float
    median_engagement_rate: float
    total_views: int
    share_of_catalogue: float


class CohortCoverage(BaseModel):
    """What the reach index could and could not be computed on."""

    videos_total: int
    videos_indexed: int
    videos_excluded: int
    cohorts_used: int
    cohorts_dropped: int
    excluded_reason: str = (
        f"cohort (format × quarter) smaller than {MIN_COHORT_SIZE} videos"
    )


class PublicSignalReport(BaseModel):
    """Skill output — an evidence table, deliberately not a narrative."""

    period_start: datetime
    period_end: datetime
    coverage: CohortCoverage
    by_format: list[DimensionStat]
    by_topic: list[DimensionStat]
    by_hook: list[DimensionStat]
    by_topic_short: list[DimensionStat]
    by_topic_long: list[DimensionStat]
    by_hook_short: list[DimensionStat]
    by_hook_long: list[DimensionStat]
