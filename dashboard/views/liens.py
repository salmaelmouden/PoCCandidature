"""La porte d'entrée du funnel — ce que les descriptions publiques disent du CTA.

Les autres pages lisent ce qui fait circuler une vidéo. Celle-ci lit ce qui se
passe *après* : est-ce qu'une vidéo qui a marché propose seulement une porte
d'entrée, est-elle visible sans déplier la description, et porte-t-elle de quoi
attribuer une inscription.

La frontière est la même que partout ailleurs dans ce projet, et elle est plus
étroite ici qu'ailleurs : cette page mesure un **emplacement**, jamais une
conversion. Elle peut dire « aucune porte », jamais « personne n'est entré ».

Présentation uniquement : tout le calcul vit dans `app.skills.cta_analysis`, et
toute mise en forme dans `dashboard.cta_view`.
"""

from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from app.services.public_signals import (
    CatalogueFreshness,
    build_cta_report,
    get_catalogue_freshness,
)
from app.skills.cta_analysis import CtaReport
from dashboard import components
from dashboard.cta_view import (
    coverage_frame,
    domain_frame,
    fold_sentence,
    format_gap_sentence,
    headlines,
    missing_frame,
    state_stack,
    thin_note,
    tracking_frame,
    view_weight_sentence,
    wording_frame,
)
from dashboard.db import db_session
from dashboard.formatting import humanize_age
from dashboard.ui import active_tokens, chart, fmt_int, page_header, section, table_twin


@st.cache_data(ttl=120, show_spinner="Lecture des descriptions…")
def load() -> tuple[CtaReport | None, CatalogueFreshness]:
    """Même contrat que les autres pages publiques : un catalogue vide est ordinaire."""
    with db_session() as session:
        return build_cta_report(session), get_catalogue_freshness(session)


def _age(moment) -> str:
    if moment is None:
        return "—"
    return humanize_age((datetime.now(UTC) - moment.astimezone(UTC)).total_seconds())


report, fresh = load()
tokens = active_tokens()

chips = [(f"{fmt_int(fresh.videos)} vidéos", False), ("Sans classifieur", False)]
chips.append((f"Vérifié {_age(fresh.last_checked_at)}", True))

page_header(
    "La porte d'entrée du funnel",
    "Où se trouve le lien produit dans les descriptions publiques du catalogue, "
    "s'il existe — et ce qu'il permettrait de mesurer.",
    chips=tuple(chips),
)

st.markdown(
    components.banner(
        "<strong>Emplacement, jamais conversion.</strong> Cette page lit le texte "
        "public des descriptions&nbsp;: présence d'un lien, position, paramètres. "
        "Les clics, les inscriptions et le taux de conversion ne sont pas "
        "observables depuis l'extérieur d'une chaîne — ils ne sont ni utilisés, ni "
        "estimés ici. Analyse indépendante, sans affiliation.",
        icon="●",
        live=True,
    ),
    unsafe_allow_html=True,
)

if report is None:
    st.warning(
        "Catalogue vide — aucune vidéo n'a encore été ingérée.\n\n"
        "- En local : `make ingest-youtube`.\n"
        "- En production : c'est le service *refresher* qui alimente cette page "
        "(`docs/guides/deploy-railway.md` §3).\n\n"
        "Cette lecture n'a **pas** besoin du classifieur : dès l'ingestion faite, "
        "elle couvre tout le catalogue.",
        icon="⚠️",
    )
    st.stop()

cards = headlines(report)
for column, headline in zip(st.columns(len(cards)), cards, strict=True):
    with column:
        st.markdown(
            components.insight_card(headline.label, headline.value, note=headline.note),
            unsafe_allow_html=True,
        )

# ---- 00 · le lien existe-t-il ? ---------------------------------------------

section(
    "Le lien existe-t-il ?",
    index="00",
    note="Trois états exclusifs : lien visible, lien à déplier, aucun lien.",
)

gap = format_gap_sentence(report)
if gap:
    st.markdown(gap)

st.markdown(view_weight_sentence(report))

chart(
    state_stack(report.by_format, "Porte d'entrée par format", tokens),
    key="cta_format",
)
table_twin("Le détail par format", coverage_frame(report.by_format))

st.container(border=True).markdown(
    "**Ce que je testerais** — ajouter une ligne de lien en tête de description "
    "sur les vingt Shorts les plus vus, et comparer le trafic référent YouTube "
    "des quatre semaines suivantes à celui des quatre précédentes. Le coût est "
    "une ligne de texte par vidéo ; la mesure demande un accès aux données "
    "internes, pas une nouvelle vidéo."
)

# ---- 01 · est-il visible ? --------------------------------------------------

section("Est-il visible ?", index="01")
st.markdown(fold_sentence(report))

# ---- 02 · est-il attribuable ? ----------------------------------------------

