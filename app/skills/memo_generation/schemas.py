"""Contracts for the weekly French editorial memo."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.skills.catalogue_movement import MovementReport
from app.skills.public_signal_analysis import PublicSignalReport

#: Vocabulary that belongs to the funnel, not to public signals. The memo is
#: allowed to use these words in exactly one place — the section that exists to
#: say they are unmeasurable from outside a channel. Anywhere else they would
#: turn a reach observation into a conversion claim, which is the single failure
#: this whole track is built to avoid.
FUNNEL_VOCABULARY = (
    "inscription",
    "signup",
    "conversion",
    "converti",
    "abonnement",
    "abonné",
    "payant",
    "premium",
    "revenu",
    "chiffre d'affaires",
)

#: The only section permitted to name them.
LIMITS_SECTION_KEY = "limites"


class MemoCandidate(BaseModel):
    """One video the title recommendation applies to, already selected upstream."""

    title: str
    reach_index: float
    published_year: int


class MemoInput(BaseModel):
    """Everything the memo is allowed to know.

    The memo composes; it does not compute. Every figure it prints has to arrive
    through this object, which is what makes the "no undeclared number"
    post-condition enforceable rather than aspirational.
    """

    report: PublicSignalReport
    movement: MovementReport | None = None
    videos: int = Field(ge=0)
    classified: int = Field(ge=0)
    last_checked_at: datetime | None = None
    last_changed_at: datetime | None = None
    candidates: list[MemoCandidate] = Field(default_factory=list)
    hook: str = "question"
    generated_on: date


class MemoSection(BaseModel):
    """One block of the memo, carrying its own epistemic status."""

    key: str
    title: str
    body: str
    #: "fact" | "limit" | "method". There is deliberately no "recommendation":
    #: see the module docstring of `skill.py`.
    kind: str = "fact"


class EditorialMemo(BaseModel):
    """The rendered memo plus the audit trail that lets it be checked."""

    title: str
    generated_on: date
    period_start: date
    period_end: date
    sections: list[MemoSection]
    markdown: str
    #: Every numeric token the composer emitted. A number in `markdown` that is
    #: not in here was written by hand, and `undeclared_figures` will say so.
    figures: list[str]
    provenance: str


class MemoError(ValueError):
    """Raised when there is not enough catalogue to write a memo at all."""


__all__ = [
    "FUNNEL_VOCABULARY",
    "LIMITS_SECTION_KEY",
    "EditorialMemo",
    "MemoCandidate",
    "MemoError",
    "MemoInput",
    "MemoSection",
]
