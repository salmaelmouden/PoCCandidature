# Plan: Phase 3 — YouTube Ingestion

**Status:** Implemented  
**Branch:** `phase-3-youtube-ingestion`  
**Scope:** `youtube_ingestion` skill — extract / transform / load YouTube Data API v3 metadata + stats into Postgres via repositories.  
**Out of scope:** Dashboard, agents, OAuth Analytics API, Langfuse, acquisition funnel fabrication from YouTube.

## Design

- **Extract:** channel → uploads playlist → paginated `playlistItems` → batched `videos.list`.
- **Transform:** validate + normalize; `is_synthetic=false`, `dataset_label=youtube_api`.
- **Load:** repository upserts keyed by `youtube_video_id` and `(video_id, metric_date)`.
- **Metrics note:** Data API statistics are cumulative lifetime totals snapshotted for `metric_date`.

## DoD

- [x] Skill + README contract
- [x] Client with timeout + bounded retries
- [x] Tests green without network
- [ ] Branch commit/push
- [x] No secrets committed
