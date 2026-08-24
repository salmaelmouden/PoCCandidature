"""Orchestrateur — point d'entrée IA principal (ADR-004).

Route vers l'analyste et/ou le stratège, puis synthétise. Présentation seulement.
"""

from __future__ import annotations

import streamlit as st

from app.agents.growth_orchestrator_agent import GrowthOrchestratorAgent, OrchestratorQuestion
from app.agents.growth_orchestrator_agent.prompts import DEFAULT_ORCHESTRATOR_QUESTION
from app.observability import flush_tracing
from dashboard import agent_view, components
from dashboard.db import db_session
from dashboard.formatting import DECISION_FR, ROUTE_FR
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
    DEFAULT_ORCHESTRATOR_QUESTION,
    "What should we do about the Premium conversion drop?",
    "Did the YouTube CTA experiment work?",
    "How should we test the Premium conversion drop?",
    "Where is the funnel bottleneck right now?",
]

STORE = "orchestrator_run"
PRIORITY_KIND = {"P0": "critical", "P1": "serious", "P2": "neutral"}

days, channel = sidebar_filters()

page_header(
    "Orchestrateur",
    "Le point d'entrée : la question est routée vers les spécialistes qu'elle "
    "appelle — diagnostic, action, ou expérimentation — puis synthétisée.",
    chips=(
        (f"{days} jours glissants", False),
        (channel_label(channel), False),
        ("Routage automatique", True),
    ),
)

question, run = agent_view.question_form(
    "orch_question",
    EXAMPLE_QUESTIONS,
    default=DEFAULT_ORCHESTRATOR_QUESTION,
    run_label="Lancer l'orchestrateur",
    help_text="Un diagnostic part chez l'analyste, une demande d'action chez le "
    "stratège, une question d'A/B test chez le spécialiste expérimentation.",
)

if run and question.strip():
    with st.status("Routage de la question…", expanded=False) as status:
        with db_session() as session:
            resp = GrowthOrchestratorAgent().run(
                session,
                OrchestratorQuestion(question=question, days=days, channel=channel),
            )
        flush_tracing()
        status.update(
            label=f"Route « {ROUTE_FR.get(resp.route.value, resp.route.value)} » — "
            f"{len(resp.agents_called)} agent(s)",
            state="complete",
        )
    st.session_state[STORE] = agent_view.AgentRun(resp, question, days, channel)

stored: agent_view.AgentRun | None = st.session_state.get(STORE)

if stored is None:
    agent_view.empty_state(
        "Pose une question et lance l'orchestrateur. Le résultat reste affiché "
        "tant que tu ne relances pas."
    )
    st.stop()

resp = stored.report
agent_view.stale_notice(stored, days=days, channel=channel)

has_synthetic, labels = agent_view.provenance_of(
    resp.analyst_report.tool_calls if resp.analyst_report else []
)
data_provenance_banner(has_synthetic=has_synthetic, labels=labels)

route_left, route_right = st.columns([2, 3], gap="medium")
route_left.markdown(
    components.insight_card(
        "Route retenue",
        ROUTE_FR.get(resp.route.value, resp.route.value),
        note="Agents mobilisés : " + (", ".join(resp.agents_called) or "aucun"),
        badge_text="Routage",
        badge_kind="fact",
    ),
    unsafe_allow_html=True,
)
route_right.markdown(
    components.insight_card(
        "Synthèse",
        resp.summary,
        note=f"« {stored.question} » · "
        f"{fmt_period(resp.period_start, resp.period_end)} · "
        f"{channel_label(stored.channel)}",
        badge_text="Orchestrateur",
        badge_kind="interpretation",
    ),
    unsafe_allow_html=True,
)

if resp.insufficient_evidence:
    st.warning("Preuves insuffisantes chez au moins un spécialiste.", icon="⚠️")

# ---- analyste --------------------------------------------------------------

if resp.analyst_report and resp.analyst_report.primary_driver:
    section("Facteur principal — analyste", index="02")
    st.markdown(
        components.insight_card(
            "Diagnostic",
            resp.analyst_report.primary_driver,
            badge_text="Analyste",
            badge_kind="fact",
        ),
        unsafe_allow_html=True,
    )

# ---- stratège --------------------------------------------------------------

if resp.strategy_report and resp.strategy_report.recommendations:
    section(
        "Recommandations — stratège",
        index="03",
        note="Chaque recommandation porte sa priorité, son action et le "
        "raisonnement qui la relie au diagnostic.",
    )
    for rec in resp.strategy_report.recommendations:
        with st.container(border=True):
            st.markdown(
                components.badge(rec.priority.value, PRIORITY_KIND.get(rec.priority.value, "neutral"))
                + f'&nbsp;&nbsp;<strong style="font-size:1rem">{rec.title}</strong>',
                unsafe_allow_html=True,
            )
            st.write(rec.action)
            st.caption(rec.rationale)

# ---- expérimentation -------------------------------------------------------

if resp.experiment_report:
    experiment = resp.experiment_report
    section("Spécialiste expérimentation", index="04")
    cols = st.columns(2, gap="medium")
    cols[0].markdown(
        components.insight_card(
            "Mode",
            "Analyse d'un test existant"
            if experiment.mode.value == "analyze"
            else "Proposition de test",
            note=f"Clé : {experiment.experiment_key}" if experiment.experiment_key else None,
            badge_text="Expérimentation",
            badge_kind="neutral",
        ),
        unsafe_allow_html=True,
    )
    if experiment.decision_hint:
        cols[1].markdown(
            components.insight_card(
                "Indication de décision",
                DECISION_FR.get(experiment.decision_hint.value, experiment.decision_hint.value),
                note="Indication, pas verdict : la décision reste humaine.",
                badge_text="Signal",
                badge_kind="good"
                if experiment.decision_hint.value == "ship_treatment"
                else "warning",
            ),
            unsafe_allow_html=True,
        )
    if experiment.design:
        st.markdown(
            components.insight_card(
                experiment.design.name,
                experiment.design.hypothesis,
                note=f"Métrique principale : {experiment.design.primary_metric}",
                badge_text="Design proposé",
                badge_kind="recommendation",
            ),
            unsafe_allow_html=True,
        )

# ---- assertions ------------------------------------------------------------

section(
    "Assertions",
    index="05",
    note="Synthèse des assertions des spécialistes, étiquettes conservées.",
)
render_claims(resp.claims)

for title, report in (
    ("Outils — analyste", resp.analyst_report),
    ("Outils — stratège", resp.strategy_report),
    ("Outils — expérimentation", resp.experiment_report),
):
    if report is not None:
        agent_view.tool_log(report.tool_calls, label=title)
