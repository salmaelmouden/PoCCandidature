"""Dix titres — la seule page de ce projet qui propose du travail éditorial.

L'analyse dit qu'une accroche sous-performe. Ça ne se livre pas en réunion
éditoriale : ce qui se livre, ce sont des titres. Cette page fait le dernier
pas, et elle le fait sous contrainte — la sélection des vidéos est dérivée des
données, la réécriture est assumée comme un jugement, et les deux sont
distinguées à l'écran.

Présentation uniquement : la sélection vit dans le service, les réécritures dans
`dashboard.rewrites`.
"""

from __future__ import annotations

import streamlit as st

from app.services.public_signals import (
    MIN_LONG_SECONDS,
    SERIES_TITLE_MARKERS,
    TitleEvidence,
    build_title_evidence,
)
from dashboard import components
from dashboard.catalogue_view import table_frame
from dashboard.db import db_session
from dashboard.formatting import fr
from dashboard.rewrites import SLOT_NOTE, gap_sentence, proposals, unwritten
from dashboard.ui import page_header, section


@st.cache_data(ttl=120, show_spinner="Lecture du catalogue…")
def load() -> TitleEvidence | None:
    """Same contract as the other public pages: an empty catalogue is ordinary."""
    with db_session() as session:
        return build_title_evidence(session)


evidence = load()

page_header(
    "Dix titres que je réécrirais",
    "Une recommandation éditoriale tirée du catalogue public, livrée sous la "
    "forme où elle est utilisable : des titres, pas un graphique.",
    chips=(("Format long", False), ("Jugement éditorial", False), ("Sélection dérivée", True)),
)

st.markdown(
    components.banner(
        "<strong>Analyse indépendante, sans affiliation.</strong> Les vidéos citées "
        "sont publiques et les chiffres viennent de l'API YouTube Data v3 en lecture "
        "seule. Les réécritures sont des propositions&nbsp;: je n'ai accès ni au CTR, "
        "ni aux inscriptions, ni aux tests réels de la chaîne.",
        icon="●",
        live=True,
    ),
    unsafe_allow_html=True,
)

if evidence is None:
    st.warning(
        "Le catalogue n'est pas encore peuplé — cette page se remplit dès que "
        "l'ingestion et la classification ont tourné une première fois.",
        icon="⚠️",
    )
    st.stop()

# ---- 00 · l'écart -----------------------------------------------------------

section("L'écart que ces titres visent", index="00")

gap = gap_sentence(evidence)
if gap:
    st.markdown(gap)

st.markdown(
    f"""
Ces deux classements ne disent pas la même chose, et c'est la raison d'être de
cette page. À l'échelle du format long, l'accroche d'**autorité** domine. Dans la
série récurrente d'analyses de patrimoine — **{evidence.series_videos} vidéos**,
repérées par leurs propres conventions de titre — elle ne figure même pas au
tableau : trop peu d'épisodes l'emploient pour qu'une médiane soit rapportable.
Le registre qui y gagne parmi les catégories bien dotées est le **chiffre**.

Une règle de réécriture tirée du seul classement global serait donc appliquée à
contresens là où elle le serait le plus. Les propositions ci-dessous suivent le
registre qui gagne **dans le sous-format concerné** — ce qui explique que sept
d'entre elles visent le chiffre et trois l'autorité.
"""
)

left, right = st.columns(2)
with left:
    st.caption(f"Accroches — tout le format long ({len(evidence.longs)} vidéos)")
    st.dataframe(table_frame(evidence.by_hook_long, False), width="stretch", hide_index=True)
with right:
    st.caption(f"Accroches — série patrimoine ({evidence.series_videos} vidéos)")
    st.dataframe(table_frame(evidence.by_hook_series, False), width="stretch", hide_index=True)

st.caption(
    "Les valeurs adossées à moins de 10 vidéos sont marquées d'un astérisque — "
    "dans la colonne de droite, cela concerne la plupart des accroches minoritaires, "
    "et c'est pourquoi l'argument ne repose que sur les deux mieux dotées. "
    f"Série repérée par ses conventions de titre : {', '.join(f'« {m} »' for m in SERIES_TITLE_MARKERS)}."
)

