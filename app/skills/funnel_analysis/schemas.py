"""Schemas for funnel_analysis skill."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


FUNNEL_STAGE_ORDER: tuple[str, ...] = (
    "views",
    "visits",
    "signups",
    "activated_users",
    "premium_users",
)


class FunnelCounts(BaseModel):
    """Absolute counts at each funnel stage."""

    views: int = Field(ge=0)
    visits: int = Field(ge=0)
    signups: int = Field(ge=0)
    activated_users: int = Field(ge=0)
    premium_users: int = Field(ge=0)

    @model_validator(mode="after")
    def stages_should_not_increase(self) -> FunnelCounts:
        values = [
            self.views,
            self.visits,
            self.signups,
            self.activated_users,
            self.premium_users,
        ]
        for previous, current in zip(values[:-1], values[1:], strict=True):
            if current > previous:
                raise ValueError(
                    "Funnel stage counts must be non-increasing "
                    f"(got {values} for {FUNNEL_STAGE_ORDER})"
                )
        return self


class StageConversion(BaseModel):
    from_stage: str
    to_stage: str
    rate: float = Field(ge=0.0, le=1.0)
    from_count: int
    to_count: int


class StageDropoff(BaseModel):
    from_stage: str
    to_stage: str
    dropoff_count: int = Field(ge=0)
    dropoff_rate: float = Field(ge=0.0, le=1.0)


class FunnelResult(BaseModel):
    counts: FunnelCounts
    conversions: list[StageConversion]
    dropoffs: list[StageDropoff]
    bottleneck_from_stage: str | None
    bottleneck_to_stage: str | None
    bottleneck_dropoff_rate: float | None


class FunnelPeriodComparison(BaseModel):
    current: FunnelResult
    previous: FunnelResult
    absolute_deltas: dict[str, int]
    relative_deltas: dict[str, float | None]
    conversion_rate_deltas: dict[str, float | None]
