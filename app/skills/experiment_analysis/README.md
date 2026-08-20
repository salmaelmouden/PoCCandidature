# Skill: experiment_analysis

## Purpose

Deterministic A/B (two-proportion) analysis: rates, lift, confidence interval, significance, decision hint.

## Does

- `compare_variants` / `analyze_ab_test`
- `propose_experiment_design` (brief only — no invented historical metrics)

## Does not

- Access the database (agent/repos load rows)
- Call LLMs
- Run live experiment platforms

## Formulas

- \(\hat p = \text{conversions} / \text{users}\)
- Absolute lift = \(\hat p_t - \hat p_c\)
- Relative lift = absolute / \(\hat p_c\) (undefined if control rate is 0)
- Wald CI for difference: lift \(\pm z_{\alpha/2}\sqrt{\hat p_c(1-\hat p_c)/n_c + \hat p_t(1-\hat p_t)/n_t}\)
- Two-proportion z-test with pooled \(\hat p\) under \(H_0\); \(p = 2(1-\Phi(|z|))\)
- \(\Phi\) via `math.erf`

## Inputs / outputs

Pydantic models in `schemas.py`.

## Determinism

Fully deterministic for the same inputs.

## Side effects

None.

## Example

```python
from app.skills.experiment_analysis import compare_variants

result = compare_variants(
    {"variant": "control", "users": 4200, "conversions": 378},
    {"variant": "treatment", "users": 4180, "conversions": 443},
)
print(result.absolute_lift, result.significant, result.decision_hint)
```
