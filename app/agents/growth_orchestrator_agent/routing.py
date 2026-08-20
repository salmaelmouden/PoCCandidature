"""Question routing for the growth orchestrator."""

from __future__ import annotations

from app.agents.growth_orchestrator_agent.schemas import RouteKind

_STRATEGY_KEYS = (
    "should we",
    "what should",
    "recommend",
    "recommendation",
    "next step",
    "next steps",
    "how to fix",
    "how do we",
    "action",
    "priorit",
    "what to do",
    "improve",
    "fix the",
)

_ANALYSIS_KEYS = (
    "why",
    "what happened",
    "what changed",
    "bottleneck",
    "anomal",
    "which channel",
    "which topic",
    "high reach",
    "decreas",
    "drop",
    "compare",
    "vs last",
    "period",
)


def classify_route(question: str) -> RouteKind:
    """
    Route diagnostic questions to analyst only; action questions to analyst→strategist.

    Ambiguous questions default to analyst→strategist so the product question
    “What should we do?” is always reachable from the orchestrator entrypoint.
    """
    q = question.lower().strip()
    wants_strategy = any(k in q for k in _STRATEGY_KEYS)
    wants_analysis = any(k in q for k in _ANALYSIS_KEYS)

    if wants_strategy:
        return RouteKind.ANALYST_THEN_STRATEGIST
    if wants_analysis:
        return RouteKind.ANALYST_ONLY
    return RouteKind.ANALYST_THEN_STRATEGIST
