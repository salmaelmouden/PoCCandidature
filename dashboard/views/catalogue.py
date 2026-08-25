"""Catalogue public — lecture en direct du catalogue YouTube ingéré.

Présentation uniquement : chaque nombre est dérivé du rapport que renvoie le
service, pour que le récit ne puisse pas dériver après une nouvelle ingestion.
Les aides graphiques vivent dans `dashboard.catalogue_view` (testables).
"""

from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from app.services.public_signals import (
    CatalogueFreshness,
    build_public_signal_report,
    get_catalogue_freshness,
)
from app.skills.public_signal_analysis import PublicSignalError, PublicSignalReport
from dashboard import components
from dashboard.catalogue_view import (
    dumbbell,
    empty_state_message,
    fr,
    humanize_age,
    label_of,
    paired_frame,
    pick,
    rank_of,
    scatter,
    table_frame,
)
from dashboard.db import db_session
from dashboard.ui import active_tokens, chart, fmt_int, page_header, section

tokens = active_tokens()


@st.cache_data(ttl=120, show_spinner="Lecture du catalogue…")
def load() -> tuple[PublicSignalReport | None, CatalogueFreshness]:
    """Read the catalogue, tolerating one that has not been populated yet.

    An empty catalogue is an ordinary state, not a fault: on a fresh deploy the
    refresher has not run its first cycle. `analyse_public_signals` is right to
    refuse to analyse nothing, so absorb that refusal here and return no report.

    This page is public and unauthenticated, so an unhandled PublicSignalError
    renders a stack trace — internal paths included — to anyone holding the link.
    """
    with db_session() as session:
        fresh = get_catalogue_freshness(session)
        try:
            return build_public_signal_report(session), fresh
        except PublicSignalError:
            return None, fresh


def _age(moment) -> str:
    if moment is None:
        return "—"
    return humanize_age(
        (datetime.now(UTC) - moment.astimezone(UTC)).total_seconds()
    )


report, fresh = load()

# The corpus span comes from the report, so it can only be shown once there is
# one. The header itself still renders on an empty catalogue — a page that says
# what it is beats a blank one.
chips = [(f"{fmt_int(fresh.videos)} vidéos", False)]
if report is not None:
    chips.append((f"{report.period_start:%Y} → {report.period_end:%Y}", False))
chips.append((f"Vérifié {_age(fresh.last_checked_at)}", True))

page_header(
    "Catalogue public",
    "Lecture en direct du catalogue YouTube ingéré — signaux publics uniquement, "
    "analyse indépendante et sans affiliation.",
    chips=tuple(chips),
)

# The button drops the 120-second read cache; it does not fetch from YouTube.
# Labelled "Rafraîchir" it read as broken, because the honest outcome of a click
# is usually an identical page: the catalogue only moves when the refresher
# service runs, and `last_checked_at` comes from `ingest_runs`, which this button
# never writes. So the label now says what it does, and the click is acknowledged
# — an action with no visible effect and no feedback is indistinguishable from a
# dead control.
head_left, head_right = st.columns([4, 1])
with head_right:
    if st.button(
        "Relire la base",
        width="stretch",
        icon=":material/refresh:",
        help=(
            "Vide le cache de lecture (2 minutes) et relit la base. Le catalogue "
            "lui-même est mis à jour par le service d'ingestion, pas par ce "
            "bouton : « Dernière vérification » ne bougera qu'après un cycle."
        ),
    ):
        st.session_state["gia_catalogue_reread"] = True
        load.clear()
        st.rerun()

# Set before the rerun and consumed after it, because `st.rerun` discards
# everything already drawn — a toast emitted next to the button would never show.
if st.session_state.pop("gia_catalogue_reread", False):
    st.toast("Base relue.", icon=":material/refresh:")

empty = empty_state_message(
    has_report=report is not None,
    videos=fresh.videos,
    classified=fresh.classified,
)
if empty is not None:
    st.warning(empty, icon="⚠️")
    st.stop()

st.markdown(
    components.banner(
        "<strong>Analyse indépendante, sans affiliation.</strong> Données publiques "
        "via l'API YouTube Data v3 en lecture seule&nbsp;: titre, date, durée, vues, "
        "likes, commentaires. Les inscriptions, la conversion, la durée de "
        "visionnage et les sources de trafic ne sont pas observables depuis "
        "l'extérieur d'une chaîne — elles ne sont ni utilisées, ni estimées ici.",
        icon="●",
        live=True,
    ),
    unsafe_allow_html=True,
)

# ---- fraîcheur -------------------------------------------------------------

f1, f2, f3, f4 = st.columns(4)
f1.metric("Vidéos ingérées", fmt_int(fresh.videos), border=True)
f2.metric(
    "Classées",
    fmt_int(fresh.classified),
    delta=None if not fresh.unclassified else f"{fresh.unclassified} en attente",
    delta_color="off",
    border=True,
)
f3.metric("Dernière vérification", _age(fresh.last_checked_at), border=True)
f4.metric("Dernier changement", _age(fresh.last_changed_at), border=True)

