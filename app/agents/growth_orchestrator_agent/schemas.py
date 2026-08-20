"""Pydantic contracts for growth_orchestrator_agent."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field

from app.agents.growth_data_analyst_agent.schemas import AnalystReport, EvidenceClaim
from app.agents.growth_strategist_agent.schemas import StrategyReport


class RouteKind(StrEnum):
    ANALYST_ONLY = "analyst_only"
    ANALYST_THEN_STRATEGIST = "analyst_then_strategist"


class OrchestratorQuestion(BaseModel):
    question: str = Field(min_length=3)
    days: int = Field(default=30, ge=1, le=365)
    channel: str | None = None
    as_of: date | None = None


class OrchestratorResponse(BaseModel):
    question: str
    route: RouteKind
    agents_called: list[str]
    period_start: date | None = None
    period_end: date | None = None
    channel: str | None = None
    summary: str
    analyst_report: AnalystReport | None = None
    strategy_report: StrategyReport | None = None
    claims: list[EvidenceClaim] = Field(default_factory=list)
    insufficient_evidence: bool = False
    notes: str = (
        "Orchestrator routes and synthesizes; it does not reimplement specialist logic (ADR-004)."
    )
