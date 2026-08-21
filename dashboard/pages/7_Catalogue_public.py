"""Public catalogue page — live reading of the ingested YouTube catalogue.

Presentation only: every number is derived from the report the service returns,
so the narrative cannot drift away from the data after a new ingest.
Chart/table helpers live in `dashboard.catalogue_view` (unit-testable).
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from app.services.public_signals import (
    CatalogueFreshness,
    build_public_signal_report,
    get_catalogue_freshness,
)
from app.skills.public_signal_analysis import PublicSignalReport
from dashboard.catalogue_view import (
    dumbbell,
    fr,
    label_of,
    paired_frame,
    pick,
    rank_of,
    scatter,
    table_frame,
)
from dashboard.db import db_session
from dashboard.ui import page_header

st.set_page_config(page_title="Catalogue public · Growth Intelligence AI", layout="wide")


@st.cache_data(ttl=120, show_spinner="Lecture du catalogue…")
def load() -> tuple[PublicSignalReport, CatalogueFreshness]:
    with db_session() as session:
        return build_public_signal_report(session), get_catalogue_freshness(session)


# ---------------------------------------------------------------- page

page_header(
    "Catalogue public",
    "Lecture en direct du catalogue YouTube ingéré — signaux publics uniquement.",
)

head_left, head_right = st.columns([4, 1])
with head_right:
    if st.button("Rafraîchir", width="stretch"):
        load.clear()
        st.rerun()

report, fresh = load()

if fresh.classified == 0:
    st.warning(
        "Aucune vidéo classée. Lance `make ingest-youtube` puis `make classify` "
        "pour alimenter cette page."
    )
    st.stop()

st.info(
    "**Analyse indépendante, sans affiliation.** Données publiques via l'API YouTube "
    "Data v3 en lecture seule : titre, date, durée, vues, likes, commentaires. "
    "Les inscriptions, la conversion, la durée de visionnage et les sources de trafic "
    "ne sont pas observables depuis l'extérieur d'une chaîne — elles ne sont ni "
    "utilisées, ni estimées ici.",
    icon="ℹ️",
)

# ---- freshness -------------------------------------------------------------

f1, f2, f3, f4 = st.columns(4)
f1.metric("Vidéos ingérées", f"{fresh.videos:,}".replace(",", " "))
f2.metric(
    "Classées",
    f"{fresh.classified:,}".replace(",", " "),
    delta=None if not fresh.unclassified else f"-{fresh.unclassified} en attente",
    delta_color="off",
)
f3.metric(
    "Dernier relevé",
    fresh.last_metric_date.isoformat() if fresh.last_metric_date else "—",
)
if fresh.last_ingest_at:
    age_hours = (
        datetime.now(timezone.utc) - fresh.last_ingest_at.astimezone(timezone.utc)
    ).total_seconds() / 3600
    age = f"il y a {age_hours:.0f} h" if age_hours >= 1 else "il y a moins d'1 h"
else:
    age = "—"
f4.metric("Dernière ingestion", age)

st.caption(
    "Cette page relit la base à chaque chargement (cache 2 min). La fraîcheur des "
    "chiffres dépend de la dernière ingestion : l'API publique YouTube renvoie des "
    "compteurs cumulés à l'instant de la collecte, sans historique."
)

st.divider()

# ---- 00 · framing ----------------------------------------------------------

short_fmt = pick(report.by_format, "short")
long_fmt = pick(report.by_format, "long")

st.subheader("00 · Ce catalogue est deux produits, pas un")

if short_fmt and long_fmt:
    ratio = (
        long_fmt.median_engagement_rate / short_fmt.median_engagement_rate
        if short_fmt.median_engagement_rate
        else 0
    )
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Shorts (≤ 60 s)", f"{short_fmt.share_of_catalogue * 100:.0f} %",
              f"{short_fmt.videos} vidéos", delta_color="off")
    k2.metric("Format long", f"{long_fmt.share_of_catalogue * 100:.0f} %",
              f"{long_fmt.videos} vidéos", delta_color="off")
    k3.metric("Engagement — Shorts", f"{fr(short_fmt.median_engagement_rate * 100)} %")
    k4.metric("Engagement — long", f"{fr(long_fmt.median_engagement_rate * 100)} %",
              f"{fr(ratio, 1)}× les Shorts", delta_color="off")

    st.markdown(
        f"""
Un spectateur de format long laisse une trace **{fr(ratio, 1)} fois plus souvent**
qu'un spectateur de Short. Cet écart est systématique et il contamine toute
statistique agrégée : un sujet majoritairement traité en long affichera un
engagement élevé par simple effet de composition, sans que le sujet y soit pour
quoi que ce soit.

