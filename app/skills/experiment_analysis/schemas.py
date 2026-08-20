"""Pydantic contracts for experiment_analysis."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class DecisionHint(StrEnum):
    SHIP_TREATMENT = "ship_treatment"
    KEEP_CONTROL = "keep_control"
    INCONCLUSIVE = "inconclusive"
    UNDERPOWERED = "underpowered"


class VariantInput(BaseModel):
    variant: str = Field(min_length=1)
    users: int = Field(ge=0)
    conversions: int = Field(ge=0)

    @model_validator(mode="after")
    def conversions_le_users(self) -> VariantInput:
        if self.conversions > self.users:
            raise ValueError("conversions cannot exceed users")
        return self

    @property
    def rate(self) -> float:
        return (self.conversions / self.users) if self.users > 0 else 0.0


class ExperimentCompareInput(BaseModel):
    control: VariantInput
    treatment: VariantInput
    alpha: float = Field(default=0.05, gt=0.0, lt=0.5)
    min_users_per_variant: int = Field(default=100, ge=1)


class VariantResult(BaseModel):
    variant: str
    users: int
    conversions: int
    conversion_rate: float


class ExperimentCompareResult(BaseModel):
    control: VariantResult
    treatment: VariantResult
    absolute_lift: float
    relative_lift: float | None
    ci_low: float
    ci_high: float
    z_score: float | None
    p_value: float | None
    alpha: float
    significant: bool
    decision_hint: DecisionHint
    notes: str


class ExperimentDesignProposal(BaseModel):
    name: str
    hypothesis: str
    primary_metric: str
    control_description: str
    treatment_description: str
    success_criteria: str
    grounded_in: str | None = None
