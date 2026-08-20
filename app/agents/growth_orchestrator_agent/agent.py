"""growth_orchestrator_agent — route specialists and synthesize (ADR-004)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.growth_data_analyst_agent import AnalystQuestion, GrowthDataAnalystAgent
from app.agents.growth_data_analyst_agent.schemas import EvidenceClaim, SemanticLabel
from app.agents.growth_orchestrator_agent.config import OrchestratorConfig
from app.agents.growth_orchestrator_agent.prompts import DEFAULT_ORCHESTRATOR_QUESTION
from app.agents.growth_orchestrator_agent.routing import classify_route
from app.agents.growth_orchestrator_agent.schemas import (
    OrchestratorQuestion,
    OrchestratorResponse,
    RouteKind,
)
from app.agents.growth_strategist_agent import GrowthStrategistAgent, StrategistQuestion


class GrowthOrchestratorAgent:
    """
    Primary AI entrypoint: classifies route, calls specialists, synthesizes summary.

    Does not reimplement analyst or strategist logic.
    """

    name = "growth_orchestrator_agent"

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        self.config = config or OrchestratorConfig()
        self._analyst = GrowthDataAnalystAgent()
        self._strategist = GrowthStrategistAgent()

    def run(
        self, session: Session, question: OrchestratorQuestion | str | None = None
    ) -> OrchestratorResponse:
        payload = self._normalize(question)
        route = classify_route(payload.question)
        agents_called: list[str] = []

        analyst_report = self._analyst.run(
            session,
            AnalystQuestion(
                question=payload.question,
                days=payload.days,
                channel=payload.channel,
                as_of=payload.as_of,
            ),
        )
        agents_called.append(self._analyst.name)

        strategy_report = None
        if route == RouteKind.ANALYST_THEN_STRATEGIST:
            strategy_report = self._strategist.run(
                session,
                StrategistQuestion(
                    question=payload.question,
                    days=payload.days,
                    channel=payload.channel,
                    as_of=payload.as_of,
                    analyst_report=analyst_report,
                ),
            )
            agents_called.append(self._strategist.name)

        claims = self._merge_claims(route, analyst_report, strategy_report)
        summary = self._summarize(route, analyst_report, strategy_report)
        insufficient = analyst_report.insufficient_evidence or (
            strategy_report.insufficient_evidence if strategy_report else False
        )

        return OrchestratorResponse(
            question=payload.question,
            route=route,
            agents_called=agents_called,
            period_start=analyst_report.period_start,
            period_end=analyst_report.period_end,
            channel=analyst_report.channel,
            summary=summary,
            analyst_report=analyst_report,
            strategy_report=strategy_report,
            claims=claims,
            insufficient_evidence=insufficient,
        )

    def _normalize(self, question: OrchestratorQuestion | str | None) -> OrchestratorQuestion:
        if question is None:
            return OrchestratorQuestion(question=DEFAULT_ORCHESTRATOR_QUESTION)
        if isinstance(question, str):
            return OrchestratorQuestion(question=question)
        return question

    def _merge_claims(
        self,
        route: RouteKind,
        analyst_report,
        strategy_report,
    ) -> list[EvidenceClaim]:
        agents = [self._analyst.name] + (
            [self._strategist.name] if strategy_report else []
        )
        claims: list[EvidenceClaim] = [
            EvidenceClaim(
                label=SemanticLabel.FACT,
                text=f"Orchestrator route={route.value}; agents={', '.join(agents)}.",
                source_tool=None,
                numbers={"route": route.value},
            )
        ]
        # Keep analyst interpretations/facts (cap for UI)
        for c in analyst_report.claims[:6]:
            claims.append(c)
        if strategy_report:
            for c in strategy_report.claims:
                if c.label == SemanticLabel.RECOMMENDATION:
                    claims.append(c)
        return claims

    def _summarize(self, route: RouteKind, analyst_report, strategy_report) -> str:
        driver = analyst_report.primary_driver or "no clear primary driver"
        if route == RouteKind.ANALYST_ONLY:
            return (
                f"Analysis only. Primary driver: {driver}. "
                f"{'Insufficient evidence flagged.' if analyst_report.insufficient_evidence else ''}"
            ).strip()

        if not strategy_report or not strategy_report.recommendations:
            return (
                f"Routed to strategist after analysis (driver: {driver}), "
                "but no grounded recommendations were produced."
            )

        tops = "; ".join(
            f"[{r.priority.value}] {r.title}" for r in strategy_report.recommendations[:3]
        )
        return f"Driver: {driver}. Recommended next actions: {tops}."
