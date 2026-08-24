"""Expérimentations — analyser un A/B stocké ou proposer un test.

Présentation uniquement : l'agent expérimentation fait le travail.
"""

from __future__ import annotations

import streamlit as st

from app.agents.growth_experiment_analyst_agent import (
    ExperimentAnalystQuestion,
    GrowthExperimentAnalystAgent,
)
from app.agents.growth_experiment_analyst_agent.prompts import (
    DEFAULT_EXPERIMENT_QUESTION,
    DEFAULT_PROPOSE_QUESTION,
)
from app.observability import flush_tracing
from dashboard import agent_view, components
from dashboard.db import db_session
from dashboard.formatting import DECISION_FR
from dashboard.ui import (
    channel_label,
    data_provenance_banner,
    page_header,
    render_claims,
    section,
    sidebar_filters,
)

EXAMPLE_QUESTIONS = [
    DEFAULT_EXPERIMENT_QUESTION,
    DEFAULT_PROPOSE_QUESTION,
    "Analyze experiment syn_exp_youtube_cta",
]

STORE = "experiment_run"

#: A decision hint is a signal, not a verdict — the colour says which way it
#: leans without ever reading as "ship it".
DECISION_KIND = {
    "ship_treatment": "good",
    "keep_control": "neutral",
    "inconclusive": "warning",
    "underpowered": "serious",
}

days, channel = sidebar_filters()

page_header(
    "Expérimentations",
    "Analyser un test déjà mesuré, ou concevoir celui qui manque — avec le "
    "critère de décision posé avant de regarder le résultat.",
    chips=(
        (f"{days} jours glissants", False),
        (channel_label(channel), False),
        ("Lift, IC, test z", True),
    ),
)

question, run = agent_view.question_form(
    "exp_question",
    EXAMPLE_QUESTIONS,
    default=DEFAULT_EXPERIMENT_QUESTION,
    run_label="Lancer le spécialiste",
    help_text="Le jeu synthétique contient `syn_exp_youtube_cta`. Demande s'il a "
    "fonctionné, ou comment tester une baisse de conversion Premium.",
)

if run and question.strip():
    with st.status("Analyse de l'expérimentation…", expanded=False) as status:
        with db_session() as session:
            report = GrowthExperimentAnalystAgent().run(
                session,
                ExperimentAnalystQuestion(question=question, days=days, channel=channel),
            )
        flush_tracing()
        status.update(
            label=f"Mode « {report.mode.value} » — {len(report.tool_calls)} outil(s)",
            state="complete",
        )
    st.session_state[STORE] = agent_view.AgentRun(report, question, days, channel)

stored: agent_view.AgentRun | None = st.session_state.get(STORE)

if stored is None:
    agent_view.empty_state(
        "Pose une question et lance le spécialiste. Le résultat reste affiché "
        "tant que tu ne relances pas."
    )
    st.stop()

report = stored.report
agent_view.stale_notice(stored, days=days, channel=channel)

has_synthetic, labels = agent_view.provenance_of(report.tool_calls)
data_provenance_banner(has_synthetic=has_synthetic, labels=labels)

cols = st.columns(2, gap="medium")
cols[0].markdown(
    components.insight_card(
        "Mode",
        "Analyse d'un test existant" if report.mode.value == "analyze" else "Proposition de test",
        note=f"Expérimentation : {report.experiment_key}"
        if report.experiment_key
        else f"Question : « {stored.question} »",
        badge_text="Spécialiste expérimentation",
        badge_kind="fact",
    ),
    unsafe_allow_html=True,
)
if report.decision_hint:
    cols[1].markdown(
        components.insight_card(
            "Indication de décision",
            DECISION_FR.get(report.decision_hint.value, report.decision_hint.value),
            note="Une indication statistique, pas une décision : le coût du "
            "déploiement et le contexte produit ne sont pas dans les chiffres.",
            badge_text="Signal",
            badge_kind=DECISION_KIND.get(report.decision_hint.value, "neutral"),
        ),
        unsafe_allow_html=True,
    )

if report.insufficient_evidence:
    st.warning("Preuves insuffisantes.", icon="⚠️")

if report.design:
    section(
        "Design proposé",
        index="02",
        note="Le critère de succès est posé d'avance — c'est ce qui empêche de "
        "relire le résultat jusqu'à ce qu'il dise oui.",
    )
    design = report.design
    with st.container(border=True):
        st.markdown(
            components.badge("Hypothèse", "recommendation")
            + f'&nbsp;&nbsp;<strong style="font-size:1rem">{design.name}</strong>',
            unsafe_allow_html=True,
        )
        st.write(design.hypothesis)
        st.caption(f"Métrique principale : {design.primary_metric}")

    bras = st.columns(2, gap="medium")
    bras[0].markdown(
        components.insight_card(
            "Contrôle", design.control_description, badge_text="A", badge_kind="neutral"
        ),
        unsafe_allow_html=True,
    )
    bras[1].markdown(
        components.insight_card(
            "Variante", design.treatment_description, badge_text="B", badge_kind="fact"
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        components.banner(
            f"<strong>Critère de succès&nbsp;:</strong> {design.success_criteria}",
            icon="◆",
        ),
        unsafe_allow_html=True,
    )

section(
    "Assertions",
    index="03" if report.design else "02",
    note="Les chiffres attachés à chaque assertion sont ceux qu'a renvoyés la "
    "compétence d'analyse d'expérimentation.",
)
render_claims(report.claims)

agent_view.tool_log(report.tool_calls)