C'est pourquoi tout ce qui suit est présenté **par format**.
"""
    )

st.divider()

# ---- 01 · narrative needs runway -------------------------------------------

topics = paired_frame(report.by_topic_short, report.by_topic_long)
hooks = paired_frame(report.by_hook_short, report.by_hook_long)

st.subheader("01 · Le récit a besoin de durée")

narrative_s = pick(report.by_topic_short, "portrait_histoire")
narrative_l = pick(report.by_topic_long, "portrait_histoire")
if narrative_s and narrative_l:
    rank_l = rank_of(report.by_topic_long, "portrait_histoire")
    rank_s = rank_of(report.by_topic_short, "portrait_histoire")
    st.markdown(
        f"""
Les vidéos construites comme un récit représentent
**{narrative_l.share_of_catalogue * 100:.1f} %** du format long. Leur performance
ne dépend pas du sujet mais du format dans lequel il est servi.

En format long elles atteignent **{fr(narrative_l.median_reach_index)}**
(rang {rank_l} sur {len(report.by_topic_long)}). En Short, les mêmes récits tombent
à **{fr(narrative_s.median_reach_index)}** (rang {rank_s} sur
{len(report.by_topic_short)}). Les deux échantillons sont larges —
{narrative_l.videos} vidéos longues, {narrative_s.videos} Shorts.
"""
    )

if not topics.empty:
    st.altair_chart(
        dumbbell(topics, "Indice de portée par sujet — Shorts contre format long"),
        width="stretch",
    )
    st.caption(
        "Trié par écart entre formats. Les sujets du haut gagnent à être traités en "
        "long, ceux du bas perdent. 1,00 = médiane de la cohorte (format × trimestre)."
    )

with st.expander("Ce que je testerais"):
    st.markdown(
        """
- **Pourquoi ça compte** — le récit est le registre qui exige le moins de compétence
  financière préalable : c'est le point d'entrée d'une audience qui ne s'estime pas
  encore concernée. Le servir en Short le prive de ce qui le rend efficace.
- **Test** — cesser de découper les récits en Shorts ; utiliser le Short comme amorce
  renvoyant vers la version longue.
- **Mesure** — indice de portée du récit long avant/après sur 8 semaines, à cohorte
  comparable. En interne : le taux d'inscription par vue, invisible d'ici.
"""
    )

st.divider()

# ---- 02 · format decides the hook ------------------------------------------

st.subheader("02 · Le format décide de l'accroche, pas l'inverse")

auth_s = pick(report.by_hook_short, "autorite")
auth_l = pick(report.by_hook_long, "autorite")
contra_s = pick(report.by_hook_short, "contrarian")
contra_l = pick(report.by_hook_long, "contrarian")
quest_s = pick(report.by_hook_short, "question")
quest_l = pick(report.by_hook_long, "question")
quest_all = pick(report.by_hook, "question")

if auth_s and auth_l and contra_s and contra_l and quest_s and quest_l and quest_all:
    st.markdown(
        f"""
Le constat précédent n'est pas propre au récit. En classant chaque titre par le
ressort qu'il emploie, le même renversement apparaît — plus net encore.

L'accroche **d'autorité** passe de {fr(auth_s.median_reach_index)} en Short à
**{fr(auth_l.median_reach_index)}** en long, rang
{rank_of(report.by_hook_long, "autorite")} du format. Le **contre-pied** fait
l'inverse : **{fr(contra_s.median_reach_index)}** en Short, où il domine, contre
{fr(contra_l.median_reach_index)} en long.

Le point le plus actionnable est ailleurs. L'accroche la plus utilisée est la
**question** : {quest_all.videos} vidéos, **{quest_all.share_of_catalogue * 100:.1f} %**
de la production. Elle obtient {fr(quest_s.median_reach_index)} en Short et
{fr(quest_l.median_reach_index)} en long — le seul ressort qui ne gagne dans aucun
des deux formats.
"""
    )

if not hooks.empty:
    st.altair_chart(
        dumbbell(hooks, "Indice de portée par accroche — Shorts contre format long"),
        width="stretch",
    )
    st.caption("Même lecture. L'ordre des accroches gagnantes s'inverse entre formats.")

with st.expander("Ce que je testerais"):
    st.markdown(
        """
- **Pourquoi ça compte** — décision éditoriale à coût nul : ni le sujet, ni le
  tournage, ni le montage ne changent. Seulement la formulation du titre selon le
  format de destination.
