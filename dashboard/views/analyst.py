"""Analyste de données — « qu'est-ce qui se passe ? », preuves à l'appui.

Présentation uniquement : l'agent choisit ses outils et produit son rapport.
"""

from __future__ import annotations

import streamlit as st

from app.agents.growth_data_analyst_agent import AnalystQuestion, GrowthDataAnalystAgent
from app.agents.growth_data_analyst_agent.prompts import DEFAULT_PREMIUM_QUESTION
from app.observability import flush_tracing
from dashboard import agent_view, components
from dashboard.db import db_session
from dashboard.ui import (
    channel_label,
    data_provenance_banner,
    fmt_period,
    page_header,
    render_claims,
    section,
    sidebar_filters,
)

EXAMPLE_QUESTIONS = [
    DEFAULT_PREMIUM_QUESTION,
    "Where is the funnel bottleneck right now?",
    "Which channel is leaking the most at Premium?",
    "Which topics have high reach but low conversion?",
    "What changed in the funnel vs the previous period?",
    "Any traffic anomalies this period?",
]

STORE = "analyst_run"

days, channel = sidebar_filters()

page_header(
    "Analyste de données",
    "Des preuves structurées pour « qu'est-ce qui se passe ? ». Les outils sont "
    "choisis à partir de la question — un goulot, un sujet et une anomalie ne "
    "mobilisent pas les mêmes.",
    chips=(
        (f"{days} jours glissants", False),
        (channel_label(channel), False),
        ("Rapport FAIT / INTERPRÉTATION", True),
    ),
)

question, run = agent_view.question_form(
    "analyst_question",
    EXAMPLE_QUESTIONS,
    default=DEFAULT_PREMIUM_QUESTION,
    run_label="Lancer l'analyste",
    help_text="Les questions d'exemple sont laissées en anglais : ce sont les "
    "intentions que le routage de l'agent sait reconnaître.",
)

if run and question.strip():
    with st.status("L'analyste choisit ses outils…", expanded=False) as status:
        with db_session() as session:
            report = GrowthDataAnalystAgent().run(
                session,
                AnalystQuestion(question=question, days=days, channel=channel),
            )
        flush_tracing()
        status.update(
            label=f"{len(report.tool_calls)} outil(s) appelé(s), "
            f"{len(report.claims)} assertion(s)",
            state="complete",
        )
    st.session_state[STORE] = agent_view.AgentRun(report, question, days, channel)

stored: agent_view.AgentRun | None = st.session_state.get(STORE)

if stored is None:
    agent_view.empty_state(
        "Choisis un exemple ou écris ta question, puis lance l'analyste. "
        "Le résultat reste affiché tant que tu ne relances pas."
    )
    st.stop()

report = stored.report
agent_view.stale_notice(stored, days=days, channel=channel)

has_synthetic, labels = agent_view.provenance_of(report.tool_calls)
data_provenance_banner(has_synthetic=has_synthetic, labels=labels)

st.caption(
    f"Question analysée : « {stored.question} » · "
    f"{fmt_period(report.period_start, report.period_end)} · "
    f"{channel_label(stored.channel)}"
)

if report.primary_driver:
    st.markdown(
        components.insight_card(
            "Facteur principal",
            report.primary_driver,
            badge_text="Conclusion de l'agent",
            badge_kind="interpretation",
        ),
        unsafe_allow_html=True,
    )

if report.insufficient_evidence:
    st.warning(
        "Preuves insuffisantes — ne traite pas ceci comme une explication complète.",
        icon="⚠️",
    )

section(
    "Assertions",
    index="02",
    note="Chaque assertion porte son étiquette : un FAIT remonte à un résultat "
    "d'outil, une INTERPRÉTATION est un raisonnement construit sur ces faits. "
    "Cet agent n'émet pas de recommandation — c'est le rôle du stratège.",
)
render_claims(report.claims)

agent_view.tool_log(report.tool_calls)
