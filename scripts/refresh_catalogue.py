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
import re
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


_CREDENTIAL_IN_URL = re.compile(
    r"((?:[?&])(?:key|api_?key|access_token|token|password)=)[^&\s\"'<>]+",
    re.IGNORECASE,
)


def redact_credentials(error: str | None) -> str | None:
    """Strip credentials out of an error before it is persisted.

    `ingest_runs.error` is rendered verbatim on the public catalogue page, and
    what reaches it is raw exception text. httpx puts the full request URL into
    its messages, so a failing YouTube call raises with `key=<the API key>` in
    the string — which would then be published to anyone holding the link.

    The same hazard is already handled for logging further down, where httpx's
    INFO level is silenced precisely because it prints request URLs. This closes
    the other end of it.
    """
    if not error:
        return error
    return _CREDENTIAL_IN_URL.sub(r"\1[redacted]", error)


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
                error=redact_credentials(error),
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

    ok = cycle_ok(classified=classified.classified, failed=classified.failed)
    if not ok:
        logger.error(
            "refresh_classify_none_succeeded failed_videos=%s — recording cycle as failed",
            classified.failed,
        )

    result = CycleResult(
        videos_upserted=ingested.videos_upserted,
        metrics_upserted=ingested.metrics_upserted,
        classified=classified.classified,
        classification_failed=classified.failed,
        ok=ok,
    )
    _record(
        factory,
        channel_id=channel_id,
        started_at=started_at,
        result=result,
        # Kept factual and free of operator instructions: this string is rendered
        # on the public page. The actionable detail goes to the log above.
        error=(
            None
            if ok
            else f"classification indisponible — {classified.failed} vidéos non classées"
        ),
    )
    return result


def cycle_ok(*, classified: int, failed: int) -> bool:
    """Did this cycle's classification actually do its job?

    `classify_channel_content` deliberately absorbs a failing batch and continues,
    so a run in which *every* batch failed still returns normally, with
    classified=0. Recording that as ok makes the failure invisible in the only
    two places anyone would look: the backoff stays disengaged, so a dead API key
    is retried at full cadence and full cost, and the page keeps reporting a
    healthy "Dernière vérification" while the pending count never moves.

    Partial progress still counts as ok. If some batches landed the classifier
    works, and the remainder will be picked up next cycle — backing off there
    would slow down a run that is succeeding.
    """
    return not (classified == 0 and failed > 0)


def backoff_delay(interval_seconds: int, failures: int) -> int:
    """Seconds to wait after `failures` consecutive failed cycles.

    Doubles per failure, capped at 8x so a 10-minute cadence stretches to at most
    80 minutes rather than growing without bound.
    """
    if failures <= 0:
        return interval_seconds
    return interval_seconds * min(2**failures, 8)


def _suppressed_by_backoff(interval_seconds: int) -> bool:
    """Should this scheduled run stand down?

    Only consulted with --respect-backoff, i.e. under cron. The process cannot
    remember previous failures, so ask the run history: if the last cycles failed
    and the widened interval has not elapsed, skip without touching the API.

    Any error here is deliberately non-fatal — a backoff check that cannot read
    the database must not stop the refresh it is meant to pace.
    """
    try:
        with session_scope() as session:
            runs = IngestRunRepository(session)
            failures = runs.consecutive_failures()
            if failures == 0:
                return False
            last = runs.latest()
            if last is None:
                return False
            delay = backoff_delay(interval_seconds, failures)
            # finished_at is always written in UTC, but not every backend hands it
            # back with a tzinfo — SQLite drops it. Reading a naive value as local
            # time would shift the comparison by the host's UTC offset and silently
            # defeat the backoff, so pin it to UTC rather than assume.
            finished = last.finished_at
            if finished.tzinfo is None:
                finished = finished.replace(tzinfo=timezone.utc)
            waited = (datetime.now(timezone.utc) - finished).total_seconds()
            if waited < delay:
                logger.warning(
                    "refresh_backoff failures=%s waited=%ss needs=%ss — skipping this run",
                    failures,
                    int(waited),
                    delay,
                )
                return True
            return False
    except Exception as exc:  # noqa: BLE001 — never let pacing block refreshing
        logger.warning("refresh_backoff_check_failed %s — running anyway", exc)
        return False


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
        help="Cadence (default 900 = 15 min, ~38%% of the free daily quota)",
    )
    parser.add_argument(
        "--respect-backoff",
        action="store_true",
        help=(
            "Skip this run if recent runs failed and the backoff window has not "
            "elapsed. For cron, which cannot keep the counter in memory. Manual "
            "one-shot runs omit it so seeding is never silently skipped."
        ),
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
        "refresh_start channel=%s loop=%s interval=%ss respect_backoff=%s",
        channel_id,
        args.loop,
        args.interval_seconds,
        args.respect_backoff,
    )

    # Checked before the first cycle in either mode: a restarted loop container
    # has forgotten its counter just as thoroughly as a fresh cron run has.
    if args.respect_backoff and _suppressed_by_backoff(args.interval_seconds):
        return 0

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
        # hammer the API at full cadence for a day.
        delay = backoff_delay(args.interval_seconds, failures)
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
