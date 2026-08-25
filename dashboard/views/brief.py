"""En bref — the three-minute reading of the public catalogue.

The landing page. Everything numeric on it is derived from the same live report
the full catalogue page reads, through `dashboard.brief`, so the summary cannot
drift from the argument it summarises after an ingest.

Presentation only: no aggregation, no threshold, no ranking decided here.
"""

from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from app.services.public_signals import (
    CatalogueFreshness,
    build_cta_report,
    build_public_signal_report,
    get_catalogue_freshness,
)
from app.skills.cta_analysis import CtaReport
from app.skills.public_signal_analysis import PublicSignalError, PublicSignalReport
from dashboard import components
from dashboard.brief import findings, headlines
from dashboard.catalogue_view import empty_state_message, humanize_age
from dashboard.cta_view import teaser_sentence
from dashboard.db import db_session
from dashboard.ui import fmt_int, page_header, section


@st.cache_data(ttl=120, show_spinner="Lecture du catalogue…")
def load() -> tuple[PublicSignalReport | None, CatalogueFreshness, CtaReport | None]:
    """Read the catalogue, tolerating one that has not been populated yet.

    Same contract as the catalogue page: an empty catalogue is an ordinary state
    on a fresh deploy, and this page is public and unauthenticated, so an
    unhandled `PublicSignalError` would render internal paths to anyone holding
    the link.

    The CTA report rides along in the same session rather than in a second cached
    loader: it reads the same rows, and two loaders would let the landing page
    show two different vintages of the same catalogue.
    """
    with db_session() as session:
        fresh = get_catalogue_freshness(session)
        cta = build_cta_report(session)
        try:
            return build_public_signal_report(session), fresh, cta
        except PublicSignalError:
            return None, fresh, cta


def _age(moment) -> str:
    if moment is None:
        return "—"
    return humanize_age((datetime.now(UTC) - moment.astimezone(UTC)).total_seconds())


report, fresh, cta = load()

chips = [(f"{fmt_int(fresh.videos)} vidéos", False)]
if report is not None:
    chips.append((f"{report.period_start:%Y} → {report.period_end:%Y}", False))
chips.append((f"Vérifié {_age(fresh.last_checked_at)}", True))

page_header(
    "Ce que dit le catalogue public",
    "Trois lectures d'un catalogue YouTube de mille vidéos, et ce qu'elles "
    "impliquent pour le calendrier éditorial. Analyse indépendante, données "
    "publiques uniquement.",
    chips=tuple(chips),
)

st.markdown(
    components.banner(
        "<strong>Analyse indépendante, sans affiliation.</strong> Données publiques "
        "via l'API YouTube Data v3 en lecture seule&nbsp;: titre, date, durée, vues, "
        "likes, commentaires. Les inscriptions, la conversion, la durée de visionnage "
        "et les sources de trafic ne sont pas observables depuis l'extérieur d'une "
        "chaîne — elles ne sont ni utilisées, ni estimées ici.",
        icon="●",
        live=True,
    ),
    unsafe_allow_html=True,
)

# ---- lectures ---------------------------------------------------------------

empty = empty_state_message(
    has_report=report is not None,
    videos=fresh.videos,
    classified=fresh.classified,
)

if empty is not None:
    # The reading is unavailable, but the method and the rest of the app are not:
    # a landing page that explains what it is beats one that only apologises.
    st.warning(empty, icon="⚠️")
else:
    # Built once: the count decides the column layout, so a second call would be
    # a second chance for the two to disagree.
    cards = headlines(report)
    for column, headline in zip(st.columns(len(cards)), cards, strict=True):
        with column:
            st.markdown(
                components.insight_card(
                    headline.label, headline.value, note=headline.note
                ),
                unsafe_allow_html=True,
            )

    for finding in findings(report):
        section(finding.title, index=finding.index)
        st.markdown(components.badge(finding.badge, finding.badge_kind), unsafe_allow_html=True)
        st.markdown(finding.body)
        with st.container(border=True):
            st.markdown(f"**Ce que je testerais** — {finding.action}")

    section("Le raisonnement complet")
    st.markdown(
        "Ces trois lectures sont la version courte. Le détail — cinq lectures, les "
        "graphiques par format, la couverture cohorte par cohorte et le tableau de "
        "données complet — vit sur la page suivante, et se recalcule à chaque "
        "ingestion."
    )
    st.page_link(
        "views/catalogue.py",
        label="Catalogue public — la lecture détaillée",
        icon=":material/public:",
    )

