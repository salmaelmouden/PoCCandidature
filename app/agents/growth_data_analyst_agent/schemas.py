"""Pydantic contracts for growth_data_analyst_agent."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class SemanticLabel(StrEnum):
    FACT = "FACT"
    INTERPRETATION = "INTERPRETATION"
    RECOMMENDATION = "RECOMMENDATION"


class AnalystQuestion(BaseModel):
    question: str = Field(min_length=3)
    days: int = Field(default=30, ge=1, le=365)
    channel: str | None = None
    as_of: date | None = None


class EvidenceClaim(BaseModel):
    label: SemanticLabel
    text: str
    source_tool: str | None = None
    numbers: dict[str, float | int | str | None] = Field(default_factory=dict)


class ToolInvocation(BaseModel):
    tool: str
    ok: bool
    summary: str
    detail: dict = Field(default_factory=dict)


class AnalystReport(BaseModel):
    question: str
    period_start: date
    period_end: date
    channel: str | None
    primary_driver: str | None
    claims: list[EvidenceClaim]
    tool_calls: list[ToolInvocation]
    insufficient_evidence: bool = False
    notes: str = (
        "FACT claims must trace to tool results. "
        "INTERPRETATION is reasoned from those facts. "
        "This agent does not issue RECOMMENDATIONs (strategist owns that)."
    )
