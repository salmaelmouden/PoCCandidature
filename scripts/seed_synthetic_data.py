#!/usr/bin/env python3
"""Seed labelled synthetic data into PostgreSQL (idempotent)."""

from __future__ import annotations

import argparse
import logging
import sys

from app.config import get_settings
from app.db import create_db_engine, create_session_factory, session_scope
from app.db.loader import load_synthetic_dataset
from app.db.synthetic import generate_synthetic_dataset

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed SYNTHETIC growth data (labelled).")
    parser.add_argument("--days", type=int, default=None, help="Number of days to generate")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for determinism")
    args = parser.parse_args(argv)

    settings = get_settings()
    days = args.days or settings.synthetic_days
    seed = args.seed if args.seed is not None else settings.synthetic_seed

    logger.info(
        "Generating synthetic dataset label=synthetic_v1 seed=%s days=%s (NOT real company data)",
        seed,
        days,
    )
    dataset = generate_synthetic_dataset(seed=seed, days=days)

    engine = create_db_engine()
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        counts = load_synthetic_dataset(session, dataset)

    logger.info("Seed complete: %s", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
