#!/usr/bin/env python3
"""CLI: ingest YouTube channel metadata/stats into Postgres (idempotent)."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from app.config import get_settings
from app.db.session import create_db_engine, create_session_factory, session_scope
from app.skills.youtube_ingestion import YouTubeIngestRequest, ingest_youtube_channel
from app.skills.youtube_ingestion.client import YouTubeClient


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest YouTube channel videos (Data API v3)")
    parser.add_argument("--channel-id", default=None, help="Overrides YOUTUBE_CHANNEL_ID")
    parser.add_argument("--metric-date", default=None, help="YYYY-MM-DD (default: UTC today)")
    parser.add_argument("--max-pages", type=int, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    api_key = settings.youtube_api_key
    channel_id = args.channel_id or settings.youtube_channel_id
    if not api_key:
        logging.error("YOUTUBE_API_KEY is required (set in .env, never commit secrets)")
        return 1
    if not channel_id:
        logging.error("YOUTUBE_CHANNEL_ID or --channel-id is required")
        return 1

    metric_date = date.fromisoformat(args.metric_date) if args.metric_date else None
    max_pages = args.max_pages or settings.youtube_max_pages
    request = YouTubeIngestRequest(
        channel_id=channel_id, metric_date=metric_date, max_pages=max_pages
    )

    engine = create_db_engine()
    factory = create_session_factory(engine)
    with YouTubeClient(
        api_key,
        timeout_seconds=settings.youtube_timeout_seconds,
        max_retries=settings.youtube_max_retries,
    ) as client:
        with session_scope(factory) as session:
            result = ingest_youtube_channel(session, client, request)

    logging.info(
        "Done: videos_upserted=%s metrics_upserted=%s skipped=%s metric_date=%s",
        result.videos_upserted,
        result.metrics_upserted,
        result.skipped_invalid,
        result.metric_date,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
