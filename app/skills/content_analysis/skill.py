"""Deterministic content analysis skill with documented Content Value Score."""

from __future__ import annotations

from statistics import median

from app.skills.content_analysis.schemas import (
    ContentGapItem,
    ContentMetrics,
    ContentValueScore,
    ContentValueWeights,
    TopicComparison,
)


def calculate_content_value(
    items: list[ContentMetrics] | list[dict],
    weights: ContentValueWeights | None = None,
) -> list[ContentValueScore]:
    """
    Content Value Score (CVS)

    For a cohort of content items, min-max normalize each component to [0, 1], then:

        CVS = w_r * reach_n
            + w_e * engagement_n
            + w_s * signup_contribution_n
            + w_p * premium_conversion_n

    Default weights (sum 1.0):
        reach=0.20, engagement=0.15, signup_contribution=0.30, premium_conversion=0.35

    Components:
        reach_n                 = normalize(reach)
        engagement_n            = normalize(engagement)
        signup_contribution_n   = normalize(signups)
        premium_conversion_n    = normalize(premium_rate) where
                                  premium_rate = premium_users / max(signups, 1)
                                  (also exposed; scoring uses cohort-normalized rate)

    Ranking must not use views/reach alone — CVS blends reach with conversion value.
    """
    parsed = _parse_items(items)
    if not parsed:
        return []

    w = (weights or ContentValueWeights()).normalized()
    reaches = [item.reach for item in parsed]
    engagements = [item.engagement for item in parsed]
    signups = [item.signups for item in parsed]
    premium_rates = [_premium_rate(item) for item in parsed]

    scores: list[ContentValueScore] = []
    for item, premium_rate in zip(parsed, premium_rates, strict=True):
        reach_n = _minmax(item.reach, reaches)
        engagement_n = _minmax(item.engagement, engagements)
        signup_n = _minmax(item.signups, signups)
        premium_n = _minmax(premium_rate, premium_rates)
        components = {
            "reach": reach_n,
            "engagement": engagement_n,
            "signup_contribution": signup_n,
            "premium_conversion": premium_n,
        }
        score = (
            w.reach * reach_n
            + w.engagement * engagement_n
            + w.signup_contribution * signup_n
            + w.premium_conversion * premium_n
        )
        scores.append(
            ContentValueScore(
                content_id=item.content_id,
                title=item.title,
                topic=item.topic,
                score=score,
                components=components,
                reach=item.reach,
                engagement=item.engagement,
                signups=item.signups,
                premium_users=item.premium_users,
                signup_rate=_signup_rate(item),
                premium_rate=premium_rate,
            )
        )
    return scores


def rank_content(
    items: list[ContentMetrics] | list[dict],
    weights: ContentValueWeights | None = None,
    *,
    limit: int | None = None,
) -> list[ContentValueScore]:
    ranked = sorted(
        calculate_content_value(items, weights),
        key=lambda row: (row.score, row.premium_users, row.signups),
        reverse=True,
    )
    if limit is not None:
        return ranked[:limit]
    return ranked


def compare_topics(
    items: list[ContentMetrics] | list[dict],
    weights: ContentValueWeights | None = None,
) -> list[TopicComparison]:
    parsed = _parse_items(items)
    scored = {row.content_id: row for row in calculate_content_value(parsed, weights)}
    by_topic: dict[str, list[ContentMetrics]] = {}
    for item in parsed:
        by_topic.setdefault(item.topic, []).append(item)

    comparisons: list[TopicComparison] = []
    for topic, topic_items in by_topic.items():
        total_reach = sum(i.reach for i in topic_items)
        total_signups = sum(i.signups for i in topic_items)
        total_premium = sum(i.premium_users for i in topic_items)
        avg_score = (
            sum(scored[i.content_id].score for i in topic_items) / len(topic_items)
            if topic_items
            else 0.0
        )
        comparisons.append(
            TopicComparison(
                topic=topic,
                content_count=len(topic_items),
                total_reach=total_reach,
                total_signups=total_signups,
                total_premium_users=total_premium,
                avg_content_value_score=avg_score,
                signup_rate=(total_signups / total_reach) if total_reach else 0.0,
                premium_rate=(total_premium / total_signups) if total_signups else 0.0,
            )
        )
    return sorted(comparisons, key=lambda row: row.avg_content_value_score, reverse=True)


def identify_high_reach_low_conversion(
    items: list[ContentMetrics] | list[dict],
    weights: ContentValueWeights | None = None,
) -> list[ContentGapItem]:
    """Reach at/above median AND premium_rate at/below median."""
    parsed = _parse_items(items)
    if not parsed:
        return []
    scored = calculate_content_value(parsed, weights)
    reach_med = median(row.reach for row in scored)
    premium_med = median(row.premium_rate for row in scored)
    gaps: list[ContentGapItem] = []
    for row in scored:
        if row.reach >= reach_med and row.premium_rate <= premium_med:
            gaps.append(
                ContentGapItem(
                    content_id=row.content_id,
                    title=row.title,
                    topic=row.topic,
                    reach=row.reach,
                    signup_rate=row.signup_rate,
                    premium_rate=row.premium_rate,
                    content_value_score=row.score,
                    reason="high_reach_low_conversion",
                )
            )
    return sorted(gaps, key=lambda g: (g.reach, -g.premium_rate), reverse=True)


def identify_high_conversion_low_reach(
    items: list[ContentMetrics] | list[dict],
    weights: ContentValueWeights | None = None,
) -> list[ContentGapItem]:
    """Premium_rate at/above median AND reach at/below median."""
    parsed = _parse_items(items)
    if not parsed:
        return []
    scored = calculate_content_value(parsed, weights)
    reach_med = median(row.reach for row in scored)
    premium_med = median(row.premium_rate for row in scored)
    gaps: list[ContentGapItem] = []
    for row in scored:
        if row.premium_rate >= premium_med and row.reach <= reach_med:
            gaps.append(
                ContentGapItem(
                    content_id=row.content_id,
                    title=row.title,
                    topic=row.topic,
                    reach=row.reach,
                    signup_rate=row.signup_rate,
                    premium_rate=row.premium_rate,
                    content_value_score=row.score,
                    reason="high_conversion_low_reach",
                )
            )
    return sorted(gaps, key=lambda g: (g.premium_rate, -g.reach), reverse=True)


def _parse_items(items: list[ContentMetrics] | list[dict]) -> list[ContentMetrics]:
    return [
        item if isinstance(item, ContentMetrics) else ContentMetrics.model_validate(item)
        for item in items
    ]


def _signup_rate(item: ContentMetrics) -> float:
    return (item.signups / item.reach) if item.reach else 0.0


def _premium_rate(item: ContentMetrics) -> float:
    return (item.premium_users / item.signups) if item.signups else 0.0


def _minmax(value: float, cohort: list[float]) -> float:
    lo = min(cohort)
    hi = max(cohort)
    if hi == lo:
        return 0.0
    return (value - lo) / (hi - lo)
