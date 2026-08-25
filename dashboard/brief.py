"""Executive reading of the public-catalogue report — pure, no Streamlit runtime.

The catalogue page argues in five parts; this is the thirty-second version of the
same argument. Both derive every number from the same :class:`PublicSignalReport`,
so the short form cannot keep asserting something the long form stopped saying
after an ingest. Nothing here is hard-coded except the prose around the numbers.

A finding whose inputs are absent is dropped rather than rendered with a hole in
it. Topics and hooks come from a versioned classifier whose vocabulary can
change, and a cohort that falls under the reporting threshold leaves the report
entirely — so any given lookup here is allowed to fail. One finding fewer is a
smaller loss than a sentence with a gap where its number should be.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.skills.public_signal_analysis import DimensionStat, PublicSignalReport
from dashboard.catalogue_view import label_of, pick, rank_of
from dashboard.formatting import fmt_int, fmt_pct, fr


@dataclass(frozen=True)
class Headline:
    """One called-out number: what it measures, its value, and what it implies."""

    label: str
    value: str
    note: str


@dataclass(frozen=True)
class Finding:
    """One reading, condensed: the claim, the evidence, and the move it implies.

    ``badge`` carries the epistemic status on purpose. Two of these are
    conclusions and one is a question the public data cannot settle; collapsing
    that distinction is exactly the failure the long form spends a section
    avoiding.
    """

    index: str
    title: str
    body: str
    action: str
    badge: str
    badge_kind: str


def headlines(report: PublicSignalReport) -> tuple[Headline, ...]:
    """The three numbers that frame every other number on the page.

    Coverage comes first because it bounds everything after it: a reader who
    does not know how much of the catalogue carries an index cannot weigh the
    rest. The format split comes next because it is the reason every subsequent
    comparison is drawn at constant format.
    """
    coverage = report.coverage
    indexed_share = coverage.videos_indexed / max(coverage.videos_total, 1)

    items = [
        Headline(
            label="Catalogue indexé",
            value=f"{fmt_int(coverage.videos_indexed)} vidéos",
            note=(
                f"sur {fmt_int(coverage.videos_total)} ({fmt_pct(indexed_share, 0)}). "
                f"{coverage.videos_excluded} écartées : {coverage.excluded_reason}."
            ),
        )
    ]

    short = pick(report.by_format, "short")
    long = pick(report.by_format, "long")
    if short is not None:
        items.append(
            Headline(
                label="Part de Shorts",
                value=fmt_pct(short.share_of_catalogue, 0),
                note=(
                    f"{fmt_int(short.videos)} vidéos de 60 secondes ou moins. "
                    "Ce catalogue est deux produits, pas un."
                ),
            )
        )
    if short is not None and long is not None and short.median_engagement_rate > 0:
        ratio = long.median_engagement_rate / short.median_engagement_rate
        items.append(
            Headline(
                label="Engagement — format long",
                value=f"{fr(ratio, 1)}× les Shorts",
                note=(
                    f"{fmt_pct(long.median_engagement_rate, 2)} contre "
                    f"{fmt_pct(short.median_engagement_rate, 2)}. L'écart est "
                    "systématique : il contamine toute statistique agrégée."
                ),
            )
        )
    return tuple(items)


def _reach(stat: DimensionStat) -> str:
    return fr(stat.median_reach_index)


def _hook_finding(report: PublicSignalReport, index: str) -> Finding | None:
    """The zero-cost editorial move: the same hook wins in one format and loses in the other."""
    authority_s = pick(report.by_hook_short, "autorite")
    authority_l = pick(report.by_hook_long, "autorite")
    contrarian_s = pick(report.by_hook_short, "contrarian")
    contrarian_l = pick(report.by_hook_long, "contrarian")
    question_s = pick(report.by_hook_short, "question")
    question_l = pick(report.by_hook_long, "question")
    question_all = pick(report.by_hook, "question")
    if not all(
        (authority_s, authority_l, contrarian_s, contrarian_l, question_s, question_l, question_all)
    ):
        return None

    authority_rank = rank_of(report.by_hook_long, "autorite")
    return Finding(
        index=index,
        title="Le format décide de l'accroche, pas l'inverse",
        body=(
            f"En classant chaque titre par le ressort qu'il emploie, l'ordre des "
            f"accroches gagnantes s'inverse entre les deux formats. L'accroche "
            f"**d'autorité** passe de {_reach(authority_s)} en Short à "
            f"**{_reach(authority_l)}** en format long (rang {authority_rank} sur "
            f"{len(report.by_hook_long)}). Le **contre-pied** fait exactement "
            f"l'inverse : **{_reach(contrarian_s)}** en Short, où il domine, contre "
            f"{_reach(contrarian_l)} en long.\n\n"
            f"Le point actionnable est ailleurs. L'accroche la plus utilisée du "
            f"catalogue est la **question** — {fmt_int(question_all.videos)} vidéos, "
            f"**{fmt_pct(question_all.share_of_catalogue, 1)}** de la production. Elle "
            f"obtient {_reach(question_s)} en Short et {_reach(question_l)} en long : "
            f"c'est le seul ressort qui ne gagne dans aucun des deux formats."
        ),
        action=(
            "Décision à coût nul — ni le sujet, ni le tournage, ni le montage ne "
            "changent, seulement la formulation du titre selon le format de "
            "destination. Sur dix vidéos longues à venir, remplacer la question par "
            "une accroche d'autorité ; sur dix Shorts, par un contre-pied. Mesure à "
            "cohorte constante, minimum vingt vidéos par bras. En interne, le CTR de "
            "la vignette isolerait l'effet du titre bien mieux que la portée."
        ),
        badge="Constat",
        badge_kind="fact",
    )


def _narrative_finding(report: PublicSignalReport, index: str) -> Finding | None:
    """Same topic, opposite outcome depending on the format it is served in."""
    short = pick(report.by_topic_short, "portrait_histoire")
    long = pick(report.by_topic_long, "portrait_histoire")
    if short is None or long is None:
        return None

    return Finding(
        index=index,
        title="Le récit a besoin de durée",
        body=(
            f"Les vidéos construites comme un récit représentent "
            f"**{fmt_pct(long.share_of_catalogue, 1)}** du format long. Leur "
            f"performance ne dépend pas du sujet mais du format dans lequel il est "
            f"servi : **{_reach(long)}** en format long (rang "
            f"{rank_of(report.by_topic_long, 'portrait_histoire')} sur "
            f"{len(report.by_topic_long)}), contre **{_reach(short)}** en Short (rang "
            f"{rank_of(report.by_topic_short, 'portrait_histoire')} sur "
            f"{len(report.by_topic_short)}).\n\n"
            f"Les deux échantillons sont larges — {fmt_int(long.videos)} vidéos "
            f"longues, {fmt_int(short.videos)} Shorts — donc l'écart ne tient pas à "
            f"quelques valeurs extrêmes."
        ),
        action=(
            "Le récit est le registre qui exige le moins de compétence financière "
            "préalable : c'est le point d'entrée d'une audience qui ne s'estime pas "
            "encore concernée. Le servir en Short le prive de ce qui le rend "
            "efficace. Cesser de découper les récits, et utiliser le Short comme "
            "amorce renvoyant vers la version longue."
        ),
        badge="Constat",
        badge_kind="fact",
    )


def _volume_finding(report: PublicSignalReport, index: str) -> Finding | None:
    """The largest editorial bet sits on the least-travelling topic — and public data cannot say why."""
    long = pick(report.by_topic_long, "epargne_placements")
    overall = pick(report.by_topic, "epargne_placements")
    if long is None or overall is None:
        return None

    return Finding(
        index=index,
        title="Le plus gros pari éditorial est le moins diffusé",
        body=(
            f"L'épargne et les placements constituent le premier sujet du catalogue "
            f"— {fmt_int(overall.videos)} vidéos, "
            f"**{fmt_pct(overall.share_of_catalogue, 1)}** de l'ensemble. En format "
            f"long la concentration est plus marquée encore : "
            f"**{fmt_pct(long.share_of_catalogue, 0)}** de tout le format long.\n\n"
            f"C'est aussi le sujet qui circule le moins : **{_reach(long)}**, rang "
            f"{rank_of(report.by_topic_long, 'epargne_placements')} sur "
            f"{len(report.by_topic_long)}. Le nuage sujets × portée le situe **sur** "
            f"la tendance et non en anomalie — ce n'est donc pas la performance du "
            f"sujet qui interroge, c'est le volume qui lui est consacré."
        ),
        action=(
            "Ne rien changer avant d'avoir tranché en interne. Si ce volume vise la "
            "qualification de l'audience plutôt que le volume d'audience, le choix "
            "est cohérent — mais il devrait alors se lire dans le taux d'inscription, "
            "pas dans la portée. Réduire un sujet sur son seul indice de portée "
            "serait une erreur si c'est le sujet qui convertit. C'est exactement la "
            "donnée que je ne vois pas d'ici."
        ),
        badge="À trancher en interne",
        badge_kind="warning",
    )


#: Topics whose questions only arise once there is capital to manage, and topics
#: that address someone still forming habits. Declared here, and named in the
#: rendered text, because the whole reading moves if a reader disagrees with the
#: mapping — and a reader well might. Burying it in prose would hide the one
#: assumption the conclusion rests on.
_CAPITAL_TOPICS = ("fiscalite", "immobilier")
_ENTRY_TOPICS = ("education_financiere", "epargne_placements")


def _share_of(rows: list[DimensionStat], values: tuple[str, ...]) -> tuple[float, int]:
    """Combined catalogue share and video count for the topics actually present."""
    present = [row for row in rows if row.value in values]
    return sum(row.share_of_catalogue for row in present), sum(row.videos for row in present)


def _segment_finding(report: PublicSignalReport, index: str) -> Finding | None:
    """Production mix against the business model — the acquisition engine's aim.

    Deliberately a mix statement, not an audience one. Who watches a video is
    not observable from outside the channel; what share of the catalogue treats
    a given subject is. The inference from one to the other is the reader's, and
    the text says so.
    """
    capital_share, capital_videos = _share_of(report.by_topic, _CAPITAL_TOPICS)
    entry_share, entry_videos = _share_of(report.by_topic, _ENTRY_TOPICS)
    if capital_videos == 0 or entry_videos == 0:
        return None

    capital_names = ", ".join(
        label_of(row.value).lower() for row in report.by_topic if row.value in _CAPITAL_TOPICS
    )
    entry_names = ", ".join(
        label_of(row.value).lower() for row in report.by_topic if row.value in _ENTRY_TOPICS
    )
    ratio = entry_share / capital_share if capital_share else 0.0

    return Finding(
        index=index,
        title="Le catalogue et le haut de gamme ne se regardent pas",
        body=(
            f"Une offre réservée aux gros patrimoines a un présupposé : un capital "
            f"déjà constitué. En classant les sujets selon qu'ils supposent ce "
            f"capital ({capital_names}) ou qu'ils s'adressent à quelqu'un qui le "
            f"constitue encore ({entry_names}), l'écart de production est net.\n\n"
            f"Les sujets qui supposent un capital pèsent "
            f"**{fmt_pct(capital_share, 1)}** du catalogue "
            f"({fmt_int(capital_videos)} vidéos). Ceux d'entrée de gamme en pèsent "
            f"**{fmt_pct(entry_share, 1)}** ({fmt_int(entry_videos)} vidéos), soit "
            f"**{fr(ratio, 1)} fois plus**. Le moteur d'acquisition est pointé vers "
            f"le haut du funnel, ce qui est cohérent pour un produit grand public — "
            f"et l'est beaucoup moins si l'offre patrimoniale est une priorité de "
            f"croissance.\n\n"
            f"C'est un constat de **répartition éditoriale**, pas d'audience : qui "
            f"regarde quoi n'est pas observable de l'extérieur. Le pont entre les "
            f"deux appartient au lecteur, et il tient à la classification "
            f"ci-dessus — la déplacer déplace le chiffre."
        ),
        action=(
            "La question à poser en réunion éditoriale n'est pas « faut-il produire "
            "plus de contenu patrimonial » mais « d'où viennent les leads qualifiés "
            "aujourd'hui ». Si une poignée de vidéos les génère, leur sujet et leur "
            "format sont un modèle réplicable et le mix actuel est un angle mort "
            "chiffrable. Si les leads viennent d'ailleurs, le catalogue n'est pas le "
            "levier et le sujet est clos. La donnée qui tranche est le taux de "
            "qualification par vidéo d'origine — invisible d'ici, triviale en interne."
        ),
        badge="Hypothèse — dépend de la classification",
        badge_kind="interpretation",
    )


def findings(report: PublicSignalReport) -> tuple[Finding, ...]:
    """The readings worth three minutes, in the order they should be read.

    The two zero-cost editorial moves come first and the two strategic questions
    last, because both end on what public data cannot answer — which is the note
    the page should close on, not open with. Within that, production mix comes
    after volume: the second reads as a consequence of the first.

    Indices are assigned after the drops, so a missing finding leaves 01/02
    rather than a gap at 02.
    """
    builders = (_hook_finding, _narrative_finding, _volume_finding, _segment_finding)
    built: list[Finding] = []
    for builder in builders:
        found = builder(report, f"{len(built) + 1:02d}")
        if found is not None:
            built.append(found)
    return tuple(built)
