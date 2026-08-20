"""Typed tools for growth_strategist_agent — wraps analyst, no SQL."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.agents.growth_data_analyst_agent import AnalystQuestion, GrowthDataAnalystAgent
from app.agents.growth_data_analyst_agent.schemas import AnalystReport


def tool_get_analyst_report(
    session: Session,
    *,
    question: str,
    days: int = 30,
    channel: str | None = None,
    as_of: date | None = None,
) -> AnalystReport:
    """Run the data analyst and return its structured report."""
    return GrowthDataAnalystAgent().run(
        session,
        AnalystQuestion(question=question, days=days, channel=channel, as_of=as_of),
    )
