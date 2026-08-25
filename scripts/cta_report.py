#!/usr/bin/env python3
"""CLI: print where the funnel's entry point sits in the ingested catalogue."""

from __future__ import annotations

import argparse
import logging
import sys

from app.db.session import create_db_engine, create_session_factory, session_scope
from app.services.public_signals import build_cta_report
from app.skills.cta_analysis import CtaReport, PlacementStat, TrackingState


def _table(title: str, rows: list[PlacementStat]) -> None:
    print(f"\n=== {title} ===")
    if not rows:
        print("  (aucune tranche)")
        return
    print(
        f"  {'tranche':<16}{'n':>6}{'avec lien':>12}{'visible':>10}"
        f"{'attribuable':>14}{'pos. med.':>11}{'vues sans lien':>16}"
    )
    for row in rows:
        median = "—" if row.median_offset is None else f"{row.median_offset:.0f}"
        print(
            f"  {row.value:<16}{row.videos:>6}"
            f"{row.share_with_primary * 100:>11.1f}%"
            f"{row.share_above_fold * 100:>9.1f}%"
            f"{row.share_tracked * 100:>13.1f}%"
            f"{median:>11}"
            f"{(1 - row.view_share_with_primary) * 100:>15.1f}%"
        )


def render(report: CtaReport) -> None:
    coverage = report.coverage
    print("=" * 78)
    print("PORTE D'ENTREE DU FUNNEL — TABLE DE PREUVES")
    print("=" * 78)
    print(f"periode         : {report.period_start:%Y-%m-%d} -> {report.period_end:%Y-%m-%d}")
    print(f"videos          : {coverage.videos_total}")
    print(f"avec description: {coverage.described}")
    print(f"avec un lien    : {coverage.with_any_link}")
    print(f"avec lien produit: {coverage.with_primary}")
    print(f"domaine produit : {coverage.primary_domain or '(aucun)'}")
    print(f"                  {coverage.primary_domain_reason}")

    print(
        "\n'visible' = part des videos PORTANT un lien dont le lien precede le repli "
        "de la description.\n'pos. med.' = position du premier lien en caracteres, "
        "sans seuil.\n'vues sans lien' = part des vues cumulees sur une video sans "
        "lien produit."
    )

    _table("FORMAT", report.by_format)
    _table("ANNEE DE PUBLICATION", report.by_year)
    _table("CATALOGUE", [report.overall])

    print("\n=== ATTRIBUTION (videos portant un lien produit) ===")
    counted = {state: 0 for state in TrackingState}
    for placement in report.placements:
        if placement.has_primary:
            counted[placement.tracking] += 1
    for state in (TrackingState.TRACKED, TrackingState.OPAQUE, TrackingState.UNTRACKED):
        print(f"  {state.value:<12}{counted[state]:>6}")

    print("\n=== DOMAINES LES PLUS LIES ===")
    print(f"  {'domaine':<40}{'type':<14}{'videos':>8}")
    for row in report.domains:
        marker = " *" if row.domain == coverage.primary_domain else ""
        print(f"  {row.domain:<40}{row.kind.value:<14}{row.videos:>8}{marker}")

    if report.cta_lines:
        print("\n=== FORMULATIONS ===")
        for line in report.cta_lines:
            print(f"  {line.videos:>5}  {line.template[:90]}")

    print(
        "\nNOTE: emplacement uniquement. Les clics, les inscriptions et la conversion "
        "ne sont pas\nobservables de l'exterieur d'une chaine et ne sont jamais estimes ici."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Funnel entry-point evidence table")
    parser.add_argument("--dataset-label", default="youtube_api")
    parser.add_argument(
        "--primary-domain",
        default=None,
        help="Pin the product domain instead of deriving it from link frequency.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    engine = create_db_engine()
    factory = create_session_factory(engine)
    with session_scope(factory) as session:
        report = build_cta_report(
            session,
            dataset_label=args.dataset_label,
            primary_domain=args.primary_domain,
        )
    if report is None:
        print("Catalogue vide — rien a analyser. Lancer `make ingest-youtube` d'abord.")
        return 1
    render(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
