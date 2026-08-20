# Skill Taxonomy

## Definition

A skill is a reusable, typed capability. Prefer deterministic Python. Independently testable. No UI dependency.

## Runtime skills (planned)

| Skill | Responsibility |
|-------|----------------|
| `youtube_ingestion` | Fetch/normalize/persist YouTube metadata and metrics |
| `funnel_analysis` | Funnel rates, dropoffs, bottlenecks, period compare |
| `content_analysis` | Rank content, value score, topic compare, reach/conversion gaps |
| `anomaly_detection` | Deterministic anomaly flags (z-score, IQR, thresholds, …) |
| `experiment_analysis` | Rates, deltas, CIs, significance, practical significance |
| `report_generation` | Structured weekly growth report from analytical results |

## Naming

`<domain>_<capability>` — avoid `helper`, `utils`, `smart_analysis`.

## Contracts

Every skill uses `docs/templates/skill-contract.md`.

## Core split

| Concern | Owner |
|---------|--------|
| Calculations | Skills (Python) |
| Reasoning | Agents (LLM) |
| Truth | Database |
| Observability | Langfuse |
| Quality control | Evaluation |
