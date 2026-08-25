"""Editorial memo application service — repositories + skills, no UI, no prose.

The memo's wording lives in `app.skills.memo_generation`. This module only
decides what the memo is allowed to know, and it deliberately reuses the same
loaders the dashboard reads: the Monday memo and the page a reader opens on
Monday afternoon must not be able to disagree about the same week.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.observability import observation
from app.services.public_signals import (
    build_movement_report,
    build_public_signal_report,
    build_title_evidence,
    get_catalogue_freshness,
)
from app.skills.content_classification.schemas import CLASSIFICATION_VERSION
from app.skills.memo_generation import (
    EditorialMemo,
    MemoCandidate,
    MemoInput,
    generate_editorial_memo,
    memo_filename,
)

REPORTS_DIR = Path("reports")


def build_editorial_memo(
    session: Session,
    *,
    dataset_label: str = "youtube_api",
    version: str = CLASSIFICATION_VERSION,
    generated_on: date | None = None,
    candidate_limit: int = 5,
) -> EditorialMemo:
    """Assemble the week's facts and compose the memo.

    `build_movement_report` returning `None` is an ordinary state, not an error:
    week-over-week movement needs two snapshots, and a freshly deployed database
    has one. The skill renders that absence explicitly rather than being handed a
    zero it would report as "nothing moved".
    """
    with observation(
        "build_editorial_memo",
        input={"dataset_label": dataset_label, "version": version},
        tags=["memo", "catalogue"],
    ):
        report = build_public_signal_report(
            session, dataset_label=dataset_label, version=version
        )
        movement = build_movement_report(
            session, dataset_label=dataset_label, version=version
        )
        freshness = get_catalogue_freshness(
            session, dataset_label=dataset_label, version=version
        )
        evidence = build_title_evidence(
            session, dataset_label=dataset_label, version=version, limit=candidate_limit
        )

        candidates = [
            MemoCandidate(
                title=item.signal.title,
                reach_index=item.reach_index,
                published_year=item.signal.published_at.year,
            )
            for item in (evidence.candidates if evidence else [])
        ]

        return generate_editorial_memo(
            MemoInput(
                report=report,
                movement=movement,
                videos=freshness.videos,
                classified=freshness.classified,
                last_checked_at=freshness.last_checked_at,
                last_changed_at=freshness.last_changed_at,
                candidates=candidates,
                generated_on=generated_on or datetime.now(UTC).date(),
            )
        )


def write_memo(
    memo: EditorialMemo,
    *,
    directory: Path | None = None,
    moment: datetime | None = None,
) -> Path:
    """Persist the memo as dated markdown and return where it landed."""
    target = directory or REPORTS_DIR
    target.mkdir(parents=True, exist_ok=True)
    path = target / memo_filename(memo, moment=moment)
    path.write_text(memo.markdown, encoding="utf-8")
    return path
