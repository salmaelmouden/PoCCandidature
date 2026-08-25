"""Contracts for the description-CTA reading — the funnel's public entry point.

This skill reads *where the door is*, never who walks through it. A description
is the only part of the acquisition path a channel exposes publicly: whether a
link to the product exists, whether it is visible before the reader clicks
"plus", and whether it carries anything an analytics tool could attribute a
signup to. None of that is a conversion measurement, and nothing here estimates
one — see ``skill.py`` for the boundary.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.skills.public_signal_analysis import SHORT_MAX_SECONDS, VideoFormat

FOLD_LINES = 3
"""Rendered lines YouTube shows before collapsing the description behind "plus".

An approximation, and deliberately a visible one: the real cut depends on the
client, the viewport width and whether the video carries chapters. The report
therefore carries the raw character offset of every link as well, so a reader
who disagrees with this threshold can still read the distribution underneath it.
"""

WRAP_COLUMNS = 80
"""Characters per rendered line used to approximate wrapping.

YouTube truncates by rendered lines, not by characters, so a long first
paragraph pushes a link out of view even at a small character offset. Counting
wrapped lines models that; counting characters alone would not.
"""

THIN_SLICE = 10
"""Below this many videos a slice is reported but marked, never used as a rule."""


class LinkKind(StrEnum):
    """Why a domain is, or is not, eligible to be the catalogue's product link."""

    PRODUCT = "product"
    PLATFORM = "platform"
    SOCIAL = "social"


class TrackingState(StrEnum):
    """What the link says about attribution — from the URL text alone.

    ``OPAQUE`` exists because a shortener or a ``go.`` redirect can append
    tracking server-side, invisibly. Folding those into ``UNTRACKED`` would
    manufacture a finding out of something the public data cannot settle.
    """

    TRACKED = "tracked"
    OPAQUE = "opaque"
    UNTRACKED = "untracked"
    ABSENT = "absent"


class VideoDescription(BaseModel):
    """One video, restricted to what a description reading needs.

    Deliberately independent of :class:`VideoClassification`: a description
    carries a link whether or not a classifier has seen the video, so this
    reading covers the whole ingested catalogue rather than the classified
    subset the reach index is limited to.
    """

    youtube_video_id: str
    title: str
    published_at: datetime
    duration_seconds: int = Field(ge=0)
    views: int = Field(ge=0)
    description: str = ""

    @property
    def video_format(self) -> VideoFormat:
        return (
            VideoFormat.SHORT
            if self.duration_seconds <= SHORT_MAX_SECONDS
            else VideoFormat.LONG
        )

    @property
    def published_year(self) -> int:
        return self.published_at.year


class LinkPlacement(BaseModel):
    """Where the product link sits in one description, or that it is missing."""

    youtube_video_id: str
    title: str
    video_format: VideoFormat
    published_year: int
    views: int
    described: bool
    links_total: int
    has_primary: bool
    first_offset: int | None = None
    rendered_line: int | None = None
    above_fold: bool = False
    tracking: TrackingState = TrackingState.ABSENT
    primary_url: str | None = None
    cta_line: str | None = None


class DomainStat(BaseModel):
    """One linked domain and how much of the catalogue points at it."""

    domain: str
    kind: LinkKind
    videos: int
    share_of_catalogue: float


class CtaLineStat(BaseModel):
    """One call-to-action wording, with the URL replaced by a placeholder."""

    template: str
    videos: int


class PlacementStat(BaseModel):
    """One slice of the catalogue — a format, a publication year — and its door.

    Counts rather than ratios, because the denominator changes meaning between
    them: ``above_fold`` is a share of the videos that *have* a link, while
    ``with_primary`` is a share of the videos in the slice. Storing both
    numerators next to their own denominators keeps a caller from dividing by
    the wrong one.
    """

    value: str
    videos: int
    with_primary: int
    above_fold: int
    tracked: int
    views: int
    views_with_primary: int
    views_above_fold: int
    median_offset: float | None = None

    @property
    def share_with_primary(self) -> float:
        return self.with_primary / self.videos if self.videos else 0.0

    @property
    def share_above_fold(self) -> float:
        """Of the videos that carry a link — not of the slice."""
        return self.above_fold / self.with_primary if self.with_primary else 0.0

    @property
    def share_tracked(self) -> float:
        return self.tracked / self.with_primary if self.with_primary else 0.0

    @property
    def view_share_with_primary(self) -> float:
        """Cumulated views landing on a video that carries a link.

        Lifetime views, not impressions over a period: a 2021 video has had five
        years to accumulate. It weights the finding by audience without
        pretending to be a traffic measurement.
        """
        return self.views_with_primary / self.views if self.views else 0.0

    @property
    def view_share_above_fold(self) -> float:
        return self.views_above_fold / self.views if self.views else 0.0

    @property
    def is_thin(self) -> bool:
        return self.videos < THIN_SLICE


class CtaCoverage(BaseModel):
    """What the reading ran on, and how the product domain was chosen."""

    videos_total: int
    described: int
    with_any_link: int
    with_primary: int
    primary_domain: str | None
    primary_domain_reason: str


class CtaReport(BaseModel):
    """Skill output — an evidence table about placement, never about conversion."""

    period_start: datetime
    period_end: datetime
    coverage: CtaCoverage
    domains: list[DomainStat]
    overall: PlacementStat
    by_format: list[PlacementStat]
    by_year: list[PlacementStat]
    cta_lines: list[CtaLineStat]
    placements: list[LinkPlacement]
