"""growth_data_analyst_agent — evidence gathering via typed tools."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.growth_data_analyst_agent.config import DataAnalystConfig
from app.agents.growth_data_analyst_agent.prompts import DEFAULT_PREMIUM_QUESTION
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
from app.services.dashboard import resolve_period


class GrowthDataAnalystAgent:
    """
    Analyst agent: runs deterministic tools and synthesizes FACT / INTERPRETATION.

    Phase 5 uses a deterministic synthesizer so demos and CI work without an LLM key.
    An optional LLM narrative layer can wrap the same tool outputs later.
    """

    name = "growth_data_analyst_agent"

    def __init__(self, config: DataAnalystConfig | None = None) -> None:
        self.config = config or DataAnalystConfig()

    def run(self, session: Session, question: AnalystQuestion | str | None = None) -> AnalystReport:
        payload = self._normalize_question(question)
        period = resolve_period(payload.days, as_of=payload.as_of)
        tool_calls: list[ToolInvocation] = []

        overview = self._safe_tool(
            tool_calls,
            "get_overview",
            lambda: tool_get_overview(
                session, days=payload.days, channel=payload.channel, as_of=payload.as_of
            ),
        )
        funnel = self._safe_tool(
            tool_calls,
            "get_funnel_compare",
            lambda: tool_get_funnel_compare(
                session, days=payload.days, channel=payload.channel, as_of=payload.as_of
            ),
        )
        acquisition = self._safe_tool(
            tool_calls,
            "get_acquisition_by_channel",
            lambda: tool_get_acquisition_by_channel(
                session, days=payload.days, as_of=payload.as_of
            ),
        )
        content = self._safe_tool(
            tool_calls,
            "get_content_gaps",
            lambda: tool_get_content_gaps(
                session, days=payload.days, channel=payload.channel, as_of=payload.as_of
            ),
        )

        claims, primary_driver, insufficient = self._synthesize(
            question=payload.question,
            overview=overview,
            funnel=funnel,
            acquisition=acquisition,
            content=content,
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
        fn,
    ) -> dict | None:
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
        overview: dict | None,
        funnel: dict | None,
        acquisition: dict | None,
        content: dict | None,
    ) -> tuple[list[EvidenceClaim], str | None, bool]:
        claims: list[EvidenceClaim] = []
        if not any([overview, funnel, acquisition, content]):
            return (
                [
                    EvidenceClaim(
                        label=SemanticLabel.INTERPRETATION,
                        text="Insufficient evidence: all analyst tools failed.",
                        source_tool=None,
                    )
                ],
                None,
                True,
            )

        premium_delta = None
        activated_to_premium_delta = None
        if funnel:
            cur = funnel["current_counts"]
            prev = funnel["previous_counts"]
            claims.append(
                EvidenceClaim(
                    label=SemanticLabel.FACT,
                    text=(
                        f"Current period premium_users={cur['premium_users']}, "
                        f"previous={prev['premium_users']} "
                        f"(activated_users {cur['activated_users']} → prev {prev['activated_users']})."
                    ),
                    source_tool="get_funnel_compare",
                    numbers={
                        "premium_users_current": cur["premium_users"],
                        "premium_users_previous": prev["premium_users"],
                        "activated_users_current": cur["activated_users"],
                        "activated_users_previous": prev["activated_users"],
                    },
                )
            )
            deltas = funnel.get("conversion_rate_deltas") or {}
            activated_to_premium_delta = deltas.get("activated_users_to_premium_users")
            if activated_to_premium_delta is not None:
                claims.append(
                    EvidenceClaim(
                        label=SemanticLabel.FACT,
                        text=(
                            "activated_users→premium_users conversion rate delta "
                            f"(current − previous) = {activated_to_premium_delta:.4f}."
                        ),
                        source_tool="get_funnel_compare",
                        numbers={"activated_to_premium_rate_delta": activated_to_premium_delta},
                    )
                )
            bn = funnel.get("current_bottleneck") or {}
            if bn.get("from"):
                claims.append(
                    EvidenceClaim(
                        label=SemanticLabel.FACT,
                        text=(
                            f"Current funnel bottleneck: {bn['from']} → {bn['to']} "
                            f"(dropoff_rate={bn['dropoff_rate']:.4f})."
                        ),
                        source_tool="get_funnel_compare",
                        numbers={"bottleneck_dropoff_rate": bn["dropoff_rate"]},
                    )
                )
            if prev["premium_users"] > 0:
                premium_delta = (cur["premium_users"] - prev["premium_users"]) / prev[
                    "premium_users"
                ]

        worst_channel = None
        if acquisition and acquisition.get("channels"):
            ranked = sorted(
                acquisition["channels"],
                key=lambda row: (row["premium_rate"], -row["views"]),
            )
            worst_channel = ranked[0]
            claims.append(
                EvidenceClaim(
                    label=SemanticLabel.FACT,
                    text=(
                        f"Lowest premium_rate channel in period: {worst_channel['channel']} "
                        f"(premium_rate={worst_channel['premium_rate']:.4f}, "
                        f"views={worst_channel['views']}, "
                        f"premium_users={worst_channel['premium_users']})."
                    ),
                    source_tool="get_acquisition_by_channel",
                    numbers={
                        "channel": worst_channel["channel"],
                        "premium_rate": worst_channel["premium_rate"],
                        "views": worst_channel["views"],
                        "premium_users": worst_channel["premium_users"],
                    },
                )
            )

        gap_topic = None
        if content and content.get("reach_conversion_gaps"):
            gap = content["reach_conversion_gaps"][0]
            gap_topic = gap.get("topic")
            claims.append(
                EvidenceClaim(
                    label=SemanticLabel.FACT,
                    text=(
                        f"Top reach/low-conversion gap: topic={gap.get('topic')} "
                        f"reach={gap.get('reach')} premium_rate={gap.get('premium_rate'):.4f} "
                        f"({gap.get('reason')})."
                    ),
                    source_tool="get_content_gaps",
                    numbers={
                        "topic": gap.get("topic"),
                        "reach": gap.get("reach"),
                        "premium_rate": gap.get("premium_rate"),
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

        primary_driver = None
        interpretation_bits: list[str] = []
        if activated_to_premium_delta is not None and activated_to_premium_delta < 0:
            interpretation_bits.append(
                "Premium conversion rate from activated users fell vs the prior period."
            )
        if worst_channel and worst_channel["channel"] == "YouTube":
            primary_driver = "YouTube channel premium conversion weakness"
            interpretation_bits.append(
                "YouTube shows the weakest premium_rate among channels in this window, "
                "consistent with a YouTube-concentrated Premium decline narrative."
            )
        elif worst_channel:
            primary_driver = f"{worst_channel['channel']} channel premium_rate lag"
            interpretation_bits.append(
                f"{worst_channel['channel']} is the weakest premium_rate channel in the window."
            )
        if gap_topic:
            interpretation_bits.append(
                f"Content gaps highlight topic '{gap_topic}' as high reach / low conversion."
            )
        if premium_delta is not None and premium_delta < 0 and primary_driver is None:
            primary_driver = "period-over-period premium_users decline"

        q_lower = question.lower()
        if "premium" in q_lower and activated_to_premium_delta is None and premium_delta is None:
            insufficient = True
        else:
            insufficient = False

        if interpretation_bits:
            claims.append(
                EvidenceClaim(
                    label=SemanticLabel.INTERPRETATION,
                    text=" ".join(interpretation_bits),
                    source_tool=None,
                    numbers={
                        "primary_driver": primary_driver,
                        "activated_to_premium_rate_delta": activated_to_premium_delta,
                        "premium_users_relative_delta": premium_delta,
                    },
                )
            )
        elif not claims:
            insufficient = True
            claims.append(
                EvidenceClaim(
                    label=SemanticLabel.INTERPRETATION,
                    text="Insufficient evidence to explain the asked change.",
                    source_tool=None,
                )
            )

        return claims, primary_driver, insufficient