# ---- 01 · les réécritures ---------------------------------------------------

cards = proposals(evidence)

section("Les dix", index="01", note=f"{len(cards)} propositions, indice de portée croissant")

st.markdown(
    f"""
**Comment ces dix vidéos ont été choisies** — pas par moi. La sélection est une
requête : format long d'au moins {MIN_LONG_SECONDS // 60} minutes, accroche
« question », indice de portée sous la médiane de sa propre cohorte, les pires
d'abord. Elle se rejoue à chaque ingestion : une vidéo qui remonte sort de la
liste, et sa réécriture disparaît avec elle.

**Ce que j'ai écrit, en revanche, est un jugement.** {SLOT_NOTE}
"""
)

for position, card in enumerate(cards, start=1):
    st.markdown(
        components.rewrite_card(
            original=card.original,
            proposal=card.proposal,
            meta=(
                f"{position:02d} · indice {fr(card.reach_index)} · "
                f"{card.published_year} · {card.topic_label}"
            ),
            register=f"→ {card.register_label}",
            url=card.url,
        ),
        unsafe_allow_html=True,
    )
    st.markdown(f"{card.rationale}")
    if card.precedent is not None:
        st.info(
            f"**Le catalogue a déjà fait le test.** [{card.precedent.title}]"
            f"({card.precedent.url}) obtient **{fr(card.precedent.reach_index)}** "
            f"contre **{fr(card.reach_index)}** ici, soit **{fr(card.precedent.ratio, 1)}×**. "
            f"{card.precedent.note} Deux vidéos ne sont pas un test — mais c'est "
            f"la comparaison la plus proche que les données publiques permettent.",
            icon="⚖️",
        )
    st.markdown("")

missing = unwritten(evidence)
if missing:
    st.caption(
        f"{len(missing)} vidéo(s) remontée(s) par la requête n'ont pas encore de "
        "réécriture rédigée : " + " · ".join(f"« {title} »" for title in missing)
    )

# ---- 02 · ce qui en ferait un test ------------------------------------------

section("Ce qui en ferait un test", index="02")
st.markdown(
    """
Rien de ce qui précède n'est démontré. L'indice de portée est un proxy : il
mesure si une vidéo a circulé, pas si son titre y est pour quelque chose. Le
sujet, la vignette, le moment de publication et la promotion bougent en même
temps que l'accroche, et rien ici ne les sépare.

Le protocole qui trancherait, et qu'il est réaliste de lancer :

- **Bras A / bras B** — sur les vingt prochaines vidéos longues de la série,
  alterner titre « question » et titre « chiffre », assignation décidée avant
  le tournage et pas après.
- **Métrique primaire** — le CTR de la vignette, pas les vues. C'est la seule
  mesure qui isole l'effet du titre ; les vues intègrent l'algorithme, l'heure de
  publication et l'audience existante.
- **Métrique de garde-fou** — la durée de visionnage. Un titre qui gagne du clic
  en perdant de la rétention est une perte nette, et c'est exactement le risque
  d'un titre plus affirmatif.
- **Taille** — vingt vidéos ne donneront pas un intervalle serré. C'est une
  première lecture, à confirmer sur un trimestre.

Un test A/B natif sur les titres existe déjà côté YouTube Studio. Il rend cette
page obsolète en six semaines, et c'est le but : une proposition éditoriale a
vocation à être réfutée par la mesure, pas à rester une opinion bien argumentée.
"""
)

section("Ce que je ne peux pas voir")
st.markdown(
    """
Le CTR par vignette, la durée de visionnage, les sources de trafic, les
inscriptions par vidéo. Aucune n'est observable depuis l'extérieur d'une chaîne,
et toutes les quatre changeraient l'ordre de ces dix propositions.

> Celle qui compte le plus : **est-ce que le classement des vidéos par vues est
> le même que par inscriptions ?** Si les deux divergent, réécrire pour la portée
> optimise la mauvaise métrique — et il faudrait réécrire pour autre chose.
"""
)

st.caption(
    "Analyse indépendante, sans affiliation. API YouTube Data v3, lecture seule. "
    "Sélection recalculée à chaque ingestion ; réécritures rédigées à la main."
)
