"""Tests for content_analysis skill."""

from app.skills.content_analysis import (
    calculate_content_value,
    compare_topics,
    identify_high_conversion_low_reach,
    identify_high_reach_low_conversion,
    rank_content,
)

ITEMS = [
    {
        "content_id": "a",
        "title": "Viral crypto",
        "topic": "Crypto",
        "reach": 100000,
        "engagement": 5000,
        "signups": 200,
        "premium_users": 5,
    },
    {
        "content_id": "b",
        "title": "Budgeting basics",
        "topic": "Budgeting",
        "reach": 8000,
        "engagement": 900,
        "signups": 400,
        "premium_users": 80,
    },
    {
        "content_id": "c",
        "title": "ETF primer",
        "topic": "ETFs",
        "reach": 20000,
        "engagement": 1200,
        "signups": 300,
        "premium_users": 40,
    },
]


def test_rank_not_by_reach_alone() -> None:
    ranked = rank_content(ITEMS)
    assert ranked[0].content_id != "a"
    assert ranked[0].content_id == "b"


def test_content_value_components_present() -> None:
    scores = calculate_content_value(ITEMS)
    assert len(scores) == 3
    assert set(scores[0].components) == {
        "reach",
        "engagement",
        "signup_contribution",
        "premium_conversion",
    }


def test_compare_topics() -> None:
    topics = compare_topics(ITEMS)
    names = {t.topic for t in topics}
    assert names == {"Crypto", "Budgeting", "ETFs"}


def test_high_reach_low_conversion() -> None:
    gaps = identify_high_reach_low_conversion(ITEMS)
    ids = {g.content_id for g in gaps}
    assert "a" in ids


def test_high_conversion_low_reach() -> None:
    gaps = identify_high_conversion_low_reach(ITEMS)
    ids = {g.content_id for g in gaps}
    assert "b" in ids


def test_empty_input() -> None:
    assert rank_content([]) == []
    assert identify_high_reach_low_conversion([]) == []