section(
    "Est-il attribuable ?",
    index="02",
    note="La seule des trois questions qui porte sur l'instrumentation, pas sur l'éditorial.",
)
st.markdown(
    """
Un lien sans paramètre de campagne arrive dans l'analytics comme du trafic
référent indifférencié. La vidéo qui l'a produit n'est pas récupérable côté
produit : c'est exactement l'attribution qui manque pour relier une vidéo à une
inscription — l'entonnoir que cette page ne peut pas mesurer, et qu'une
convention de nommage suffirait à rendre mesurable.

La troisième ligne du tableau est une **incertitude assumée**, pas un constat :
une redirection peut ajouter un paramètre après le saut, et le texte du lien ne
permet pas de le savoir.
"""
)
st.dataframe(tracking_frame(report), width="stretch", hide_index=True)

st.container(border=True).markdown(
    "**Ce que je testerais** — une convention `utm_source=youtube&utm_content=<id "
    "de la vidéo>` sur les prochaines descriptions publiées. À partir de là, le "
    "classement des vidéos par inscriptions devient lisible, et la question qui "
    "commande tout le reste de ce projet — *le classement par vues est-il le même "
    "que par inscriptions ?* — se tranche sans nouvelle instrumentation."
)

# ---- 03 · la dérive dans le temps -------------------------------------------

section("Est-ce que ça bouge ?", index="03")
st.markdown(
    "Par année de publication. Une convention de description se met en place, se "
    "perd, ou ne s'est jamais appliquée à un format arrivé plus tard — les trois "
    "se lisent ici, et aucune ne se voit sur un agrégat du catalogue entier."
)
chart(
    state_stack(report.by_year, "Porte d'entrée par année de publication", tokens),
    key="cta_year",
)
table_twin("Le détail par année", coverage_frame(report.by_year))

note = thin_note(report.by_year)
if note:
    st.caption(note)

# ---- 04 · les vidéos à ouvrir en premier ------------------------------------

section(
    "Les vidéos à ouvrir en premier",
    index="04",
    note="Les plus vues du catalogue qui ne proposent aucun lien produit.",
)
st.markdown(
    "Classées par vues cumulées, pas par date : une vidéo ancienne qui tourne "
    "encore est une porte fermée tous les jours, et c'est une ligne de "
    "description. La liste est une **requête**, pas une sélection — elle se "
    "rejoue à chaque ingestion."
)
st.dataframe(
    missing_frame(report),
    width="stretch",
    hide_index=True,
    column_config={
        "Vues": st.column_config.NumberColumn(format="%d"),
        "Année": st.column_config.NumberColumn(format="%d"),
        "Lien": st.column_config.LinkColumn("Voir", display_text="YouTube"),
    },
)

# ---- 05 · comment le domaine produit est choisi -----------------------------

section("Comment le domaine produit est choisi", index="05")
st.markdown(
    f"""
Rien n'est codé en dur. Le domaine retenu est **le plus lié du catalogue hors
YouTube et hors réseaux sociaux** — ici `{report.coverage.primary_domain or "—"}`,
{report.coverage.primary_domain_reason}.

Les domaines écartés restent dans le tableau, avec la raison de leur exclusion :
une chaîne qui met son Instagram dans les {fmt_int(report.coverage.videos_total)}
descriptions se verrait sinon annoncer que son produit est Instagram. Un choix
d'hypothèse qu'on ne peut pas vérifier est une hypothèse cachée.

Seuls les liens que YouTube rend cliquables sont comptés — schéma `http(s)` ou
préfixe `www.`. Un `domaine.com` au fil d'une phrase est du texte, pas un lien,
et le compter gonflerait le nombre de portes.
"""
)
st.dataframe(domain_frame(report), width="stretch", hide_index=True)

wordings = wording_frame(report)
if not wordings.empty:
    st.caption("Les formulations d'appel à l'action réellement employées, l'URL remplacée par un repère.")
    st.dataframe(wordings, width="stretch", hide_index=True)

# ---- la limite --------------------------------------------------------------

section("Ce que je ne peux pas voir")
st.markdown(
    """
Tout ce qui précède décrit un **emplacement**. Rien ici ne dit combien de
personnes ont cliqué, ni combien se sont inscrites : le taux de clic sur une
description, le trafic référent et les inscriptions par vidéo ne sont visibles
que depuis l'intérieur.

> La question que ces données publiques posent sans pouvoir la trancher :
> **est-ce que les vidéos qui portent un lien convertissent mieux — ou est-ce
> qu'elles ont simplement été publiées à une période où la convention existait ?**
> Les deux produisent le même tableau vu de l'extérieur, et une journée d'accès
> au trafic référent les sépare.

La lecture reste utile sans cette réponse, parce que les trois constats
n'en dépendent pas : une vidéo sans lien ne convertit pas, un lien replié se voit
moins qu'un lien visible, et un lien sans paramètre n'est pas attribuable. Ce
sont des propriétés du dispositif, pas des hypothèses sur l'audience.
"""
)

st.caption(
    "Analyse indépendante, sans affiliation. API YouTube Data v3, lecture seule. "
    "Lecture recalculée à chaque ingestion ; aucun classifieur requis."
)
