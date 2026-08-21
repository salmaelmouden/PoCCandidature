#!/usr/bin/env python3
"""CLI: print the public-signal evidence table for the ingested catalogue."""

from __future__ import annotations

import argparse
import logging
import sys

from app.db.session import create_db_engine, create_session_factory, session_scope
from app.services.public_signals import build_public_signal_report
from app.skills.public_signal_analysis import DimensionStat, PublicSignalReport


def _table(title: str, rows: list[DimensionStat], note: str = "") -> None:
    print(f"\n=== {title} ===")
    if note:
        print(f"({note})")
    if not rows:
        print("  (aucune valeur au-dessus du seuil de report)")
        return
    print(f"  {'valeur':<24}{'n':>5}{'reach':>9}{'engagement':>13}{'part':>8}")
    for row in rows:
        print(
            f"  {row.value:<24}{row.videos:>5}"
            f"{row.median_reach_index:>9.2f}"
            f"{row.median_engagement_rate * 100:>12.2f}%"
            f"{row.share_of_catalogue * 100:>7.1f}%"
        )


def render(report: PublicSignalReport) -> None:
    coverage = report.coverage
    print("=" * 68)
    print("SIGNAUX PUBLICS — TABLE DE PREUVES")
    print("=" * 68)
    print(f"periode        : {report.period_start:%Y-%m-%d} -> {report.period_end:%Y-%m-%d}")
    print(f"videos totales : {coverage.videos_total}")
    print(
        f"videos indexees: {coverage.videos_indexed} "
        f"({100 * coverage.videos_indexed / max(coverage.videos_total, 1):.0f}%)"
    )
    print(f"videos exclues : {coverage.videos_excluded} — {coverage.excluded_reason}")
    print(f"cohortes       : {coverage.cohorts_used} retenues, {coverage.cohorts_dropped} ecartees")
    print(
        "\nreach = vues mediane rapportees a la cohorte (format x trimestre). "
        "1.00 = typique.\nengagement = (likes + commentaires) / vues."
    )

    _table("FORMAT", report.by_format)
    _table("TOPIC — tous formats", report.by_topic)
    _table("HOOK — tous formats", report.by_hook)
    _table("TOPIC — Shorts", report.by_topic_short)
    _table("TOPIC — format long", report.by_topic_long)
    _table("HOOK — Shorts", report.by_hook_short)
    _table("HOOK — format long", report.by_hook_long)

    print(
        "\nNOTE: donnees publiques uniquement. Les signups et la conversion ne sont "
        "pas observables\nde l'exterieur d'une chaine et ne sont jamais estimes ici."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Public-signal evidence table")
    parser.add_argument("--dataset-label", default="youtube_api")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    engine = create_db_engine()
    factory = create_session_factory(engine)
    with session_scope(factory) as session:
        report = build_public_signal_report(session, dataset_label=args.dataset_label)
    render(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
