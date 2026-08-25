"""Automatisation — l'historique des runs planifiés.

La page la moins spectaculaire du projet, et celle qui décide si le reste est
crédible. Un mémo hebdomadaire qui n'arrive plus ne produit aucun signal : pas
d'erreur à l'écran, pas de page cassée, juste une absence que personne ne
remarque. Cette page transforme cette absence en état affiché.

Présentation uniquement : le verdict est rendu par `app.services.automation`.
"""

from __future__ import annotations

import streamlit as st

from app.services.automation import MEMO_AUTOMATION, get_automation_health
from dashboard import components
from dashboard.automation_view import (
    headline_age,
    runs_frame,
    status_label,
    success_rate_label,
)
from dashboard.db import db_session
from dashboard.ui import page_header, section


@st.cache_data(ttl=60, show_spinner="Lecture de l'historique…")
def load():
    with db_session() as session:
        return get_automation_health(session, automation=MEMO_AUTOMATION, limit=10)


health = load()
label, kind, meaning = status_label(health)

page_header(
    "Automatisation",
    "Le mémo éditorial hebdomadaire tourne tout seul. Cette page dit s'il tourne "
    "encore — et ce qu'il faut croire de ce qu'il a produit.",
    chips=((label, health.status == "ok"),),
)

col_a, col_b = st.columns([1, 4])
with col_a:
    if st.button("Rafraîchir", width="stretch", icon=":material/refresh:"):
        load.clear()
        st.rerun()

st.markdown(components.badge(label, kind), unsafe_allow_html=True)
st.markdown(meaning)

# ---- l'état ----------------------------------------------------------------

k1, k2, k3, k4 = st.columns(4)
k1.metric("Dernier run", headline_age(health.last_run), border=True)
k2.metric("Dernier succès", headline_age(health.last_success), border=True)
k3.metric(
    "Échecs consécutifs",
    str(health.consecutive_failures),
    delta=None if not health.consecutive_failures else "depuis le dernier succès",
    delta_color="off",
    border=True,
)
k4.metric(
    "Taux de réussite",
    success_rate_label(health),
    delta=f"sur {len(health.runs)} runs" if health.runs else None,
    delta_color="off",
    border=True,
)

st.caption(
    "« Dernier run » et « dernier succès » sont deux questions différentes, et "
    "n'en montrer qu'une ment dans un sens ou dans l'autre : la première seule "
    "cache qu'un job échoue depuis des semaines, la seconde seule cache qu'il "
    "échoue depuis le dernier succès qu'elle affiche."
)

if health.status == "failing" and health.last_run is not None:
    st.error(
        f"**Le dernier run a échoué.** {health.last_run.error or 'Raison non enregistrée.'}",
        icon="🚨",
    )
elif health.status == "stale":
    st.warning(
        "**Aucun run récent.** Le dernier a réussi, mais un job planifié qui cesse "
        "d'être déclenché n'écrit aucune ligne d'erreur — il se contente de ne rien "
        "faire. Vérifie le planificateur avant de croire que rien n'a changé.",
        icon="⚠️",
    )
elif health.status == "never":
    st.info(
        "Aucun run enregistré pour l'instant. Lance `make memo-write`, ou importe "
        "le workflow n8n planifié, et cette page se remplira.",
        icon="ℹ️",
    )

# ---- l'historique ----------------------------------------------------------

section("Les derniers runs", index="01")

if not health.runs:
    st.caption("Rien à afficher tant qu'aucun run n'a été enregistré.")
else:
    st.dataframe(runs_frame(health), width="stretch", hide_index=True)
    st.caption(
        "Un échec est une ligne, pas une absence. Ne rien écrire quand un run "
        "échoue rendrait une automatisation cassée indiscernable d'une "
        "automatisation qui n'était pas encore due."
    )

# ---- ce que le mémo garantit -----------------------------------------------

section("Ce qu'un run réussi garantit", index="02")
st.markdown(
    """
Un run n'est marqué **OK** que si le mémo a passé ses deux post-conditions, qui
sont vérifiées avant écriture :

- **Aucun chiffre non déclaré** — chaque nombre du markdown a été émis par le
  compositeur ou provient d'une donnée citée. Un « environ 40 % » tapé à la main
  fait échouer le run.
- **Vocabulaire d'entonnoir confiné** — inscription, conversion, abonnement
  payant n'apparaissent que dans la section dont le rôle est de dire que ces
  choses sont invisibles depuis l'extérieur d'une chaîne.

Un mémo qui échoue à l'une des deux n'est pas publié : il est enregistré comme
échec, avec le détail. C'est délibérément l'inverse du réflexe habituel — un
mémo légèrement faux qui part quand même coûte plus cher qu'un mémo qui manque,
parce que personne ne relit un chiffre qui a l'air normal.
"""
)

st.caption(
    "Historique lu depuis `automation_runs`. Le verdict est calculé dans "
    "`app/services/automation.py` — cette page n'en décide rien."
)
