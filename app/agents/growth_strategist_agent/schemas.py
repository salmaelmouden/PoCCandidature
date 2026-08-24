"""Pydantic contracts for growth_strategist_agent."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field

from app.agents.growth_data_analyst_agent.schemas import (
    AnalystReport,
    EvidenceClaim,
    SemanticLabel,
    ToolInvocation,
)
from app.skills.metric_validation import DataWarning


class Priority(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class StrategistQuestion(BaseModel):
    question: str = Field(min_length=3)
    days: int = Field(default=30, ge=1, le=365)
    channel: str | None = None
    as_of: date | None = None
    analyst_report: AnalystReport | None = None
    #: Verdicts from `metric_validation`, produced by the application service before
    #: the agent runs. Passed in rather than fetched: the warnings must also reach
    #: reports generated with no agent in the loop, so the service owns the call.
    data_warnings: list[DataWarning] = Field(default_factory=list)


class Recommendation(BaseModel):
    priority: Priority
    title: str
    action: str
    rationale: str
    grounded_in: str | None = None
    numbers: dict[str, float | int | str | None] = Field(default_factory=dict)
    #: Funnel stage this recommendation acts on, when it acts on one. Declared as a
    #: field rather than inferred from prose so the guardrail can match a
    #: recommendation to a warning without parsing English.
    target_stage: str | None = None


class StrategyReport(BaseModel):
    question: str
    period_start: date
    period_end: date
    channel: str | None
    recommendations: list[Recommendation]
    claims: list[EvidenceClaim]
    tool_calls: list[ToolInvocation]
    analyst_primary_driver: str | None = None
    insufficient_evidence: bool = False
    notes: str = (
        "RECOMMENDATION claims must be grounded in AnalystReport facts. "
        "This agent does not invent metrics or run experiments (Phase 7)."
    )


__all__ = [
    "Priority",
    "StrategistQuestion",
    "Recommendation",
    "StrategyReport",
    "SemanticLabel",
    "EvidenceClaim",
    "AnalystReport",
    "ToolInvocation",
    "DataWarning",
]
