# Data model (Phase 1)

## Tables

| Table | Grain | Notes |
|-------|-------|-------|
| `videos` | one row per video | Unique `youtube_video_id`; topic indexed |
| `video_daily_metrics` | video × day | Unique `(video_id, metric_date)` |
| `acquisition` | day × channel × topic × video? | Funnel counts; nulls-not-distinct unique |
| `users` | one row per synthetic user | Journey timestamps + channel/topic |
| `experiments` | one row per experiment | |
| `experiment_results` | experiment × variant | |
| `analytics_snapshots` | metric × period × dimension | Precomputed demo snapshots |

## Labelling

- `is_synthetic` boolean
- `dataset_label` (current: `synthetic_v1`)

## Funnel stages

Views → Visits → Signups → Activated Users → Premium Users
