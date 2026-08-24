"""catalogue_movement skill package."""

from app.skills.catalogue_movement.schemas import (
    AGE_BUCKET_OLDEST,
    AGE_BUCKETS,
    MIN_DIMENSION_VIDEOS,
    MovementCoverage,
    MovementError,
    MovementReport,
    MovementStat,
    TopMover,
    VideoSnapshotPair,
)
from app.skills.catalogue_movement.skill import analyse_movement

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
    "analyse_movement",
]
