"""growth_strategist_agent — recommendations grounded in analyst evidence."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.agents.growth_data_analyst_agent.schemas import (
    AnalystReport,
    EvidenceClaim,
    SemanticLabel,
    ToolInvocation,
)
from app.agents.growth_strategist_agent.config import StrategistConfig
from app.agents.growth_strategist_agent.prompts import DEFAULT_STRATEGY_QUESTION
from app.agents.growth_strategist_agent.schemas import (
    Priority,
    Recommendation,
    StrategistQuestion,
    StrategyReport,
)
from app.agents.growth_strategist_agent.tools import tool_get_analyst_report


class GrowthStrategistAgent:
    """
    Strategist: turns AnalystReport evidence into prioritized RECOMMENDATIONs.

    Phase 6 uses a deterministic playbook so demos and CI work without an LLM key.
    """

    name = "growth_strategist_agent"

    def __init__(self, config: StrategistConfig | None = None) -> None:
        self.config = config or StrategistConfig()

    def run(
        self, session: Session, question: StrategistQuestion | str | None = None
    ) -> StrategyReport:
        payload = self._normalize(question)
        tool_calls: list[ToolInvocation] = []

        if payload.analyst_report is not None:
            report = payload.analyst_report
            tool_calls.append(
                ToolInvocation(
                    tool="get_analyst_report",
                    ok=True,
                    summary="Used caller-provided AnalystReport (no re-run).",
                    detail={"primary_driver": report.primary_driver},
                )
            )
        else:
            try:
                report = tool_get_analyst_report(
                    session,
                    question=payload.question,
                    days=payload.days,
                    channel=payload.channel,
                    as_of=payload.as_of,
                )
                tool_calls.append(
                    ToolInvocation(
                        tool="get_analyst_report",
                        ok=True,
                        summary=f"Analyst primary_driver={report.primary_driver!r}",
                        detail={
                            "primary_driver": report.primary_driver,
                            "insufficient_evidence": report.insufficient_evidence,
                            "claim_count": len(report.claims),
                        },
                    )
                )
            except Exception as exc:  # noqa: BLE001 — surface as tool failure
                tool_calls.append(
                    ToolInvocation(
                        tool="get_analyst_report",
                        ok=False,
                        summary=f"Analyst tool failed: {exc}",
                        detail={"error": str(exc)},
                    )
                )
                fallback = payload.as_of or date.today()
                return StrategyReport(
                    question=payload.question,
                    period_start=fallback,
                    period_end=fallback,
                    channel=payload.channel,
                    recommendations=[],
                    claims=[
                        EvidenceClaim(
                            label=SemanticLabel.INTERPRETATION,
                            text="Insufficient evidence: analyst tool failed.",
                            source_tool="get_analyst_report",
                        )
                    ],
                    tool_calls=tool_calls,
                    insufficient_evidence=True,
                )

        recommendations, claims, insufficient = self._synthesize(payload.question, report)
        recommendations = recommendations[: self.config.max_recommendations]
        return StrategyReport(
            question=payload.question,
            period_start=report.period_start,
            period_end=report.period_end,
            channel=report.channel,
            recommendations=recommendations,
            claims=claims,
            tool_calls=tool_calls,
            analyst_primary_driver=report.primary_driver,
            insufficient_evidence=insufficient,
        )

    def _normalize(self, question: StrategistQuestion | str | None) -> StrategistQuestion:
        if question is None:
            return StrategistQuestion(question=DEFAULT_STRATEGY_QUESTION)
        if isinstance(question, str):
            return StrategistQuestion(question=question)
        return question

    def _synthesize(
        self, question: str, report: AnalystReport
    ) -> tuple[list[Recommendation], list[EvidenceClaim], bool]:
        claims: list[EvidenceClaim] = [
            EvidenceClaim(
                label=SemanticLabel.FACT,
                text=(
                    f"Strategist grounded on analyst primary_driver="
                    f"{report.primary_driver!r} "
                    f"(insufficient_evidence={report.insufficient_evidence})."
                ),
                source_tool="get_analyst_report",
                numbers={"analyst_claim_count": len(report.claims)},
            )
        ]

        if report.insufficient_evidence or not report.claims:
            claims.append(
                EvidenceClaim(
                    label=SemanticLabel.INTERPRETATION,
                    text="Insufficient analyst evidence — no grounded recommendations.",
                    source_tool="get_analyst_report",
                )
            )
            return [], claims, True

        # Carry forward key FACT numbers for traceability
        for c in report.claims:
            if c.label == SemanticLabel.FACT and c.numbers:
                claims.append(
                    EvidenceClaim(
                        label=SemanticLabel.FACT,
                        text=c.text,
                        source_tool=c.source_tool,
                        numbers=c.numbers,
                    )
                )
                break

        recs = self._playbook(report)
        if not recs:
            claims.append(
                EvidenceClaim(
                    label=SemanticLabel.INTERPRETATION,
                    text=(
                        "Analyst returned evidence but no playbook match; "
                        "defer specific actions until the driver is clearer."
                    ),
                    source_tool=None,
                )
            )
            return [], claims, True

        for rec in recs:
            claims.append(
                EvidenceClaim(
                    label=SemanticLabel.RECOMMENDATION,
                    text=f"[{rec.priority.value}] {rec.title}: {rec.action}",
                    source_tool="get_analyst_report",
                    numbers=rec.numbers,
                )
            )

        claims.append(
            EvidenceClaim(
                label=SemanticLabel.INTERPRETATION,
                text=(
                    f"Prioritized {len(recs)} action(s) for “{question.strip()}” "
                    f"from driver “{report.primary_driver}”."
                ),
                source_tool=None,
            )
        )
        return recs, claims, False

    def _playbook(self, report: AnalystReport) -> list[Recommendation]:
        driver = (report.primary_driver or "").lower()
        blob = " ".join(c.text.lower() for c in report.claims) + " " + driver
        recs: list[Recommendation] = []

        # Channel / Premium-rate pressure
        if any(k in blob for k in ("youtube", "premium_rate", "channel", "weakest")):
            channel_name = None
            for token in ("youtube", "linkedin", "instagram", "organic", "paid"):
                if token in driver or token in blob:
                    channel_name = token.title() if token != "youtube" else "YouTube"
                    if token == "linkedin":
                        channel_name = "LinkedIn"
                    break
            grounded = report.primary_driver or "channel premium_rate lag"
            recs.append(
                Recommendation(
                    priority=Priority.P0,
                    title="Fix Premium leak on weakest channel",
                    action=(
                        f"Audit signup→activation→Premium path for "
                        f"{channel_name or 'the weakest channel'}: "
                        "landing message match, paywall timing, and CTA clarity. "
                        "Compare Premium rate to the best channel before changing spend."
                    ),
                    rationale=(
                        "Analyst flagged channel-level Premium weakness; "
                        "fix conversion before scaling acquisition."
                    ),
                    grounded_in=grounded,
                    numbers={"driver": grounded},
                )
            )

        # Funnel bottleneck
        if "bottleneck" in blob or "→" in (report.primary_driver or ""):
            stage = report.primary_driver or "funnel bottleneck"
            recs.append(
                Recommendation(
                    priority=Priority.P0 if not recs else Priority.P1,
                    title="Relieve the funnel bottleneck stage",
                    action=(
                        f"Concentrate product and growth work on “{stage}”: "
                        "remove friction at that step, then re-measure dropoff vs the prior period."
                    ),
                    rationale="Analyst identified the highest dropoff stage as the primary constraint.",
                    grounded_in=stage,
                    numbers={"driver": stage},
                )
            )

        # Content gaps
        if "content gap" in blob or "topic=" in blob or "reach" in blob:
            topic = None
            for c in report.claims:
                if "topic" in (c.numbers or {}):
                    topic = c.numbers.get("topic")
                    break
            if topic is None and "topic=" in driver:
                topic = driver.split("topic=", 1)[-1].strip()
            recs.append(
                Recommendation(
                    priority=Priority.P1 if recs else Priority.P0,
                    title="Reposition high-reach / low-conversion content",
                    action=(
                        f"For topic “{topic or 'the flagged gap'}”, revise hooks and landing "
                        "alignment toward signup/Premium intent; pause scaling that format until "
                        "premium_rate improves vs peers."
                    ),
                    rationale="Analyst marked high reach with weak conversion as a content gap.",
                    grounded_in=report.primary_driver,
                    numbers={"topic": topic},
                )
            )

        # Period / Premium volume drop without more specific match
        if not recs and any(k in blob for k in ("premium", "period", "conversion", "delta")):
            recs.append(
                Recommendation(
                    priority=Priority.P1,
                    title="Stabilize Premium conversion before growth bets",
                    action=(
                        "Hold acquisition experiments; run a focused review of "
                        "activated→Premium conversion vs last period, then pick one "
                        "channel or stage to repair first."
                    ),
                    rationale="Analyst evidence shows Premium/period pressure without a sharper driver.",
                    grounded_in=report.primary_driver,
                )
            )

        # Soft default when we have a driver but no keyword match
        if not recs and report.primary_driver:
            recs.append(
                Recommendation(
                    priority=Priority.P2,
                    title="Act on the stated primary driver",
                    action=(
                        f"Treat “{report.primary_driver}” as the next growth focus: "
                        "define one measurable fix and re-run the analyst after one period."
                    ),
                    rationale="Analyst produced a primary driver; keep the action tightly scoped.",
                    grounded_in=report.primary_driver,
                )
            )

        return recs
