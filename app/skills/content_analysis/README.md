# Skill: content_analysis

## Purpose

Rank and compare content using a documented **Content Value Score**, not views alone.

## Content Value Score (CVS)

Min-max normalize cohort components to `[0, 1]`, then:

```text
CVS = 0.20 * reach_n
    + 0.15 * engagement_n
    + 0.30 * signup_contribution_n
    + 0.35 * premium_conversion_n
```

- `signup_contribution_n` = normalize(signups)
- `premium_conversion_n` = normalize(premium_users / max(signups, 1))

Weights are configurable via `ContentValueWeights` and re-normalized to sum to 1.

## Does

- `rank_content`
- `calculate_content_value`
- `compare_topics`
- `identify_high_reach_low_conversion`
- `identify_high_conversion_low_reach`

## Does not

- Access DB / UI
- Invent metrics
- Rank solely by reach

## Determinism

Fully deterministic for the same inputs and weights.

## Side effects

None.
