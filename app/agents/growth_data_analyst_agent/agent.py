"""growth_data_analyst_agent — evidence gathering via typed tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.agents.growth_data_analyst_agent.config import DataAnalystConfig
from app.agents.growth_data_analyst_agent.prompts import DEFAULT_PREMIUM_QUESTION
from app.agents.growth_data_analyst_agent.routing import (
    AnalystIntent,
    classify_intent,
    tools_for_intent,
)
from app.agents.growth_data_analyst_agent.schemas import (
    AnalystQuestion,
    AnalystReport,
    EvidenceClaim,
    SemanticLabel,
    ToolInvocation,
)
from app.agents.growth_data_analyst_agent.tools import (
    tool_get_acquisition_by_channel,
    tool_get_content_gaps,
    tool_get_funnel_compare,
    tool_get_overview,
)
from app.observability import observation
from app.services.dashboard import resolve_period


class GrowthDataAnalystAgent:
    """
    Analyst agent: routes tools from the question, then synthesizes FACT / INTERPRETATION.

    Phase 5 uses a deterministic synthesizer so demos and CI work without an LLM key.
    """

    name = "growth_data_analyst_agent"

    def __init__(self, config: DataAnalystConfig | None = None) -> None:
        self.config = config or DataAnalystConfig()

    def run(self, session: Session, question: AnalystQuestion | str | None = None) -> AnalystReport:
        payload = self._normalize_question(question)
        intent = classify_intent(payload.question)
        with observation(
            self.name,
            input={"question": payload.question},
            metadata={"intent": intent.value, "days": payload.days, "channel": payload.channel},
            tags=["analyst", intent.value],
        ) as span:
            report = self._run_with_intent(session, payload, intent)
            span.update(
                output={
                    "primary_driver": report.primary_driver,
                    "insufficient_evidence": report.insufficient_evidence,
                    "tool_count": len(report.tool_calls),
                }
            )
            return report

    def _run_with_intent(
        self,
        session: Session,
        payload: AnalystQuestion,
        intent: AnalystIntent,
    ) -> AnalystReport:
        period = resolve_period(payload.days, as_of=payload.as_of)
        tool_calls: list[ToolInvocation] = []

        runners: dict[str, Callable[[], dict[str, Any]]] = {
            "get_overview": lambda: tool_get_overview(
                session, days=payload.days, channel=payload.channel, as_of=payload.as_of
            ),
            "get_funnel_compare": lambda: tool_get_funnel_compare(
                session, days=payload.days, channel=payload.channel, as_of=payload.as_of
            ),
            "get_acquisition_by_channel": lambda: tool_get_acquisition_by_channel(
                session, days=payload.days, as_of=payload.as_of
            ),
            "get_content_gaps": lambda: tool_get_content_gaps(
                session, days=payload.days, channel=payload.channel, as_of=payload.as_of
            ),
        }

        results: dict[str, dict[str, Any] | None] = {}
        for name in tools_for_intent(intent):
            with observation(
                f"tool:{name}",
                as_type="span",
                input={"tool": name},
                metadata={"agent": self.name},
                tags=["tool", name],
            ) as tool_span:
                results[name] = self._safe_tool(tool_calls, name, runners[name])
                tool_span.update(output={"ok": results[name] is not None})

        claims, primary_driver, insufficient = self._synthesize(
            question=payload.question,
            intent=intent,
            overview=results.get("get_overview"),
            funnel=results.get("get_funnel_compare"),
            acquisition=results.get("get_acquisition_by_channel"),
            content=results.get("get_content_gaps"),
        )
        return AnalystReport(
            question=payload.question,
            period_start=period.start,
            period_end=period.end,
            channel=payload.channel,
            primary_driver=primary_driver,
            claims=claims[: self.config.max_claims],
            tool_calls=tool_calls,
            insufficient_evidence=insufficient,
        )

    def _normalize_question(self, question: AnalystQuestion | str | None) -> AnalystQuestion:
        if question is None:
            return AnalystQuestion(
                question=DEFAULT_PREMIUM_QUESTION, days=self.config.default_days
            )
        if isinstance(question, str):
            return AnalystQuestion(question=question, days=self.config.default_days)
        return question

    def _safe_tool(
        self,
        tool_calls: list[ToolInvocation],
        name: str,
        fn: Callable[[], dict[str, Any]],
    ) -> dict[str, Any] | None:
        try:
            detail = fn()
            tool_calls.append(
                ToolInvocation(tool=name, ok=True, summary="ok", detail=detail)
            )
            return detail
        except Exception as exc:  # noqa: BLE001 — surfaced as tool failure, not crash
            tool_calls.append(
                ToolInvocation(tool=name, ok=False, summary=str(exc), detail={})
            )
            return None

    def _synthesize(
        self,
        *,
        question: str,
        intent: AnalystIntent,
        overview: dict | None,
        funnel: dict | None,
        acquisition: dict | None,
        content: dict | None,
    ) -> tuple[list[EvidenceClaim], str | None, bool]:
        if not any([overview, funnel, acquisition, content]):
            return (
                [
                    EvidenceClaim(
                        label=SemanticLabel.INTERPRETATION,
                        text="Insufficient evidence: all selected analyst tools failed.",
                        source_tool=None,
                    )
                ],
                None,
                True,
            )

        claims: list[EvidenceClaim] = [
            EvidenceClaim(
                label=SemanticLabel.FACT,
                text=f"Routed question intent={intent.value} for: “{question.strip()}”.",
                source_tool=None,
                numbers={"intent": intent.value},
            )
        ]

        cur = (funnel or {}).get("current_counts") or (overview or {}).get("current_counts")
        prev = (funnel or {}).get("previous_counts") or (overview or {}).get("previous_counts")
        deltas = (funnel or {}).get("conversion_rate_deltas") or {}
        activated_to_premium_delta = deltas.get("activated_users_to_premium_users")
        bn = (funnel or {}).get("current_bottleneck") or {}
        if not bn and overview:
            bn = {
                "from": overview.get("bottleneck_from"),
                "to": overview.get("bottleneck_to"),
                "dropoff_rate": overview.get("bottleneck_dropoff_rate"),
            }

        premium_delta = None
        if cur and prev and prev.get("premium_users", 0) > 0:
            premium_delta = (cur["premium_users"] - prev["premium_users"]) / prev["premium_users"]

        worst_channel = None
        best_channel = None
        if acquisition and acquisition.get("channels"):
            by_premium = sorted(
                acquisition["channels"],
                key=lambda row: (row["premium_rate"], -row["views"]),
            )
            by_signups = sorted(
                acquisition["channels"],
                key=lambda row: (-row["signups"], -row["views"]),
            )
            worst_channel = by_premium[0]
            best_channel = by_signups[0]

        gap = None
        top_content = None
        if content:
            if content.get("reach_conversion_gaps"):
                gap = content["reach_conversion_gaps"][0]
            if content.get("top_content"):
                top_content = content["top_content"][0]

        # Intent-specific FACT packing
        if intent in {
            AnalystIntent.PREMIUM,
            AnalystIntent.PERIOD_CHANGE,
            AnalystIntent.GENERAL,
            AnalystIntent.BOTTLENECK,
        } and cur and prev:
            claims.append(
                EvidenceClaim(
                    label=SemanticLabel.FACT,
                    text=(
                        f"Funnel counts current vs previous — "
                        f"views {cur['views']}→{prev['views']} (prev), "
                        f"signups {cur['signups']}→{prev['signups']} (prev), "
                        f"premium_users {cur['premium_users']}→{prev['premium_users']} (prev)."
                    ),
                    source_tool="get_funnel_compare" if funnel else "get_overview",
                    numbers={
                        "premium_users_current": cur["premium_users"],
                        "premium_users_previous": prev["premium_users"],
                        "signups_current": cur["signups"],
                        "signups_previous": prev["signups"],
                    },
                )
            )

        if intent in {AnalystIntent.PREMIUM, AnalystIntent.PERIOD_CHANGE, AnalystIntent.GENERAL}:
            if activated_to_premium_delta is not None:
                claims.append(
                    EvidenceClaim(
                        label=SemanticLabel.FACT,
                        text=(
                            "activated_users→premium_users rate delta "
                            f"(current − previous) = {activated_to_premium_delta:.4f}."
                        ),
                        source_tool="get_funnel_compare",
                        numbers={"activated_to_premium_rate_delta": activated_to_premium_delta},
                    )
                )

        if intent in {AnalystIntent.BOTTLENECK, AnalystIntent.PREMIUM, AnalystIntent.GENERAL} and bn.get(
            "from"
        ):
            claims.append(
                EvidenceClaim(
                    label=SemanticLabel.FACT,
                    text=(
                        f"Current funnel bottleneck: {bn['from']} → {bn['to']} "
                        f"(dropoff_rate={float(bn['dropoff_rate']):.4f})."
                    ),
                    source_tool="get_funnel_compare" if funnel else "get_overview",
                    numbers={"bottleneck_dropoff_rate": bn["dropoff_rate"]},
                )
            )

        if intent in {AnalystIntent.CHANNEL, AnalystIntent.PREMIUM, AnalystIntent.PERIOD_CHANGE}:
            if worst_channel:
                claims.append(
                    EvidenceClaim(
                        label=SemanticLabel.FACT,
                        text=(
                            f"Weakest premium_rate channel: {worst_channel['channel']} "
                            f"(premium_rate={worst_channel['premium_rate']:.4f}, "
                            f"views={worst_channel['views']}, "
                            f"premium_users={worst_channel['premium_users']})."
                        ),
                        source_tool="get_acquisition_by_channel",
                        numbers={
                            "channel": worst_channel["channel"],
                            "premium_rate": worst_channel["premium_rate"],
                        },
                    )
                )
            if best_channel and intent == AnalystIntent.CHANNEL:
                claims.append(
                    EvidenceClaim(
                        label=SemanticLabel.FACT,
                        text=(
                            f"Highest-signup channel: {best_channel['channel']} "
                            f"(signups={best_channel['signups']}, "
                            f"signup_rate={best_channel['signup_rate']:.4f})."
                        ),
                        source_tool="get_acquisition_by_channel",
                        numbers={
                            "channel": best_channel["channel"],
                            "signups": best_channel["signups"],
                        },
                    )
                )

        if intent in {AnalystIntent.CONTENT, AnalystIntent.PREMIUM, AnalystIntent.GENERAL}:
            if gap:
                claims.append(
                    EvidenceClaim(
                        label=SemanticLabel.FACT,
                        text=(
                            f"Top reach/low-conversion gap: topic={gap.get('topic')} "
                            f"reach={gap.get('reach')} "
                            f"premium_rate={float(gap.get('premium_rate') or 0):.4f}."
                        ),
                        source_tool="get_content_gaps",
                        numbers={
                            "topic": gap.get("topic"),
                            "reach": gap.get("reach"),
                            "premium_rate": gap.get("premium_rate"),
                        },
                    )
                )
            if top_content and intent == AnalystIntent.CONTENT:
                claims.append(
                    EvidenceClaim(
                        label=SemanticLabel.FACT,
                        text=(
                            f"Top Content Value Score unit: {top_content.get('title')} "
                            f"(topic={top_content.get('topic')}, score={float(top_content.get('score') or 0):.4f})."
                        ),
                        source_tool="get_content_gaps",
                        numbers={
                            "content_id": top_content.get("content_id"),
                            "score": top_content.get("score"),
                        },
                    )
                )

        if intent == AnalystIntent.ANOMALY and overview:
            claims.append(
                EvidenceClaim(
                    label=SemanticLabel.FACT,
                    text=(
                        f"Traffic anomaly flags in window: count={overview.get('anomaly_count', 0)} "
                        f"labels={overview.get('anomaly_labels') or []}."
                    ),
                    source_tool="get_overview",
                    numbers={
                        "anomaly_count": overview.get("anomaly_count"),
                    },
                )
            )

        if overview and overview.get("has_synthetic"):
            claims.append(
                EvidenceClaim(
                    label=SemanticLabel.FACT,
                    text=(
                        "Evidence includes labelled synthetic dataset rows "
                        f"({', '.join(overview.get('dataset_labels') or [])})."
                    ),
                    source_tool="get_overview",
                    numbers={"has_synthetic": True},
                )
            )

        primary_driver, interpretation = self._interpret(
            intent=intent,
            activated_to_premium_delta=activated_to_premium_delta,
            premium_delta=premium_delta,
            worst_channel=worst_channel,
            best_channel=best_channel,
            bn=bn,
            gap=gap,
            overview=overview,
        )
        insufficient = primary_driver is None and interpretation.startswith("Insufficient")

        claims.append(
            EvidenceClaim(
                label=SemanticLabel.INTERPRETATION,
                text=interpretation,
                source_tool=None,
                numbers={
                    "intent": intent.value,
                    "primary_driver": primary_driver,
                    "activated_to_premium_rate_delta": activated_to_premium_delta,
                    "premium_users_relative_delta": premium_delta,
                },
            )
        )
        return claims, primary_driver, insufficient

    def _interpret(
        self,
        *,
        intent: AnalystIntent,
        activated_to_premium_delta: float | None,
        premium_delta: float | None,
        worst_channel: dict | None,
        best_channel: dict | None,
        bn: dict,
        gap: dict | None,
        overview: dict | None,
    ) -> tuple[str | None, str]:
        if intent == AnalystIntent.PREMIUM:
            bits: list[str] = []
            driver = None
            if activated_to_premium_delta is not None and activated_to_premium_delta < 0:
                bits.append(
                    "Premium conversion from activated users fell vs the prior period."
                )
            if worst_channel and worst_channel["channel"] == "YouTube":
                driver = "YouTube channel premium conversion weakness"
                bits.append(
                    "YouTube has the weakest premium_rate among channels in this window."
                )
            elif worst_channel:
                driver = f"{worst_channel['channel']} channel premium_rate lag"
                bits.append(
                    f"{worst_channel['channel']} is the weakest premium_rate channel."
                )
            if gap:
                bits.append(
                    f"Content gaps also flag topic '{gap.get('topic')}' as high reach / low conversion."
                )
            if not bits:
                return None, "Insufficient evidence to explain a Premium conversion decrease."
            return driver or "period-over-period premium decline", " ".join(bits)

        if intent == AnalystIntent.BOTTLENECK:
            if bn.get("from"):
                driver = f"bottleneck {bn['from']}→{bn['to']}"
                return (
                    driver,
                    f"The largest funnel dropoff is at {bn['from']} → {bn['to']} "
                    f"(dropoff_rate={float(bn['dropoff_rate']):.4f}).",
                )
            return None, "Insufficient evidence to identify a funnel bottleneck."

        if intent == AnalystIntent.CHANNEL:
            if worst_channel and best_channel:
                return (
                    f"channel contrast {best_channel['channel']} vs {worst_channel['channel']}",
                    f"{best_channel['channel']} leads signups ({best_channel['signups']}); "
                    f"{worst_channel['channel']} has the weakest premium_rate "
                    f"({worst_channel['premium_rate']:.4f}).",
                )
            return None, "Insufficient channel evidence for this period."

        if intent == AnalystIntent.CONTENT:
            if gap:
                return (
                    f"content gap topic={gap.get('topic')}",
                    f"Highest-priority content issue is high-reach/low-conversion on topic "
                    f"'{gap.get('topic')}' (reach={gap.get('reach')}, "
                    f"premium_rate={float(gap.get('premium_rate') or 0):.4f}).",
                )
            return None, "Insufficient content-gap evidence for this period."

        if intent == AnalystIntent.ANOMALY:
            count = (overview or {}).get("anomaly_count", 0)
            labels = (overview or {}).get("anomaly_labels") or []
            if count:
                return (
                    f"{count} traffic anomalies",
                    f"Detected {count} traffic anomaly flag(s) in the window "
                    f"(example labels: {labels[:5]}).",
                )
            return (
                "no traffic anomalies flagged",
                "No traffic anomalies were flagged for this period with the current detector settings.",
            )

        if intent == AnalystIntent.PERIOD_CHANGE:
            bits = []
            driver = None
            if premium_delta is not None:
                bits.append(f"premium_users relative change={premium_delta:.4f}.")
            if activated_to_premium_delta is not None:
                bits.append(
                    f"activated→premium rate delta={activated_to_premium_delta:.4f}."
                )
            if worst_channel:
                driver = f"{worst_channel['channel']} premium_rate pressure"
                bits.append(
                    f"Weakest premium_rate channel is {worst_channel['channel']}."
                )
            if not bits:
                return None, "Insufficient period-compare evidence."
            return driver or "period-over-period funnel shift", " ".join(bits)

        # GENERAL
        bits = []
        driver = None
        if bn.get("from"):
            bits.append(f"Bottleneck at {bn['from']}→{bn['to']}.")
            driver = f"bottleneck {bn['from']}→{bn['to']}"
        if worst_channel:
            bits.append(f"Weakest premium_rate: {worst_channel['channel']}.")
            driver = driver or f"{worst_channel['channel']} premium_rate lag"
        if gap:
            bits.append(f"Content gap topic={gap.get('topic')}.")
        if not bits:
            return None, "Insufficient evidence for a general growth read."
        return driver, " ".join(bits)