if fresh.last_checked_at is None:
    st.warning(
        "Aucun cycle de rafraîchissement enregistré — les chiffres datent de la "
        "dernière ingestion manuelle. Lance `make refresh-loop` (ou le service "
        "`refresher`) pour que la page se mette à jour toute seule.",
        icon="⚠️",
    )
elif fresh.last_run_ok is False:
    st.error(
        f"Le dernier cycle de rafraîchissement a échoué : {fresh.last_run_error}. "
        "Les chiffres affichés sont ceux du dernier cycle réussi.",
        icon="🚨",
    )

st.caption(
    f"Relevé du jour : {fresh.last_metric_date or '—'}. « Vérification » = dernier "
    "passage du rafraîchisseur ; « changement » = dernière fois que des compteurs "
    "ont réellement bougé. Les deux diffèrent parce qu'un passage qui ne trouve "
    "rien de neuf n'écrit rien. L'API publique YouTube renvoie des compteurs "
    "cumulés à l'instant de la collecte : la page ne peut pas être plus fraîche "
    "que le dernier passage."
)

# ---- 00 · cadrage ----------------------------------------------------------

short_fmt = pick(report.by_format, "short")
long_fmt = pick(report.by_format, "long")

section("Ce catalogue est deux produits, pas un", index="00")

if short_fmt and long_fmt:
    ratio = (
        long_fmt.median_engagement_rate / short_fmt.median_engagement_rate
        if short_fmt.median_engagement_rate
        else 0
    )
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(
        "Shorts (≤ 60 s)",
        f"{short_fmt.share_of_catalogue * 100:.0f} %",
        f"{short_fmt.videos} vidéos",
        delta_color="off",
        border=True,
    )
    k2.metric(
        "Format long",
        f"{long_fmt.share_of_catalogue * 100:.0f} %",
        f"{long_fmt.videos} vidéos",
        delta_color="off",
        border=True,
    )
    k3.metric(
        "Engagement — Shorts",
        f"{fr(short_fmt.median_engagement_rate * 100)} %",
        border=True,
    )
    k4.metric(
        "Engagement — long",
        f"{fr(long_fmt.median_engagement_rate * 100)} %",
        f"{fr(ratio, 1)}× les Shorts",
        delta_color="off",
        border=True,
    )

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

# ---- 01 · le récit a besoin de durée ---------------------------------------

topics = paired_frame(report.by_topic_short, report.by_topic_long)
hooks = paired_frame(report.by_hook_short, report.by_hook_long)

section("Le récit a besoin de durée", index="01")

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
    chart(
        dumbbell(topics, "Indice de portée par sujet — Shorts contre format long", tokens),
        key="cat_topics",
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

# ---- 02 · le format décide de l'accroche -----------------------------------

section("Le format décide de l'accroche, pas l'inverse", index="02")

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
    chart(
        dumbbell(hooks, "Indice de portée par accroche — Shorts contre format long", tokens),
        key="cat_hooks",
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

# ---- 03 · le plus gros pari éditorial --------------------------------------

section("Le plus gros pari éditorial est le moins diffusé", index="03")

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

chart(
    scatter(report.by_topic_long, "Portée et engagement par sujet — format long", tokens),
    key="cat_scatter",
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

# ---- 04 · portée et engagement se contredisent -----------------------------

section("Ce qui porte le plus loin engage le moins", index="04")

if report.by_hook_long:
    best_reach = report.by_hook_long[0]
    worst_reach = report.by_hook_long[-1]
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

# ---- 05 · une hypothèse ----------------------------------------------------

section("Une hypothèse, pas un constat", index="05")

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

# ---- ce que je ne peux pas voir --------------------------------------------

section("Ce que je ne peux pas voir")
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

# ---- méthode et données ----------------------------------------------------

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
    groups = [
        ("Sujets — format long", report.by_topic_long, False),
        ("Sujets — Shorts", report.by_topic_short, False),
        ("Accroches — format long", report.by_hook_long, False),
        ("Accroches — Shorts", report.by_hook_short, False),
        ("Sujets — tous formats (engagement confondu)", report.by_topic, True),
        ("Accroches — tous formats (engagement confondu)", report.by_hook, True),
    ]
    populated = [group for group in groups if group[1]]
    if populated:
        for tab, (title, rows, share) in zip(
            st.tabs([title for title, _, _ in populated]), populated, strict=True
        ):
            with tab:
                st.dataframe(table_frame(rows, share), width="stretch", hide_index=True)

st.caption(
    f"Corpus : {report.period_start:%Y-%m-%d} → {report.period_end:%Y-%m-%d}. "
    "Analyse indépendante, sans affiliation. API YouTube Data v3, lecture seule."
)
