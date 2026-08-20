"""Unit tests for scoring helpers (no DB)."""

from __future__ import annotations

from app.agents.growth_data_analyst_agent.schemas import EvidenceClaim, SemanticLabel
from evaluation.evaluators import (
    score_hallucination_text,
    score_no_recommendation_from_analyst,
    score_tool_selection,
)


def test_tool_selection_detects_missing_and_forbidden() -> None:
    ok = score_tool_selection({"a", "b"}, required={"a"}, forbidden={"c"})
    assert ok.passed
    bad = score_tool_selection({"a", "c"}, required={"a", "b"}, forbidden={"c"})
    assert bad.passed is False


def test_analyst_must_not_recommend() -> None:
    claims = [
        EvidenceClaim(label=SemanticLabel.FACT, text="x"),
        EvidenceClaim(label=SemanticLabel.RECOMMENDATION, text="do y"),
    ]
    assert score_no_recommendation_from_analyst(claims).passed is False


def test_hallucination_markers() -> None:
    assert score_hallucination_text("normal growth note").passed
    assert score_hallucination_text("guaranteed uplift of 50%").passed is False