- **Test** — sur dix vidéos longues à venir, remplacer la question par une accroche
  d'autorité ou de promesse ; sur dix Shorts, privilégier le contre-pied.
- **Mesure** — indice de portée à cohorte constante, minimum 20 vidéos par bras.
  En interne : le CTR de la vignette isolerait l'effet du titre bien mieux.
"""
    )

st.divider()

# ---- 03 · biggest bet, least reach -----------------------------------------

st.subheader("03 · Le plus gros pari éditorial est le moins diffusé")

savings_l = pick(report.by_topic_long, "epargne_placements")
savings_all = pick(report.by_topic, "epargne_placements")
if savings_l and savings_all:
    st.markdown(
        f"""
L'épargne et les placements constituent le premier sujet du catalogue :
{savings_all.videos} vidéos, **{savings_all.share_of_catalogue * 100:.1f} %** de
l'ensemble. En format long la concentration est plus marquée encore —
{savings_l.videos} vidéos, **{savings_l.share_of_catalogue * 100:.0f} %** de tout le
format long.

C'est aussi le sujet qui circule le moins : **{fr(savings_l.median_reach_index)}**,
rang {rank_of(report.by_topic_long, "epargne_placements")} sur
{len(report.by_topic_long)}.

Le nuage ci-dessous situe chaque sujet sur les deux mesures. L'épargne n'y est pas
une anomalie : elle est **sur** la tendance. C'est ce qui rend le constat solide —
ce n'est pas la performance du sujet qui interroge, c'est le volume qui lui est
consacré.
"""
    )

st.altair_chart(
    scatter(report.by_topic_long, "Portée et engagement par sujet — format long"),
    width="stretch",
)
st.caption(
    "Taille du point = nombre de vidéos. Restreint au format long pour neutraliser "
    "l'effet de composition. Les sujets qui portent le plus loin engagent le moins."
)

with st.expander("Ce que je testerais"):
    st.markdown(
        """
- **Pourquoi ça compte** — un quart du format long est investi sur le sujet qui
  atteint le moins de monde. Si ce choix vise la qualification de l'audience plutôt
  que le volume, il est cohérent — mais il devrait alors se lire dans le taux
  d'inscription, pas dans la portée.
- **Test** — rien, avant d'avoir vérifié cette hypothèse en interne. Réduire le
  volume d'un sujet sur son seul indice de portée serait une erreur si c'est le
  sujet qui convertit.
- **Mesure** — inscriptions par vue et par sujet. C'est la donnée qui tranche, et
  c'est exactement celle que je ne vois pas.
"""
    )

st.divider()

# ---- 04 · reach and engagement disagree ------------------------------------

st.subheader("04 · Ce qui porte le plus loin engage le moins")

if report.by_hook_long:
    best_reach = report.by_hook_long[0]
    worst_reach = report.by_hook_long[-1]
    by_eng = sorted(report.by_hook_long, key=lambda r: r.median_engagement_rate)
    st.markdown(
        f"""
La portée dit qu'une vidéo a voyagé ; l'engagement dit qu'elle a touché. Sur les
accroches en format long, les deux se contredisent frontalement.

**{label_of(best_reach.value)}** obtient le meilleur indice de portée du format
(**{fr(best_reach.median_reach_index)}**) et le plus faible engagement
(**{fr(best_reach.median_engagement_rate * 100)} %**).
**{label_of(worst_reach.value)}** fait l'exact opposé : portée la plus basse
(**{fr(worst_reach.median_reach_index)}**), engagement le plus élevé
(**{fr(worst_reach.median_engagement_rate * 100)} %**).
{best_reach.videos} vidéos d'un côté, {worst_reach.videos} de l'autre.
"""
    )
    st.warning(
        "**Précision de méthode.** Cette contradiction n'apparaît proprement qu'à "
        "format constant. Calculée tous formats confondus, la comparaison des "
        "engagements par accroche mesure surtout la proportion de Shorts dans chaque "
        "catégorie. Les chiffres agrégés sont fournis plus bas pour transparence — "
        "ils ne veulent rien dire.",
        icon="⚠️",
    )

st.divider()

# ---- 05 · hypothesis --------------------------------------------------------

st.subheader("05 · Une hypothèse, pas un constat")

if report.by_topic_long:
    top = report.by_topic_long[0]
    top_all = pick(report.by_topic, top.value)
    if top.videos < 15 and top_all:
        st.markdown(
            f"""
