#!/usr/bin/env python3
"""
CLI: compose the weekly French editorial memo over the real catalogue.

Runs once by default (cron, a Railway scheduled job, an n8n node) or as a loop
for a long-lived container. Composition is deterministic and touches no external
API, so a repeated run costs one read of the database and nothing else.

The two post-conditions are enforced *here*, before anything is written or
printed: a memo carrying a hand-typed figure, or funnel vocabulary outside the
section that disowns it, is a failure and exits non-zero rather than landing in
`reports/` looking exactly like a good one.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType

from app.db.session import create_db_engine, create_session_factory, session_scope
from app.services.automation import MEMO_AUTOMATION, record_run
from app.services.memo import build_editorial_memo, write_memo
from app.skills.memo_generation import (
    EditorialMemo,
    MemoError,
    funnel_vocabulary_leaks,
    undeclared_figures,
)

logger = logging.getLogger("memo")

_stopping = False


def _request_stop(signum: int, _frame: FrameType | None) -> None:
    """Finish the current cycle, then exit — never leave a half-written memo."""
    global _stopping
    _stopping = True
    logger.info("memo_stop_requested signal=%s (finishing current cycle)", signum)


def verify(memo: EditorialMemo) -> list[str]:
    """Run both post-conditions and return human-readable failures."""
    problems: list[str] = []

    undeclared = undeclared_figures(memo)
    if undeclared:
        problems.append(
            "chiffres non déclarés (écrits à la main plutôt que dérivés) : "
            + ", ".join(undeclared)
        )

    leaks = funnel_vocabulary_leaks(memo)
    if leaks:
        problems.append(
            "vocabulaire de funnel hors de la section « limites » : "
            + ", ".join(f"{key} → « {term} »" for key, term in leaks)
        )
    return problems


def run_once(session_factory, *, write: bool, directory: Path | None) -> int:
    """Compose, verify, then emit. Returns a process exit code.

    Every outcome is recorded, including the ones that produce nothing. A cron
    job that silently stops working leaves no trace otherwise, and "no memo
    arrived" is indistinguishable from "no memo was due".
    """
    started_at = datetime.now(UTC)

    def _record(**fields) -> None:
        # Its own session: the run record has to survive whatever went wrong in
        # the transaction that was building the memo.
        try:
            with session_scope(session_factory) as session:
                record_run(session, automation=MEMO_AUTOMATION, started_at=started_at, **fields)
        except Exception:  # pragma: no cover - bookkeeping must never mask the outcome
            logger.exception("memo_run_record_failed")

    try:
        with session_scope(session_factory) as session:
            memo = build_editorial_memo(session)
    except MemoError as error:
        logger.error("memo_skipped reason=%s", error)
        _record(ok=False, error=f"catalogue insuffisant : {error}")
        return 1
    except Exception as error:
        logger.exception("memo_failed")
        _record(ok=False, error=f"{type(error).__name__}: {error}")
        raise

    problems = verify(memo)
    if problems:
        for problem in problems:
            logger.error("memo_rejected %s", problem)
        _record(
            ok=False,
            error="post-conditions non satisfaites : " + " ; ".join(problems),
            details={"sections": len(memo.sections), "rejected": True},
        )
        return 2

    path = write_memo(memo, directory=directory) if write else None
    _record(
        ok=True,
        artifact_path=str(path) if path else None,
        # The markdown is stored, not just the path. On Railway this runs as a
        # cron container whose filesystem is discarded when it exits, so the file
        # under reports/ is gone by the time anyone looks — an artifact_path
        # pointing at nothing is worse than no path at all. The database is the
        # only durable copy, and it is what the dashboard reads back.
        details={
            "sections": len(memo.sections),
            "figures": len(memo.figures),
            "title": memo.title,
            "markdown": memo.markdown,
        },
    )

    if path is not None:
        logger.info("memo_written path=%s sections=%s", path, len(memo.sections))
        print(path)
    else:
        print(memo.markdown)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compose the weekly editorial memo")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write dated markdown under reports/ instead of printing it",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Where --write puts the memo (default: reports/)",
    )
    parser.add_argument(
        "--loop", action="store_true", help="Keep composing until stopped"
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=604_800,
        help="Loop cadence; defaults to one week",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    signal.signal(signal.SIGTERM, _request_stop)

    directory = Path(args.output_dir) if args.output_dir else None
    session_factory = create_session_factory(create_db_engine())

    logger.info(
        "memo_start loop=%s interval=%ss write=%s at=%s",
        args.loop,
        args.interval_seconds,
        args.write,
        datetime.now(UTC).isoformat(),
    )

    while True:
        code = run_once(session_factory, write=args.write, directory=directory)
        if not args.loop:
            return code
        if _stopping:
            logger.info("memo_stopped")
            return code
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
