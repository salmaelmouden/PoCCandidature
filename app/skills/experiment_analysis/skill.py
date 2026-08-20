"""Deterministic experiment analysis skill (two-proportion comparison)."""

from __future__ import annotations

import math

from app.skills.experiment_analysis.schemas import (
    DecisionHint,
    ExperimentCompareInput,
    ExperimentCompareResult,
    ExperimentDesignProposal,
    VariantInput,
    VariantResult,
)

# Standard normal critical value for two-sided 95% (alpha=0.05).
# For other alphas we use the same z_* via inverse approx when needed.
_Z_CACHE: dict[float, float] = {0.05: 1.959963984540054, 0.01: 2.5758293035489004, 0.1: 1.6448536269514722}


def compare_variants(
    control: VariantInput | dict,
    treatment: VariantInput | dict,
    *,
    alpha: float = 0.05,
    min_users_per_variant: int = 100,
) -> ExperimentCompareResult:
    """Compare treatment vs control conversion rates (two-proportion z-test)."""
    parsed = ExperimentCompareInput(
        control=control if isinstance(control, VariantInput) else VariantInput.model_validate(control),
        treatment=(
            treatment
            if isinstance(treatment, VariantInput)
            else VariantInput.model_validate(treatment)
        ),
        alpha=alpha,
        min_users_per_variant=min_users_per_variant,
    )
    return analyze_ab_test(parsed)


def analyze_ab_test(payload: ExperimentCompareInput | dict) -> ExperimentCompareResult:
    """
    Absolute/relative lift, Wald CI for rate difference, two-proportion z-test.

    Formulas (documented in README):
    - p̂ = conversions / users
    - absolute_lift = p̂_t − p̂_c
    - relative_lift = absolute_lift / p̂_c (None if p̂_c == 0)
    - SE = sqrt(p̂_c(1−p̂_c)/n_c + p̂_t(1−p̂_t)/n_t)
    - CI = absolute_lift ± z_{α/2} · SE
    - z = absolute_lift / SE_pooled with pooled p̂ under H0
    - p = 2 · (1 − Φ(|z|))
    """
    data = (
        payload
        if isinstance(payload, ExperimentCompareInput)
        else ExperimentCompareInput.model_validate(payload)
    )
    c, t = data.control, data.treatment
    pc, pt = c.rate, t.rate
    absolute = pt - pc
    relative = (absolute / pc) if pc > 0 else None

    control_out = VariantResult(
        variant=c.variant, users=c.users, conversions=c.conversions, conversion_rate=pc
    )
    treatment_out = VariantResult(
        variant=t.variant, users=t.users, conversions=t.conversions, conversion_rate=pt
    )

    underpowered = c.users < data.min_users_per_variant or t.users < data.min_users_per_variant
    z_crit = _z_critical(data.alpha)

    if c.users == 0 or t.users == 0:
        return ExperimentCompareResult(
            control=control_out,
            treatment=treatment_out,
            absolute_lift=absolute,
            relative_lift=relative,
            ci_low=absolute,
            ci_high=absolute,
            z_score=None,
            p_value=None,
            alpha=data.alpha,
            significant=False,
            decision_hint=DecisionHint.UNDERPOWERED,
            notes="One or both variants have zero users; cannot test.",
        )

    # Wald SE for difference (for CI)
    se_wald = math.sqrt(pc * (1.0 - pc) / c.users + pt * (1.0 - pt) / t.users)
    if se_wald == 0.0:
        ci_low = ci_high = absolute
    else:
        ci_low = absolute - z_crit * se_wald
        ci_high = absolute + z_crit * se_wald

    # Pooled two-proportion z-test
    pooled = (c.conversions + t.conversions) / (c.users + t.users)
    se_pool = math.sqrt(pooled * (1.0 - pooled) * (1.0 / c.users + 1.0 / t.users))
    if se_pool == 0.0:
        z_score = None
        p_value = None
        significant = False
    else:
        z_score = absolute / se_pool
        p_value = 2.0 * (1.0 - _norm_cdf(abs(z_score)))
        significant = p_value < data.alpha

    decision, notes = _decide(
        absolute=absolute,
        significant=significant,
        underpowered=underpowered,
        p_value=p_value,
        alpha=data.alpha,
    )
    return ExperimentCompareResult(
        control=control_out,
        treatment=treatment_out,
        absolute_lift=absolute,
        relative_lift=relative,
        ci_low=ci_low,
        ci_high=ci_high,
        z_score=z_score,
        p_value=p_value,
        alpha=data.alpha,
        significant=significant,
        decision_hint=decision,
        notes=notes,
    )


def propose_experiment_design(
    *,
    driver: str,
    primary_metric: str = "activated_to_premium_rate",
    channel_or_topic: str | None = None,
) -> ExperimentDesignProposal:
    """Deterministic experiment brief from a growth driver (no invented historical stats)."""
    focus = channel_or_topic or "the flagged surface"
    return ExperimentDesignProposal(
        name=f"Test: fix {driver[:80]}",
        hypothesis=(
            f"Improving messaging/UX on {focus} will increase {primary_metric} "
            f"vs control, addressing driver “{driver}”."
        ),
        primary_metric=primary_metric,
        control_description="Current experience (no change).",
        treatment_description=(
            f"Single focused change on {focus} aligned to the driver "
            "(e.g. CTA copy, paywall timing, or landing match)."
        ),
        success_criteria=(
            f"Treatment {primary_metric} lift is positive and statistically significant "
            f"at α=0.05 with ≥100 users per variant; no material drop in activation."
        ),
        grounded_in=driver,
    )


def _decide(
    *,
    absolute: float,
    significant: bool,
    underpowered: bool,
    p_value: float | None,
    alpha: float,
) -> tuple[DecisionHint, str]:
    if underpowered:
        return (
            DecisionHint.UNDERPOWERED,
            f"Sample below min users/variant; treat results as directional only (α={alpha}).",
        )
    if significant and absolute > 0:
        return (
            DecisionHint.SHIP_TREATMENT,
            f"Treatment wins (p={p_value:.4f} < α={alpha}); absolute lift={absolute:.4f}.",
        )
    if significant and absolute < 0:
        return (
            DecisionHint.KEEP_CONTROL,
            f"Treatment underperforms significantly (p={p_value:.4f}); keep control.",
        )
    return (
        DecisionHint.INCONCLUSIVE,
        f"No significant difference at α={alpha}"
        + (f" (p={p_value:.4f})." if p_value is not None else "."),
    )


def _z_critical(alpha: float) -> float:
    if alpha in _Z_CACHE:
        return _Z_CACHE[alpha]
    # Approximate inverse CDF via binary search on Φ
    target = 1.0 - alpha / 2.0
    lo, hi = 0.0, 5.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if _norm_cdf(mid) < target:
            lo = mid
        else:
            hi = mid
    return hi


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
