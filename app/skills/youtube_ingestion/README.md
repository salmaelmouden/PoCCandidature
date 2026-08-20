# Skill: youtube_ingestion

## Identity

- **Name:** `youtube_ingestion`
- **Module:** `app/skills/youtube_ingestion/`

## Purpose

Fetch, normalize, and persist YouTube channel video metadata and public statistics via the Data API v3.

## Responsibility

- Does: paginated extract, validation/transform, idempotent repository upserts
- Does **not:** invent funnel/acquisition facts, call LLMs, store API keys, use OAuth Analytics API

## Inputs

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| channel_id | str | yes | non-empty |
| metric_date | date \| None | no | defaults to UTC today |
| max_pages | int | no | 1–50 |

API key is supplied to `YouTubeClient` from env (`YOUTUBE_API_KEY`), never hard-coded.

Public demo channel (no owned channel required): see `demo.py` and `docs/guides/youtube-demo-ingest.md`
(`UCL8w_A8p8P1HWI3k6PR5Z6w` — PBS Two Cents).

## Outputs

| Field | Type | Description |
|-------|------|-------------|
| videos_upserted | int | Videos written/updated |
| metrics_upserted | int | Daily metric snapshots written/updated |
| skipped_invalid | int | Payload rows rejected by transform |

## Determinism

- [ ] Partially deterministic (external YouTube API I/O)
- Transform helpers (`parse_iso8601_duration`, `infer_topic`, `normalize_video_payload`) are fully deterministic

## Side effects

Reads YouTube Data API; writes DB via `VideoRepository` / `VideoDailyMetricRepository`.

Rows are labelled `is_synthetic=false`, `dataset_label=youtube_api`.

## Metrics caveat

YouTube Data API `statistics` are **lifetime cumulative** counters. This skill stores a point-in-time snapshot for `metric_date`. True day-over-day increments require consecutive snapshots or YouTube Analytics API (future).

## Topic heuristic

Keyword match on title+description against `Topic` enum; default `Personal Finance`.

## Error handling

| Condition | Behavior |
|-----------|----------|
| Missing API key | `ValueError` at client init |
| HTTP 429/5xx | Bounded retries with exponential backoff |
| Invalid video payload | Skip + count in `skipped_invalid` |
| Unknown channel | `YouTubeApiError` |

## Tests

- Location: `app/skills/youtube_ingestion/tests/`
- Mocked HTTP transport; no live network
