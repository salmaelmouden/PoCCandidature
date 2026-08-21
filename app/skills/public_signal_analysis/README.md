# Skill: public_signal_analysis

## Identity

- **Name:** `public_signal_analysis`
- **Module:** `app/skills/public_signal_analysis/`

## Purpose

Compare video performance across editorial dimensions using **only** signals the public
YouTube Data API returns, without pretending to see anything it does not.

## Responsibility

- Does: normalise reach against comparable cohorts, aggregate by format / topic / hook,
  report what it could not measure.
- Does **not**: access the DB, call an LLM, estimate signups or conversion, interpret,
  or rank content by raw views.

## What is observable, and what is not

The public API returns title, description, publication date, duration, and cumulative
view / like / comment counts. It does **not** return watch time, CTR, retention, traffic
sources, demographics, signups or conversion — those require channel ownership.

Two consequences, both load-bearing:

1. `content_analysis`'s Content Value Score **cannot run here** — 65 % of its weight is
   signup contribution and premium conversion, which are invisible from outside.
2. There is **no history**. The API returns counters as of the fetch, so a single ingest
   yields one point per video. Trend analysis only becomes possible after the ingest has
   run on a schedule for weeks.

## Formulas

### Reach index

```text
reach_index(video) = views(video) / median(views of its cohort)
cohort            = video_format × publication quarter
```

Raw views are not comparable across the catalogue. Measured on the Finary catalogue, median
views per publication year were 8.5k (2021), 5.4k (2022), 27.9k (2023), 32.2k (2024),
47.1k (2025), 96.2k (2026). A 2021 video had five years to accumulate and still trails a
2026 video with eight months: **channel growth dominates age accumulation**. Aggregating raw
views by topic would therefore measure *when* a subject was covered, not how it performed.

Cohorts below `MIN_COHORT_SIZE` (5) are dropped rather than trusted, and the count of
excluded videos is reported in `CohortCoverage` — never silently absorbed.

### Engagement rate

```text
engagement_rate(video) = (likes + comments) / views
```

Reported alongside reach because it is far less growth-confounded — numerator and
denominator accumulate together — and because it measures a different thing. Reach says the
video travelled; engagement says it landed. They frequently disagree, and the disagreement
is where the finding usually is.

### Format split

`duration <= 60s` → Short, else long. Measured: 52 % of the Finary catalogue is Shorts, and
the median duration is 58 s. The catalogue is bimodal, so every dimension is also reported
per format — a blended number across two products with different view dynamics is an
artefact, not a measurement.

## Inputs

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `videos` | `list[PublicVideoSignal]` | yes | non-empty; counts ≥ 0 |

## Outputs

`PublicSignalReport` — `coverage` plus seven `DimensionStat` tables (format, topic and hook,
each blended and per format). Each `DimensionStat` carries `videos` (n), `median_reach_index`,
`median_engagement_rate`, `total_views` and `share_of_catalogue`.

Dimension values with fewer than `min_videos` (default 5) are omitted: a median over three
videos is not a finding.

## Determinism

- [x] Fully deterministic for the same inputs
- [ ] Partially deterministic

No I/O, no randomness, no clock. Medians, not means — the view distribution is heavily
right-skewed (a single Short in the catalogue has 3.0 M views against a 58 s median format).

## Side effects

None. Loading is `app/services/public_signals.py`.

## Error handling

| Condition | Error / behavior |
|-----------|------------------|
| Empty input | `PublicSignalError` |
| Cohort smaller than 5 | Cohort dropped; videos counted in `coverage.videos_excluded` |
| Cohort median of 0 views | Cohort dropped |
| Video with 0 views | `engagement_rate` returns 0.0 rather than dividing by zero |
| Dimension value below `min_videos` | Omitted from the table |

## Tests

- Location: `app/skills/public_signal_analysis/tests/`
- Key cases: Short threshold boundary, cohort keying, growth neutralisation, small-cohort
  and zero-median dropping, coverage reporting, thin-value omission, format separation.

## Run

```bash
make public-report        # or: python scripts/public_signal_report.py
```
