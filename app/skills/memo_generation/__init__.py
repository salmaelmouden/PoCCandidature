"""Skill: memo_generation — weekly French editorial memo over the real catalogue."""

from app.skills.memo_generation.schemas import (
    FUNNEL_VOCABULARY,
    LIMITS_SECTION_KEY,
    EditorialMemo,
    MemoCandidate,
    MemoError,
    MemoInput,
    MemoSection,
)
from app.skills.memo_generation.skill import (
    THIN_THRESHOLD,
    funnel_vocabulary_leaks,
    generate_editorial_memo,
    memo_filename,
    undeclared_figures,
)

__all__ = [
    "FUNNEL_VOCABULARY",
    "LIMITS_SECTION_KEY",
    "THIN_THRESHOLD",
    "EditorialMemo",
    "MemoCandidate",
    "MemoError",
    "MemoInput",
    "MemoSection",
    "funnel_vocabulary_leaks",
    "generate_editorial_memo",
    "memo_filename",
    "undeclared_figures",
]
