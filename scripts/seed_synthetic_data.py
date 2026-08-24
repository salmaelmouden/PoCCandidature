#!/usr/bin/env python3
"""Seed labelled synthetic data into PostgreSQL (idempotent)."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from app.config import get_settings
from app.db import create_db_engine, create_session_factory, session_scope
from app.db.constants import DATASET_LABEL
from app.db.loader import load_synthetic_dataset, purge_synthetic_dataset
from app.db.synthetic import generate_synthetic_dataset

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed SYNTHETIC growth data (labelled).")
    parser.add_argument("--days", type=int, default=None, help="Number of days to generate")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for determinism")
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
        help="End of the generated window (default: today)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Delete the labelled dataset before loading. Use this to re-seed a database "
            "written by an older generator: without it the load upserts, which corrects "
            "the rows it regenerates but leaves behind any it no longer produces."
        ),
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    days = args.days or settings.synthetic_days
    seed = args.seed if args.seed is not None else settings.synthetic_seed

    logger.info(
        "Generating synthetic dataset label=%s seed=%s days=%s as_of=%s (NOT real company data)",
        DATASET_LABEL,
        seed,
        days,
        args.as_of or "today",
    )
    dataset = generate_synthetic_dataset(seed=seed, days=days, as_of=args.as_of)

    engine = create_db_engine()
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        # Same transaction as the load on purpose: a purge that commits on its own
        # would empty the demo for as long as the load takes, and leave it empty for
        # good if the load then fails.
        if args.reset:
            removed = purge_synthetic_dataset(session, label=DATASET_LABEL)
            logger.info("Reset removed rows labelled %s: %s", DATASET_LABEL, removed)
        counts = load_synthetic_dataset(session, dataset)

    logger.info("Seed complete: %s", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