Le sujet le plus performant du catalogue est **{label_of(top.value)}** :
{fr(top.median_reach_index)} en format long, premier rang. C'est aussi le moins
publié — {top_all.videos} vidéos, {top_all.share_of_catalogue * 100:.1f} % du corpus.

Je le présente comme une hypothèse et non comme un résultat, pour une raison
précise : l'échantillon est de **{top.videos} vidéos** en format long. Une médiane
sur si peu d'observations est instable, et deux vidéos exceptionnelles suffiraient
à produire ce chiffre. C'est le nombre le plus spectaculaire de cette analyse et le
moins fiable — les deux vont souvent ensemble.
"""
        )
    else:
        st.markdown(
            f"""
Le sujet le mieux classé en format long est **{label_of(top.value)}**
({fr(top.median_reach_index)}, {top.videos} vidéos). L'échantillon est désormais
suffisant pour le traiter comme un constat plutôt que comme une hypothèse.
"""
        )

st.divider()

# ---- what I cannot see ------------------------------------------------------

st.subheader("Ce que je ne peux pas voir")
st.markdown(
    """
Tout ce qui précède provient de données publiques. Ce qui manque n'est pas un
détail : c'est la moitié de la question. Ni les inscriptions, ni la durée de
visionnage, ni le CTR, ni les sources de trafic. Le classement par portée est un
proxy, rien de plus.

> La première question que je voudrais trancher : **est-ce que le classement des
> vidéos par vues est le même que par inscriptions ?** Si les deux divergent, le
> calendrier éditorial optimise la mauvaise métrique — et les cinq lectures
> ci-dessus changent d'ordre de priorité.

Une journée d'accès aux données internes y répond. Le pipeline qui la traite est
déjà écrit : ingestion, classification, normalisation par cohorte. Il ne lui manque
qu'une colonne.
"""
)

st.divider()

# ---- method & data ----------------------------------------------------------

with st.expander("Méthode et limites"):
    coverage = report.coverage
    st.markdown(
        f"""
**Pourquoi pas les vues brutes** — les vues médianes par année de publication
augmentent d'un ordre de grandeur entre 2021 et 2026. Une vidéo ancienne a eu des
années pour accumuler et reste derrière une vidéo récente : c'est la croissance de
la chaîne qui domine, pas l'ancienneté. Agréger des vues brutes par sujet
reviendrait à mesurer *quand* un sujet a été traité.

**Indice de portée** — `vues ÷ médiane(cohorte)`, cohorte = `format × trimestre`.
1,00 = typique pour sa cohorte.

**Engagement** — `(likes + commentaires) ÷ vues`. Peu sensible à la croissance de
la chaîne, très sensible au format : d'où la comparaison à format constant.

**Couverture** — **{coverage.videos_indexed} vidéos sur {coverage.videos_total}**
portent un indice ({100 * coverage.videos_indexed / max(coverage.videos_total, 1):.0f} %).
{coverage.videos_excluded} sont écartées : {coverage.excluded_reason}.
{coverage.cohorts_used} cohortes retenues, {coverage.cohorts_dropped} abandonnées.

**Médianes, pas moyennes** — la distribution des vues est très asymétrique.

**Seuils** — aucune valeur reposant sur moins de 5 vidéos n'est affichée ; celles
sous 10 sont signalées par un astérisque.

**Classement éditorial** — sujets et accroches attribués par modèle de langage à
partir du **titre seul**. Les descriptions sont exclues : elles contiennent
l'argumentaire produit et les liens de campagne, présents indépendamment du contenu.

**Un seul instantané** — l'API publique renvoie des compteurs cumulés sans
historique. Aucune évolution temporelle n'est calculable tant que l'ingestion n'a
pas tourné plusieurs semaines.
"""
    )

with st.expander("Données complètes"):
    st.caption("Les valeurs adossées à moins de 10 vidéos sont marquées d'un astérisque.")
    for title, rows, share in [
        ("Sujets — format long", report.by_topic_long, False),
        ("Sujets — Shorts", report.by_topic_short, False),
        ("Accroches — format long", report.by_hook_long, False),
        ("Accroches — Shorts", report.by_hook_short, False),
        ("Sujets — tous formats (engagement confondu)", report.by_topic, True),
        ("Accroches — tous formats (engagement confondu)", report.by_hook, True),
    ]:
        if rows:
            st.markdown(f"**{title}**")
            st.dataframe(table_frame(rows, share), width="stretch", hide_index=True)

st.caption(
    f"Corpus : {report.period_start:%Y-%m-%d} → {report.period_end:%Y-%m-%d}. "
    "Analyse indépendante, sans affiliation. API YouTube Data v3, lecture seule."
)
