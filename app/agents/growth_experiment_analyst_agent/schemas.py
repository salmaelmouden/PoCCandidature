"""Pydantic contracts for growth_experiment_analyst_agent."""

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
from app.skills.experiment_analysis.schemas import DecisionHint, ExperimentDesignProposal


class ExperimentMode(StrEnum):
    ANALYZE = "analyze"
    PROPOSE = "propose"


class ExperimentAnalystQuestion(BaseModel):
    question: str = Field(min_length=3)
    days: int = Field(default=30, ge=1, le=365)
    channel: str | None = None
    as_of: date | None = None
    experiment_key: str | None = None
    analyst_report: AnalystReport | None = None
    alpha: float = Field(default=0.05, gt=0.0, lt=0.5)


class ExperimentAnalystReport(BaseModel):
    question: str
    mode: ExperimentMode
    experiment_key: str | None = None
    decision_hint: DecisionHint | None = None
    design: ExperimentDesignProposal | None = None
    claims: list[EvidenceClaim]
    tool_calls: list[ToolInvocation]
    insufficient_evidence: bool = False
    notes: str = (
        "Stats come from experiment_analysis skill / DB rows. "
        "Design proposals do not invent historical conversion numbers."
    )


__all__ = [
    "ExperimentMode",
    "ExperimentAnalystQuestion",
    "ExperimentAnalystReport",
    "SemanticLabel",
    "EvidenceClaim",
    "ToolInvocation",
    "DecisionHint",
]
