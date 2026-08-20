# Real YouTube ingest (demo)

This project uses a **hybrid data story** for portfolio demos:

| Data | Source | Label |
|------|--------|--------|
| Funnel / acquisition / users / Premium drop | Synthetic generator | `synthetic_v1`, `is_synthetic=true` |
| Video catalog + public view/like/comment stats | YouTube Data API v3 | `youtube_api`, `is_synthetic=false` |

You do **not** need your own channel. Use any public channel. The default demo channel is PBS **Two Cents** (personal finance education).

## 1. Get a free API key

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create (or select) a project.
3. Enable **YouTube Data API v3**.
4. Create credentials → **API key**.
5. (Recommended) Restrict the key to YouTube Data API v3.

Never commit the key. Put it only in local `.env`.

## 2. Configure `.env`

```bash
cp .env.example .env
```

```bash
YOUTUBE_API_KEY=your_key_here
# Optional — defaults to the public Two Cents channel if omitted:
YOUTUBE_CHANNEL_ID=UCL8w_A8p8P1HWI3k6PR5Z6w
YOUTUBE_MAX_PAGES=2
```

Demo channel:

- Name: Two Cents (PBS Digital Studios)
- URL: https://www.youtube.com/@TwoCentsPBS
- ID: `UCL8w_A8p8P1HWI3k6PR5Z6w`

## 3. Run ingest

With Postgres up (`make up` or at least `gia-postgres` healthy):

```bash
make ingest-youtube
```

Or override the channel:

```bash
.venv/bin/python scripts/ingest_youtube.py --channel-id UCxxxxxxxx --max-pages 1
```

## 4. What reviewers should see

- Rows in `videos` / `video_daily_metrics` with `dataset_label=youtube_api`
- Funnel pages still driven by labelled synthetic acquisition data
- Dashboard provenance banner stays honest about synthetic vs live

## Quota tip

First demo: `YOUTUBE_MAX_PAGES=1` or `2` (50 videos/page). Lifetime stats from the Data API are stored as point-in-time snapshots for `metric_date` (UTC today by default).
