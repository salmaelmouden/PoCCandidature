"""Question intent routing for deterministic analyst synthesis."""

from __future__ import annotations

from enum import StrEnum


class AnalystIntent(StrEnum):
    PREMIUM = "premium"
    BOTTLENECK = "bottleneck"
    CHANNEL = "channel"
    CONTENT = "content"
    ANOMALY = "anomaly"
    PERIOD_CHANGE = "period_change"
    GENERAL = "general"


def classify_intent(question: str) -> AnalystIntent:
    q = question.lower()
    if any(k in q for k in ("premium", "conversion decrease", "conversion drop", "churn to paid")):
        return AnalystIntent.PREMIUM
    if any(k in q for k in ("bottleneck", "leak", "dropoff", "drop-off", "where does the funnel")):
        return AnalystIntent.BOTTLENECK
    if any(k in q for k in ("channel", "youtube", "linkedin", "organic", "paid", "instagram")):
        return AnalystIntent.CHANNEL
    if any(k in q for k in ("topic", "content", "reach", "cvs", "value score", "gap")):
        return AnalystIntent.CONTENT
    if any(k in q for k in ("anomal", "spike", "outlier", "unusual traffic")):
        return AnalystIntent.ANOMALY
    if any(k in q for k in ("what changed", "period", "vs last", "week over", "wow", "compare")):
        return AnalystIntent.PERIOD_CHANGE
    return AnalystIntent.GENERAL


def tools_for_intent(intent: AnalystIntent) -> tuple[str, ...]:
    """Which tools to run for this intent (always include overview for provenance)."""
    mapping: dict[AnalystIntent, tuple[str, ...]] = {
        AnalystIntent.PREMIUM: (
            "get_overview",
            "get_funnel_compare",
            "get_acquisition_by_channel",
            "get_content_gaps",
        ),
        AnalystIntent.BOTTLENECK: ("get_overview", "get_funnel_compare"),
        AnalystIntent.CHANNEL: ("get_overview", "get_acquisition_by_channel", "get_funnel_compare"),
        AnalystIntent.CONTENT: ("get_overview", "get_content_gaps"),
        AnalystIntent.ANOMALY: ("get_overview",),
        AnalystIntent.PERIOD_CHANGE: ("get_overview", "get_funnel_compare", "get_acquisition_by_channel"),
        AnalystIntent.GENERAL: (
            "get_overview",
            "get_funnel_compare",
            "get_acquisition_by_channel",
            "get_content_gaps",
        ),
    }
    return mapping[intent]
