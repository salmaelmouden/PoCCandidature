# Evaluation Strategy

## Goal

Make important AI behavior **evaluable**: tool selection, factuality, numerical accuracy, recommendation quality, hallucination resistance, completeness — plus latency/cost when available.

## Layout

```text
evaluation/
  datasets/     # fixtures, synthetic snapshots
  cases/        # case definitions
  evaluators/   # scoring helpers (Phase 10)
  README.md
```

## Process

1. Define case from template (`docs/templates/evaluation-case.md`).
2. Pin synthetic dataset version / period.
3. Run agent with tools pointing at fixtures.
4. Score dimensions; fail on invented metrics.

## Example focus

Question: "Why did Premium conversion decrease?"  
Expect: funnel retrieve → period compare → channel/content inspection → primary driver with real numbers → no invented metrics → optional handoff to strategist/experiment (via orchestrator).

## Non-goals (Phase 0)

No evaluator implementation yet — structure and conventions only.
