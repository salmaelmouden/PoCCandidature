#!/usr/bin/env python3
"""CLI: classify ingested video titles into topic + hook_type (idempotent)."""

from __future__ import annotations

import argparse
import logging
import sys

from app.config import get_settings
from app.db.session import create_db_engine, create_session_factory, session_scope
from app.skills.content_classification import (
    CLASSIFICATION_VERSION,
    ClassifyContentRequest,
    build_classifier,
    classify_channel_content,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify video titles (topic + hook)")
    parser.add_argument("--dataset-label", default="youtube_api")
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None, help="Classify at most N videos")
    parser.add_argument("--version", default=CLASSIFICATION_VERSION)
    parser.add_argument("--force", action="store_true", help="Re-classify already-done videos")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # httpx/anthropic log request URLs at INFO — keep credentials out of stdout.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = get_settings()

    if not settings.anthropic_api_key:
        logging.warning(
            "ANTHROPIC_API_KEY is not set — the deterministic keyword fallback will be "
            "used and labels will be low quality."
        )

    classifier = build_classifier(
        settings.anthropic_api_key,
        model=settings.llm_model,
        ca_bundle_path=settings.ca_bundle_path,
    )
    request = ClassifyContentRequest(
        dataset_label=args.dataset_label,
        batch_size=args.batch_size or settings.llm_batch_size,
        limit=args.limit,
        version=args.version,
        force=args.force,
    )

    engine = create_db_engine()
    factory = create_session_factory(engine)
    with session_scope(factory) as session:
        result = classify_channel_content(session, classifier, request)

    logging.info(
        "Done: classified=%s skipped=%s failed=%s model=%s version=%s fallback=%s",
        result.classified,
        result.skipped_already_done,
        result.failed,
        result.model,
        result.version,
        result.used_fallback,
    )
    return 1 if result.failed and not result.classified else 0


if __name__ == "__main__":
    sys.exit(main())
