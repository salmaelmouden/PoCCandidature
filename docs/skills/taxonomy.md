# Skill Taxonomy

## Definition

A skill is a reusable, typed capability. Prefer deterministic Python. Independently testable. No UI dependency.

## Runtime skills

| Skill | Status | Responsibility |
|-------|--------|----------------|
| `funnel_analysis` | **Phase 2** | Funnel rates, dropoffs, bottlenecks, period compare |
| `content_analysis` | **Phase 2** | Content Value Score, rank, topic compare, reach/conversion gaps |
| `anomaly_detection` | **Phase 2** | Deterministic anomaly flags (z-score, IQR, % change, rolling mean) |
| `youtube_ingestion` | **Phase 3** | Fetch/normalize/persist YouTube metadata and metrics |
| `experiment_analysis` | **Phase 7** | Rates, deltas, CIs, significance |
| `report_generation` | **Phase 9** | Weekly growth report from analytical results |

## Naming

`<domain>_<capability>` — avoid `helper`, `utils`, `smart_analysis`.

## Contracts

Every skill uses `docs/templates/skill-contract.md` and ships a README.

## Core split

| Concern | Owner |
|---------|--------|
| Calculations | Skills (Python) |
| Reasoning | Agents (LLM) |
| Truth | Database |
| Observability | Langfuse |
| Quality control | Evaluation |
