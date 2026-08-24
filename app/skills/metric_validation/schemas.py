"""Schemas for metric_validation skill."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

#: Upstream volume at or above which an empty downstream stage stops being
#: ordinary smallness and starts being a measurement fault. Below it, a stage can
#: legitimately be empty — 0 Premium out of 12 activations is a slow week, not a
#: broken pipeline. Blocking there would make the validator cry wolf on every
#: low-traffic slice and train its readers to skip it.
MIN_SIGNIFICANT_UPSTREAM = 100


class WarningCode(StrEnum):
    """Why a funnel result should not be read as a growth finding."""

    TERMINAL_STAGE_EMPTY = "terminal_stage_empty"
    IMPOSSIBLE_DROPOFF = "impossible_dropoff"
    COHORT_TOO_SMALL = "cohort_too_small"

    @property
    def message_template(self) -> str:
        return _MESSAGES[self]


_MESSAGES: dict[WarningCode, str] = {
    WarningCode.TERMINAL_STAGE_EMPTY: (
        "The final funnel stage is empty while {upstream_count:,} users reached the "
        "stage before it. A conversion rate of exactly zero at this volume is far "
        "more often a measurement fault than a growth event — treat it as data to "
        "verify, not as a leak to fix."
    ),
    WarningCode.IMPOSSIBLE_DROPOFF: (
        "Stage “{stage}” is empty while {upstream_count:,} users reached “{upstream_stage}”. "
        "Traffic does not convert at exactly 0 % mid-funnel; this is a pipeline or "
        "attribution fault."
    ),
    WarningCode.COHORT_TOO_SMALL: (
        "Stage “{stage}” is empty, but only {upstream_count:,} users reached "
        "“{upstream_stage}” — below the {threshold:,} needed to tell an empty stage "
        "apart from ordinary smallness. Reported for context, not as a fault."
    ),
}


class DataWarning(BaseModel):
    """One reason to distrust a stage, with the numbers that justify it."""

    code: WarningCode
    stage: str
    upstream_stage: str | None = None
    #: Blocking warnings forbid downstream urgency. Non-blocking ones are context.
    blocking: bool = False
    message: str
    numbers: dict[str, int | float | str | None] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    warnings: list[DataWarning] = Field(default_factory=list)

    @property
    def has_blocking(self) -> bool:
        return any(w.blocking for w in self.warnings)

    @property
    def blocking_stages(self) -> frozenset[str]:
        return frozenset(w.stage for w in self.warnings if w.blocking)


__all__ = [
    "MIN_SIGNIFICANT_UPSTREAM",
    "DataWarning",
    "ValidationResult",
    "WarningCode",
]
