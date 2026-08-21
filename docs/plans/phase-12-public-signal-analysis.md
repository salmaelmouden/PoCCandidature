# Plan: Phase 12 — Public-signal analysis

**Status:** Implemented
**Branch:** `phase-11-content-classification`
**Scope:** `public_signal_analysis` skill, `public_signals` service, evidence-table CLI.
**Out of scope:** choosing and writing the insights (deliberately manual), dashboard page,
scheduled ingest.

## Why

Phase 11 produced usable `topic` and `hook_type` labels. Nothing consumed them yet, and the
existing `content_analysis` skill cannot: 65 % of its Content Value Score is signup
contribution and premium conversion, neither of which is observable from outside a channel.

This phase builds the comparison layer that *is* honest about public data.

## The measurement problem, and the fix

Raw view counts are not comparable across the catalogue. Median views by publication year on
the real Finary catalogue:

| Year | n | Median views |
|------|-----|--------------|
| 2021 | 15 | 8 560 |
| 2022 | 20 | 5 353 |
| 2023 | 117 | 27 865 |
| 2024 | 274 | 32 172 |
| 2025 | 417 | 47 061 |
| 2026 | 109 | 96 229 |

A 2021 video had five years to accumulate and still trails a 2026 video with eight months —
**channel growth dominates age accumulation**. Aggregating raw views by topic would measure
*when* a subject was covered, not how it performed.

Fix: `reach_index = views / median(views of same format × same publication quarter)`.
Cohorts under 5 videos are dropped and the exclusion is reported, not absorbed.

Second measurement problem: the catalogue is bimodal — **52 % is Shorts**, median duration
58 s. Every dimension is therefore reported per format as well as blended.

## Flow

```text
videos + video_daily_metrics + video_classifications
        → services/public_signals.load_public_signals   (excludes fallback-labelled rows)
        → public_signal_analysis skill                  (pure, deterministic)
        → PublicSignalReport                            (evidence table, no narrative)
        → [manual] pick 3 findings → insights page
```

## Decisions

- **Medians, not means.** The view distribution is heavily right-skewed — one 58-second Short
  has 3.0 M views.
- **Report coverage explicitly.** 26 of 952 videos (3 %) fall outside usable cohorts; the
  report says so rather than presenting 97 % as 100 %.
- **Omit thin dimension values.** Fewer than 5 videos is not a finding.
- **No interpretation in the skill.** It emits facts. Choosing which contradiction matters is
  the growth judgment, and it stays human.

## DoD

- [x] `public_signal_analysis` skill + 13 tests (no DB, no network)
- [x] `services/public_signals.py` loader, excludes `keyword_fallback` rows
- [x] `scripts/public_signal_report.py` + `make public-report`
- [x] Skill contract README documenting both formulas and the observability boundary
- [ ] Pick the 3 findings (manual — Phase 13)
