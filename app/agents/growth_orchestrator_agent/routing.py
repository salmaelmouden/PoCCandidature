"""Question routing for the growth orchestrator."""

from __future__ import annotations

from app.agents.growth_orchestrator_agent.schemas import RouteKind

_EXPERIMENT_KEYS = (
    "experiment",
    "a/b",
    "ab test",
    "a-b test",
    "significance",
    "how should we test",
    "how do we test",
    "design an experiment",
    "propose an experiment",
    "control vs treatment",
    "decision hint",
)

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
    Route experiment questions to the experiment agent; diagnostics to analyst;
    action questions to analyst→strategist.
    """
    q = question.lower().strip()
    wants_experiment = any(k in q for k in _EXPERIMENT_KEYS)
    # Avoid treating generic "should we" strategy as experiment unless experiment-ish
    if wants_experiment or "how should we test" in q or "how do we test" in q:
        return RouteKind.EXPERIMENT

    wants_strategy = any(k in q for k in _STRATEGY_KEYS)
    wants_analysis = any(k in q for k in _ANALYSIS_KEYS)

    if wants_strategy:
        return RouteKind.ANALYST_THEN_STRATEGIST
    if wants_analysis:
        return RouteKind.ANALYST_ONLY
    return RouteKind.ANALYST_THEN_STRATEGIST
