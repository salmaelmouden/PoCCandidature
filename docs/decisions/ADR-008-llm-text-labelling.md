# ADR-008: Where an LLM is allowed to write to the database

- **Status:** Accepted
- **Date:** 2026-08-20
- **Deciders:** Growth Intelligence AI maintainers
- **Amends:** [ADR-002](ADR-002-deterministic-skills.md)

## Context

ADR-002 established that skills are deterministic and that "LLMs may only interpret skill
outputs, never invent numbers". It was written with metrics in mind — funnels, conversion
rates, statistical tests.

Phase 10 introduces a case ADR-002 did not anticipate: assigning an editorial **topic** and
**hook type** to a video title. Measured on the real Finary catalogue (952 videos), the
existing keyword classifier put 53 % of videos into a fallback bucket, and 38 % of titles
contain no finance keyword at all even against a 35-word French vocabulary. Those 38 % are
the narrative titles — the ones whose performance is most worth comparing. `hook_type`
has no keyword expression whatsoever.

So the choice is not "LLM or keywords". It is "an unusable dimension, or an LLM".

## Decision

An LLM may **label text**. It may not **produce numbers**.

Concretely, three rules:

1. **Labels only.** An LLM may assign a value from a closed, code-defined enum to a piece
   of text. It may not compute, aggregate, estimate, rank or infer a metric.
2. **Persisted and versioned.** LLM output is written once per `(entity, version)` and every
   downstream computation reads the stored row. Analytics never call an LLM. Changing the
   taxonomy or the prompt means bumping the version, which leaves prior labels intact and
   auditable.
3. **Attributed.** Every row records which backend produced it (`classified_by`), so
   fallback-quality labels can be excluded from analysis.

Reproducibility is therefore a property of the **database**, not of the model call — which
is what ADR-002 actually needs. Re-running the analytics on the same rows gives the same
numbers, forever, with or without an API key.

## Alternatives

| Option | Why not |
|--------|---------|
| Keep keyword classification | Measured: 53 % fallback, 38 % blind. `hook_type` impossible. |
| Expand the keyword vocabulary | Tested with 35 FR terms — still 38 % uncovered, and the uncovered set is the interesting one |
| Let the LLM read descriptions too | Descriptions carry Finary's product pitch and UTM links; that is what corrupted the keyword classifier in the first place |
| Call the LLM at analysis time | Non-reproducible metrics, cost per query, and a hard dependency on an API key for every demo |
| Have the LLM also score/rank content | Directly violates ADR-002; scoring stays in `content_analysis` with a documented formula |

## Consequences

### Positive

- One genuinely unusable dimension (`topic`) becomes usable, and one new dimension
  (`hook_type`) becomes available — the only editorial signal in the project
- Metrics stay deterministic and testable; the FACT / INTERPRETATION boundary is unchanged
- Offline CI and demos still work through the deterministic fallback

### Negative / trade-offs

- A paid API call is now part of the ingestion path (one-off: ~0.65 $ for 952 titles)
- Label quality is not verifiable by unit test — it needs periodic human spot-checks
- Taxonomy changes require a version bump and a re-run, not an in-place edit

### Follow-ups

- Spot-check a random sample after each version bump and record the result in `evaluation/`
- Exclude `classified_by = "keyword_fallback"` rows from published analysis
