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
from app.observability import observation
from app.skills.funnel_analysis.schemas import FUNNEL_STAGE_ORDER
from app.skills.metric_validation import DataWarning


def _stage_mentioned_in(text: str | None) -> str | None:
    """Which funnel stage a free-text driver refers to, if any.

    The analyst states its bottleneck as prose ("activated_users → premium_users"),
    so the stage has to be recovered before the guardrail can match a recommendation
    to a warning. Last match wins: in a transition the stage being acted on is the
    destination.
    """
    if not text:
        return None
    lowered = text.lower()
    found = [stage for stage in FUNNEL_STAGE_ORDER if stage in lowered]
    return found[-1] if found else None


def _verification_recommendation(warning: DataWarning) -> Recommendation:
    """The item that stands in for withheld advice on an untrustworthy stage.

    Deliberately P2: the whole point is that this is not urgent growth work. The
    wording stays on the measurement — naming a mechanism (paywall, pricing, CTA)
    would smuggle back the causal story the warning says we cannot support.
    """
    return Recommendation(
        priority=Priority.P2,
        title=f"Verify the “{warning.stage}” measurement before acting on it",
        action=(
            f"Confirm that “{warning.stage}” is being recorded correctly for this "
            "period — check the ingestion and aggregation path end to end, and "
            "compare against a period known to be sound. Resume growth work on this "
            "stage only once the number is trusted."
        ),
        rationale=warning.message,
        grounded_in=f"{warning.code.value}: {warning.stage}",
        numbers=dict(warning.numbers),
        target_stage=warning.stage,
    )


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
        with observation(
            self.name,
            input={"question": payload.question},
            metadata={"days": payload.days, "channel": payload.channel},
            tags=["strategist"],
        ) as span:
            report = self._run_inner(session, payload)
            span.update(
                output={
                    "recommendation_count": len(report.recommendations),
                    "insufficient_evidence": report.insufficient_evidence,
                    "analyst_primary_driver": report.analyst_primary_driver,
                }
            )
            return report

    def _run_inner(self, session: Session, payload: StrategistQuestion) -> StrategyReport:
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
        recommendations, gated_claims = self._apply_data_warnings(
            recommendations, payload.data_warnings
        )
        if gated_claims:
            claims.extend(gated_claims)
            insufficient = True
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

    def _apply_data_warnings(
        self, recs: list[Recommendation], warnings: list[DataWarning]
    ) -> tuple[list[Recommendation], list[EvidenceClaim]]:
        """
        Deterministic post-condition: no urgency on a stage flagged as broken data.

        This is the guardrail that was missing when an integer-truncation artefact
        emptied the Premium stage and the playbook answered `[P0] Fix Premium leak on
        weakest channel`. It runs on the agent's *output*, in Python, so correctness
        never depends on the model having complied with an instruction (ADR-002,
        ADR-009).

        Recommendations are replaced, not deleted. Dropping them would leave the
        report looking healthy, which is the failure mode this exists to prevent —
        and `03-agents.mdc` requires an agent to state when evidence is insufficient.
        """
        blocked = {w.stage for w in warnings if w.blocking}
        if not blocked:
            return recs, []

        by_stage = {w.stage: w for w in warnings if w.blocking}
        kept: list[Recommendation] = []
        suppressed: list[Recommendation] = []
        for rec in recs:
            (suppressed if rec.target_stage in blocked else kept).append(rec)

        # Verification items lead: they must never be the ones truncated away.
        replacements = [_verification_recommendation(by_stage[s]) for s in sorted(blocked)]

        claims = [
            EvidenceClaim(
                label=SemanticLabel.INTERPRETATION,
                text=(
                    f"Data quality gate: {len(suppressed)} recommendation(s) on "
                    f"{', '.join(sorted(blocked))} withheld — the stage is flagged as "
                    "unreliable, so the measurement is verified before it is acted on."
                ),
                source_tool="metric_validation",
                numbers={"suppressed": len(suppressed), "blocked_stages": len(blocked)},
            )
        ]
        claims.extend(
            EvidenceClaim(
                label=SemanticLabel.FACT,
                text=by_stage[stage].message,
                source_tool="metric_validation",
                numbers=dict(by_stage[stage].numbers),
            )
            for stage in sorted(blocked)
        )
        return replacements + kept, claims

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
                    target_stage="premium_users",
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
                    target_stage=_stage_mentioned_in(stage),
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
                    target_stage="premium_users",
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
