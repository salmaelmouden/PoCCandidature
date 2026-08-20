"""Lightweight scoring helpers for Growth Intelligence agent evals."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.growth_data_analyst_agent.schemas import EvidenceClaim, SemanticLabel


@dataclass
class DimensionScore:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class EvalResult:
    case_id: str
    scores: list[DimensionScore] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(s.passed for s in self.scores)

    def require(self, name: str, ok: bool, detail: str = "") -> None:
        self.scores.append(DimensionScore(name=name, passed=ok, detail=detail))


def score_no_recommendation_from_analyst(claims: list[EvidenceClaim]) -> DimensionScore:
    bad = [c for c in claims if c.label == SemanticLabel.RECOMMENDATION]
    return DimensionScore(
        name="hallucination",
        passed=len(bad) == 0,
        detail="analyst emitted RECOMMENDATION" if bad else "no RECOMMENDATION labels",
    )


def score_has_fact_claims(claims: list[EvidenceClaim]) -> DimensionScore:
    facts = [c for c in claims if c.label == SemanticLabel.FACT]
    return DimensionScore(
        name="factuality",
        passed=len(facts) > 0,
        detail=f"fact_count={len(facts)}",
    )


def score_tool_selection(actual_tools: set[str], required: set[str], forbidden: set[str] | None = None) -> DimensionScore:
    missing = required - actual_tools
    forbidden = forbidden or set()
    leaked = actual_tools & forbidden
    ok = not missing and not leaked
    detail = f"actual={sorted(actual_tools)} missing={sorted(missing)} forbidden_hit={sorted(leaked)}"
    return DimensionScore(name="tool_selection", passed=ok, detail=detail)


def score_primary_driver_mentions(driver: str | None, needles: list[str]) -> DimensionScore:
    text = (driver or "").lower()
    hit = any(n.lower() in text for n in needles)
    return DimensionScore(
        name="completeness",
        passed=hit,
        detail=f"driver={driver!r} needles={needles}",
    )


def score_recommendations_grounded(recs_text: list[str], driver: str | None) -> DimensionScore:
    """Fail if recommendations exist but driver is missing (ungrounded)."""
    if not recs_text:
        return DimensionScore(
            name="recommendation_quality",
            passed=False,
            detail="no recommendations produced",
        )
    if not driver:
        return DimensionScore(
            name="recommendation_quality",
            passed=False,
            detail="recommendations without analyst primary_driver",
        )
    return DimensionScore(
        name="recommendation_quality",
        passed=True,
        detail=f"count={len(recs_text)} driver={driver!r}",
    )


def invented_metric_markers(text: str) -> list[str]:
    """Heuristic red flags — not a full NLP judge."""
    markers = []
    lowered = text.lower()
    # Phrases that often signal fabricated precision without tool backing
    for phrase in ("exactly 12.345%", "confidential finary", "guaranteed uplift of"):
        if phrase in lowered:
            markers.append(phrase)
    return markers


def score_hallucination_text(*parts: str | None) -> DimensionScore:
    blob = " ".join(p for p in parts if p)
    hits = invented_metric_markers(blob)
    return DimensionScore(
        name="hallucination",
        passed=len(hits) == 0,
        detail=f"markers={hits}" if hits else "no heuristic invention markers",
    )
