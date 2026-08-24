"""Shared presentation for the three agent pages — form, results shell, tool log.

The analyst, the orchestrator and the experiment analyst all follow the same
interaction: pick or write a question, run, read evidence. Keeping that shell in
one place is not only less code — it is what makes the three pages *feel* like
one product, and it is where the one real ergonomic fix lives: a result that
survives the next rerun instead of vanishing when you open an expander.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

import streamlit as st

from dashboard import components
from dashboard.formatting import channel_label


@dataclass(frozen=True)
class AgentRun:
    """A stored result, kept with the filters it was actually computed under."""

    report: Any
    question: str
    days: int
    channel: str | None

    def matches(self, *, days: int, channel: str | None) -> bool:
        return self.days == days and self.channel == channel


def question_form(
    key: str,
    examples: Sequence[str],
    *,
    default: str,
    run_label: str,
    help_text: str,
) -> tuple[str, bool]:
    """Example pills, a free-text question, and the run button.

    Pills are drawn before the text area on purpose: clicking one reruns the
    script, and the selection has to land in session state *before* the text
    area is instantiated, otherwise Streamlit refuses to change it.
    """
    state = st.session_state
    state.setdefault(key, default)

    st.markdown(components.section("Question", index="01", note=help_text), unsafe_allow_html=True)

    picked = st.pills(
        "Exemples",
        options=list(examples),
        selection_mode="single",
        default=None,
        key=f"{key}_pills",
        label_visibility="collapsed",
    )
    if picked and state.get(f"{key}_picked") != picked:
        state[f"{key}_picked"] = picked
        state[key] = picked

    question = st.text_area(
        "Question",
        key=key,
        height=90,
        label_visibility="collapsed",
        placeholder="Pose ta question…",
    )
    run = st.button(run_label, type="primary", icon=":material/play_arrow:")
    return question, run


def stale_notice(stored: AgentRun, *, days: int, channel: str | None) -> None:
    """Say so when the displayed result predates the current filter selection."""
    if stored.matches(days=days, channel=channel):
        return
    st.markdown(
        components.banner(
            "Ce résultat a été produit pour "
            f"<strong>{stored.days} jours · {channel_label(stored.channel)}</strong>, "
            "et les filtres ont changé depuis. Relance pour l'aligner.",
            icon="◆",
        ),
        unsafe_allow_html=True,
    )


def provenance_of(tool_calls: Iterable[Any]) -> tuple[bool, set[str]]:
    """Dataset labels and the synthetic flag, read back off the tool results."""
    labels: set[str] = set()
    has_synthetic = False
    for call in tool_calls:
        if not getattr(call, "ok", False):
            continue
        detail = getattr(call, "detail", {}) or {}
        if detail.get("dataset_labels"):
            labels.update(detail["dataset_labels"])
        if detail.get("has_synthetic"):
            has_synthetic = True
    return has_synthetic, labels


def tool_log(tool_calls: Sequence[Any], *, label: str = "Outils appelés") -> None:
    """The agent's working, folded away — visible enough to be checkable."""
    if not tool_calls:
        return
    failures = sum(1 for call in tool_calls if not getattr(call, "ok", False))
    suffix = f" — {failures} en échec" if failures else ""
    with st.expander(f"{label} ({len(tool_calls)}){suffix}"):
        st.dataframe(
            [
                {
                    "": "✓" if getattr(call, "ok", False) else "✕",
                    "Outil": getattr(call, "tool", ""),
                    "Résultat": getattr(call, "summary", ""),
                }
                for call in tool_calls
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "": st.column_config.TextColumn(width="small"),
                "Outil": st.column_config.TextColumn(width="medium"),
                "Résultat": st.column_config.TextColumn(width="large"),
            },
        )


def empty_state(message: str) -> None:
    st.markdown(
        components.banner(message, icon="◆"),
        unsafe_allow_html=True,
    )
