# Skill: funnel_analysis

## Purpose

Deterministic funnel metrics: stage conversions, dropoffs, bottleneck, and period comparison.

## Does

- `calculate_funnel`
- `calculate_conversion_rates`
- `calculate_dropoffs`
- `identify_bottleneck`
- `compare_funnel_periods`

## Does not

- Access the database
- Call LLMs
- Invent missing stage counts

## Funnel stages

Views → Visits → Signups → Activated Users → Premium Users

## Inputs / outputs

Pydantic models in `schemas.py` (`FunnelCounts`, `FunnelResult`, `FunnelPeriodComparison`).

## Determinism

Fully deterministic for the same inputs.

## Side effects

None.

## Example

```python
from app.skills.funnel_analysis import calculate_funnel

result = calculate_funnel({
    "views": 10000,
    "visits": 2000,
    "signups": 400,
    "activated_users": 220,
    "premium_users": 40,
})
print(result.bottleneck_from_stage, result.bottleneck_dropoff_rate)
```