# ---- la porte d'entrée ------------------------------------------------------

# Deliberately outside the `else`: this reading needs no classifier, so it can
# still be shown on a catalogue that has been ingested but not yet labelled —
# the exact state in which the block above has nothing to say.
teaser = teaser_sentence(cta) if cta is not None else None
if teaser is not None:
    section("Et une lecture qui ne parle pas d'éditorial")
    st.markdown(
        f"""
Tout ce qui précède porte sur ce qui fait circuler une vidéo. La question
suivante porte sur ce qui se passe ensuite : une vidéo qui a marché propose-t-elle
seulement une porte d'entrée ?

{teaser}

C'est un constat d'**emplacement**, pas de conversion : la description est la
seule partie du chemin d'acquisition qu'une chaîne publie.
"""
    )
    st.page_link(
        "views/liens.py",
        label="La porte d'entrée — où se trouve le lien produit",
        icon=":material/link:",
    )

# ---- la limite --------------------------------------------------------------

section("Ce que je ne peux pas voir")
st.markdown(
    """
Tout ce qui précède provient de données publiques. Ce qui manque n'est pas un
détail : c'est la moitié de la question. Ni les inscriptions, ni la durée de
visionnage, ni le CTR, ni les sources de trafic. Le classement par portée est un
proxy, rien de plus.

> La première question que je voudrais trancher : **est-ce que le classement des
> vidéos par vues est le même que par inscriptions ?** Si les deux divergent, le
> calendrier éditorial optimise la mauvaise métrique — et les lectures ci-dessus
> changent d'ordre de priorité.

Une journée d'accès aux données internes y répond. Le pipeline qui la traite est
déjà écrit : ingestion, classification, normalisation par cohorte. Il ne lui
manque qu'une colonne.
"""
)

# ---- comment c'est construit ------------------------------------------------

section("Comment cette chaîne se protège d'elle-même")
st.markdown(
    """
Les skills calculent, les agents raisonnent, la base est la source de vérité. Le
partage n'est pas cosmétique : aucune moyenne, aucun test statistique, aucun
seuil ne passe par un modèle de langage. Le LLM ne fait qu'une chose ici —
attribuer un sujet et un type d'accroche à partir du **titre seul** — et ce qu'il
écrit est versionné en base.

La raison de cette discipline est arrivée en cours de route. Un arrondi dans le
générateur de données synthétiques tronquait l'étage terminal du funnel à zéro.
La chaîne en a déduit un goulot à 100 %, l'agent stratège en a tiré un
`[P0] Fix Premium leak` argumenté — audit du paywall, timing, CTA — et
l'automatisation l'expédiait chaque lundi. Une recommandation prioritaire,
confiante et entièrement fausse, née d'une troncature. La suite d'évaluation
était verte : elle n'avait jamais testé les agents sur une entrée dégénérée.

Le correctif n'a pas été de mieux formuler le prompt. Une skill déterministe
(`metric_validation`) qualifie désormais les métriques avant qu'un agent les
voie, et une post-condition — également déterministe — dégrade toute
recommandation P0/P1 visant un étage signalé. La correction ne dépend donc jamais
de l'obéissance du modèle, et elle est testable sans lui.
"""
)

# ---- le reste ---------------------------------------------------------------

section("Le reste de l'application")
st.markdown(
    "Deux pistes de données cohabitent ici et ne sont **jamais** additionnées. Le "
    "catalogue ci-dessus est réel et public. Les pages ci-dessous tournent sur un "
    "jeu **synthétique explicitement étiqueté** (`synthetic_v1`) : il existe parce "
    "qu'un funnel d'acquisition complet — inscriptions, activation, conversion "
    "payante, tests A/B — n'est observable d'aucune chaîne depuis l'extérieur. Ce "
    "ne sont pas des données d'entreprise réelles, et rien n'y est présenté comme "
    "tel."
)

left, right = st.columns(2)
with left:
    st.page_link(
        "views/overview.py",
        label="Synthèse du funnel — démonstration",
        icon=":material/space_dashboard:",
    )
with right:
    st.page_link(
        "views/orchestrator.py",
        label="Orchestrateur — les agents au travail",
        icon=":material/account_tree:",
    )

st.caption(
    "Analyse indépendante, sans affiliation. API YouTube Data v3, lecture seule. "
    "Le catalogue se rafraîchit tout seul ; les chiffres de cette page suivent."
)
