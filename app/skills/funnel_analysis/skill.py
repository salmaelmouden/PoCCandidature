"""Deterministic funnel analysis skill."""

from __future__ import annotations

from app.skills.funnel_analysis.schemas import (
    FUNNEL_STAGE_ORDER,
    FunnelCounts,
    FunnelPeriodComparison,
    FunnelResult,
    StageConversion,
    StageDropoff,
)


def calculate_funnel(counts: FunnelCounts | dict) -> FunnelResult:
    """Compute conversions, dropoffs, and bottleneck for a funnel."""
    parsed = counts if isinstance(counts, FunnelCounts) else FunnelCounts.model_validate(counts)
    conversions = calculate_conversion_rates(parsed)
    dropoffs = calculate_dropoffs(parsed)
    bottleneck = identify_bottleneck(dropoffs)
    return FunnelResult(
        counts=parsed,
        conversions=conversions,
        dropoffs=dropoffs,
        bottleneck_from_stage=bottleneck.from_stage if bottleneck else None,
        bottleneck_to_stage=bottleneck.to_stage if bottleneck else None,
        bottleneck_dropoff_rate=bottleneck.dropoff_rate if bottleneck else None,
    )


def calculate_conversion_rates(counts: FunnelCounts | dict) -> list[StageConversion]:
    parsed = counts if isinstance(counts, FunnelCounts) else FunnelCounts.model_validate(counts)
    values = _as_ordered_values(parsed)
    results: list[StageConversion] = []
    for idx in range(len(FUNNEL_STAGE_ORDER) - 1):
        from_stage = FUNNEL_STAGE_ORDER[idx]
        to_stage = FUNNEL_STAGE_ORDER[idx + 1]
        from_count = values[idx]
        to_count = values[idx + 1]
        rate = (to_count / from_count) if from_count > 0 else 0.0
        results.append(
            StageConversion(
                from_stage=from_stage,
                to_stage=to_stage,
                rate=rate,
                from_count=from_count,
                to_count=to_count,
            )
        )
    return results


def calculate_dropoffs(counts: FunnelCounts | dict) -> list[StageDropoff]:
    parsed = counts if isinstance(counts, FunnelCounts) else FunnelCounts.model_validate(counts)
    values = _as_ordered_values(parsed)
    results: list[StageDropoff] = []
    for idx in range(len(FUNNEL_STAGE_ORDER) - 1):
        from_stage = FUNNEL_STAGE_ORDER[idx]
        to_stage = FUNNEL_STAGE_ORDER[idx + 1]
        from_count = values[idx]
        to_count = values[idx + 1]
        dropoff_count = max(0, from_count - to_count)
        dropoff_rate = (dropoff_count / from_count) if from_count > 0 else 0.0
        results.append(
            StageDropoff(
                from_stage=from_stage,
                to_stage=to_stage,
                dropoff_count=dropoff_count,
                dropoff_rate=dropoff_rate,
            )
        )
    return results


def identify_bottleneck(dropoffs: list[StageDropoff]) -> StageDropoff | None:
    """Return the stage transition with the highest dropoff rate."""
    if not dropoffs:
        return None
    return max(dropoffs, key=lambda item: (item.dropoff_rate, item.dropoff_count))


def compare_funnel_periods(
    current: FunnelCounts | dict,
    previous: FunnelCounts | dict,
) -> FunnelPeriodComparison:
    current_result = calculate_funnel(current)
    previous_result = calculate_funnel(previous)

    absolute_deltas: dict[str, int] = {}
    relative_deltas: dict[str, float | None] = {}
    for stage in FUNNEL_STAGE_ORDER:
        cur = getattr(current_result.counts, stage)
        prev = getattr(previous_result.counts, stage)
        absolute_deltas[stage] = cur - prev
        relative_deltas[stage] = ((cur - prev) / prev) if prev > 0 else None

    conversion_rate_deltas: dict[str, float | None] = {}
    for cur_conv, prev_conv in zip(
        current_result.conversions, previous_result.conversions, strict=True
    ):
        key = f"{cur_conv.from_stage}_to_{cur_conv.to_stage}"
        conversion_rate_deltas[key] = cur_conv.rate - prev_conv.rate

    return FunnelPeriodComparison(
        current=current_result,
        previous=previous_result,
        absolute_deltas=absolute_deltas,
        relative_deltas=relative_deltas,
        conversion_rate_deltas=conversion_rate_deltas,
    )


def _as_ordered_values(counts: FunnelCounts) -> list[int]:
    return [getattr(counts, stage) for stage in FUNNEL_STAGE_ORDER]
