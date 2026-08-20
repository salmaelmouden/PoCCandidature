# ADR-007: Why synthetic data?

- **Status:** Accepted (foundation)
- **Date:** 2026-08-20
- **Deciders:** Growth Intelligence AI maintainers

## Context

This is a portfolio project inspired by public growth/AI challenges. We do **not** have access to Finary (or any employer's) private data. We still need realistic funnels, seasonality, and anomalies for demos.

## Decision

Generate **labelled synthetic data** for channels, topics, funnel stages, content performance, experiments, and anomalies. Never present it as real company data. Never use private APIs, logos, or proprietary datasets.

## Alternatives

| Option | Why not |
|--------|---------|
| Scraped private analytics | Illegal/unethical; disqualifying |
| Tiny hand-waved CSV | Weak demo credibility |

## Consequences

### Positive

- Safe, reproducible demos; controllable anomaly stories

### Negative / trade-offs

- Must keep labelling honest in UI/README

### Follow-ups

- Phase 1: generator with seasonality + known conversion shifts
