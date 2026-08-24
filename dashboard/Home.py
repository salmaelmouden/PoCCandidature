"""Growth Intelligence AI — point d'entrée Streamlit.

Ce module ne rend rien lui-même : il déclare la navigation et exécute la page
choisie. Les pages vivent dans `dashboard/views/`, et non dans un dossier
`pages/` auto-découvert, parce que `st.navigation` permet de les regrouper, de
les nommer en français et de leur donner une icône — ce que le nom de fichier ne
permet pas.

Le thème est injecté ici, une fois, avant l'exécution de la page : c'est le même
run de script, donc toutes les pages en héritent.
"""

from __future__ import annotations

import streamlit as st

from dashboard.ui import inject_theme, sidebar_brand

st.set_page_config(
    page_title="Growth Intelligence AI",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()
sidebar_brand()

NAVIGATION = {
    "Analyse": [
        st.Page(
            "views/overview.py",
            title="Synthèse",
            icon=":material/space_dashboard:",
            default=True,
        ),
        st.Page("views/acquisition.py", title="Acquisition", icon=":material/hub:"),
        st.Page("views/content.py", title="Contenu", icon=":material/movie:"),
        st.Page("views/funnel.py", title="Entonnoir", icon=":material/filter_alt:"),
    ],
    "Agents": [
        st.Page("views/orchestrator.py", title="Orchestrateur", icon=":material/account_tree:"),
        st.Page("views/analyst.py", title="Analyste", icon=":material/query_stats:"),
        st.Page("views/experiments.py", title="Expérimentations", icon=":material/science:"),
    ],
    "Signal public": [
        st.Page("views/catalogue.py", title="Catalogue public", icon=":material/public:"),
    ],
}

st.navigation(NAVIGATION).run()
