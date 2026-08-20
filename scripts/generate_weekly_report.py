"""CLI: generate weekly growth report markdown."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from app.db.session import session_scope
from app.services.reports import build_weekly_report, write_report_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly growth report")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--channel", default=None)
    parser.add_argument("--no-orchestrator", action="store_true")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output markdown path (default reports/weekly_<ts>.md)",
    )
    args = parser.parse_args()

    with session_scope() as session:
        report = build_weekly_report(
            session,
            days=args.days,
            channel=args.channel,
            include_orchestrator=not args.no_orchestrator,
        )

    out = args.out
    if out is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = Path("reports") / f"weekly_{stamp}.md"
    write_report_markdown(report, out)
    print(f"Wrote {out}")
    print(report.markdown[:500], "...", sep="\n")


if __name__ == "__main__":
    main()
