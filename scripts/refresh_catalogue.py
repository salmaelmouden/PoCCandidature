#!/usr/bin/env python3
"""
Keep the ingested catalogue current: re-ingest public stats, classify new videos.

Runs once by default (suitable for cron / Railway scheduled jobs) or as a loop
(suitable for a long-lived container). Both steps are idempotent, so a repeated
run costs one YouTube page-through and, when no video is new, no LLM call at all.

Quota: one full pass over ~950 videos is ~40 of the 10,000 free daily units, so a
15-minute cadence uses roughly 38% of the daily allowance.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from types import FrameType

from app.config import get_settings
from app.db.repositories import IngestRunRepository
from app.db.session import create_db_engine, create_session_factory, session_scope
from app.skills.content_classification import (
    ClassifyContentRequest,
    build_classifier,
    classify_channel_content,
)
from app.skills.youtube_ingestion import YouTubeIngestRequest, ingest_youtube_channel
from app.skills.youtube_ingestion.client import YouTubeClient
from app.skills.youtube_ingestion.demo import DEMO_YOUTUBE_CHANNEL_ID

logger = logging.getLogger("refresh")

_stopping = False


def _request_stop(signum: int, _frame: FrameType | None) -> None:
    """Finish the current cycle, then exit — never abandon a half-written pass."""
    global _stopping
    _stopping = True
    logger.info("refresh_stop_requested signal=%s (finishing current cycle)", signum)


@dataclass(frozen=True)
class CycleResult:
    videos_upserted: int
    metrics_upserted: int
    classified: int
    classification_failed: int
    ok: bool


def _record(
    factory,
    *,
    channel_id: str,
    started_at: datetime,
    result: CycleResult,
    error: str | None,
) -> None:
    """Persist the cycle so the dashboard can state when it last checked."""
    try:
        with session_scope(factory) as session:
            IngestRunRepository(session).record(
                channel_id=channel_id,
                started_at=started_at,
                videos_upserted=result.videos_upserted,
                metrics_upserted=result.metrics_upserted,
                classified=result.classified,
                ok=result.ok,
                error=error,
            )
    except Exception as exc:  # noqa: BLE001 — bookkeeping must not break the refresh
        logger.error("refresh_bookkeeping_failed error=%s", exc)


def run_cycle(channel_id: str, *, max_pages: int) -> CycleResult:
    """One ingest + classify pass. Never raises — a bad cycle must not kill the loop."""
    settings = get_settings()
    engine = create_db_engine()
    factory = create_session_factory(engine)
    started_at = datetime.now(timezone.utc)

    try:
        with YouTubeClient(
            settings.youtube_api_key or "",
            timeout_seconds=settings.youtube_timeout_seconds,
            max_retries=settings.youtube_max_retries,
            ca_bundle_path=settings.ca_bundle_path,
        ) as client:
            with session_scope(factory) as session:
                ingested = ingest_youtube_channel(
                    session,
                    client,
                    YouTubeIngestRequest(channel_id=channel_id, max_pages=max_pages),
                )
    except Exception as exc:  # noqa: BLE001 — a transient API failure is not fatal
        logger.error("refresh_ingest_failed error=%s", exc)
        failed = CycleResult(0, 0, 0, 0, ok=False)
        _record(
            factory,
            channel_id=channel_id,
            started_at=started_at,
            result=failed,
            error=f"ingest: {exc}",
        )
        return failed

    classifier = build_classifier(
        settings.anthropic_api_key,
        model=settings.llm_model,
        ca_bundle_path=settings.ca_bundle_path,
    )
    try:
        with session_scope(factory) as session:
            classified = classify_channel_content(
                session,
                classifier,
                ClassifyContentRequest(batch_size=settings.llm_batch_size),
            )
    except Exception as exc:  # noqa: BLE001 — stats are already saved; labels can wait
        logger.error("refresh_classify_failed error=%s", exc)
        partial = CycleResult(
            ingested.videos_upserted, ingested.metrics_upserted, 0, 0, ok=False
        )
        _record(
            factory,
            channel_id=channel_id,
            started_at=started_at,
            result=partial,
            error=f"classify: {exc}",
        )
        return partial

    result = CycleResult(
        videos_upserted=ingested.videos_upserted,
        metrics_upserted=ingested.metrics_upserted,
        classified=classified.classified,
        classification_failed=classified.failed,
        ok=True,
    )
    _record(
        factory, channel_id=channel_id, started_at=started_at, result=result, error=None
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh the public catalogue")
    parser.add_argument("--channel-id", default=None, help="Overrides YOUTUBE_CHANNEL_ID")
    parser.add_argument("--max-pages", type=int, default=25)
    parser.add_argument(
        "--loop", action="store_true", help="Keep refreshing until stopped"
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=900,
        help="Loop cadence (default 900 = 15 min, ~38%% of the free daily quota)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # httpx logs full request URLs at INFO, which would print YOUTUBE_API_KEY.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    settings = get_settings()
    if not settings.youtube_api_key:
        logger.error("YOUTUBE_API_KEY is required — nothing to refresh")
        return 1

    channel_id = (
        args.channel_id or settings.youtube_channel_id or DEMO_YOUTUBE_CHANNEL_ID
    )
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    logger.info(
        "refresh_start channel=%s loop=%s interval=%ss",
        channel_id,
        args.loop,
        args.interval_seconds,
    )

    failures = 0
    while True:
        started = time.monotonic()
        result = run_cycle(channel_id, max_pages=args.max_pages)
        elapsed = time.monotonic() - started
        failures = 0 if result.ok else failures + 1
        logger.info(
            "refresh_cycle ok=%s videos=%s metrics=%s classified=%s failed=%s in %.1fs",
            result.ok,
            result.videos_upserted,
            result.metrics_upserted,
            result.classified,
            result.classification_failed,
            elapsed,
        )

        if not args.loop:
            return 0 if result.ok else 1
        if _stopping:
            logger.info("refresh_stopped")
            return 0

        # Back off on repeated failure so a broken key or quota exhaustion does not
        # hammer the API every 15 minutes for a day.
        delay = args.interval_seconds * min(2**failures, 8) if failures else args.interval_seconds
        if failures:
            logger.warning("refresh_backoff failures=%s next_in=%ss", failures, delay)

        slept = 0.0
        while slept < delay and not _stopping:
            time.sleep(min(5.0, delay - slept))
            slept += 5.0
        if _stopping:
            logger.info("refresh_stopped")
            return 0


if __name__ == "__main__":
    sys.exit(main())
