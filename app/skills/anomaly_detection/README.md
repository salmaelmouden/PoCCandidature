# Skill: anomaly_detection

## Purpose

Detect anomalies in growth time series with deterministic statistical methods.  
**Python detects. Agents interpret.**

## Methods

| Method | Idea |
|--------|------|
| `z_score` | \|z\| ≥ threshold (default 2.5) |
| `iqr` | Outside Q1−1.5·IQR / Q3+1.5·IQR |
| `percent_change` | Period-over-period \|Δ\| ≥ threshold (default 35%) |
| `rolling_mean` | Deviation from trailing window mean (default window 7, 40%) |

## Kinds

`traffic` · `signup` · `conversion` · `channel` · `content` · `generic`

## Does

- Flag anomalous points with score, direction, and method details
- Return empty list for insufficient series length

## Does not

- Access DB / UI
- Explain root causes (agent responsibility)
- Claim causal certainty

## Determinism

Fully deterministic for the same series and parameters.

## Side effects

None.
