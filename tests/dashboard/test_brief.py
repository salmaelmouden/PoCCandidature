"""Tests for the executive reading — pure, no Streamlit runtime."""

from __future__ import annotations

from datetime import UTC, datetime

from app.skills.public_signal_analysis import (
    CohortCoverage,
    DimensionStat,
    PublicSignalReport,
)
from dashboard.brief import findings, headlines
from dashboard.formatting import NBSP


def stat(
    value: str,
    *,
    videos: int = 20,
    reach: float = 1.0,
    engagement: float = 0.02,
    share: float = 0.1,
) -> DimensionStat:
    return DimensionStat(
        value=value,
        videos=videos,
        median_reach_index=reach,
        median_engagement_rate=engagement,
        total_views=1000,
        share_of_catalogue=share,
    )


def report(**overrides) -> PublicSignalReport:
    """A report carrying every value the findings look up, unless overridden."""
    base = {
        "period_start": datetime(2021, 1, 1, tzinfo=UTC),
        "period_end": datetime(2026, 8, 1, tzinfo=UTC),
        "coverage": CohortCoverage(
            videos_total=952,
            videos_indexed=926,
            videos_excluded=26,
            cohorts_used=30,
            cohorts_dropped=4,
        ),
        "by_format": [
            stat("short", videos=495, engagement=0.010, share=0.52),
            stat("long", videos=457, engagement=0.033, share=0.48),
        ],
        "by_topic": [
            stat("epargne_placements", videos=180, reach=0.82, share=0.19),
            stat("portrait_histoire", videos=90, reach=1.20, share=0.09),
        ],
        "by_hook": [
            stat("question", videos=300, reach=0.95, share=0.315),
            stat("autorite", videos=120, reach=1.10, share=0.13),
        ],
        "by_topic_short": [
            stat("portrait_histoire", videos=40, reach=0.70, share=0.08),
            stat("epargne_placements", videos=60, reach=0.90, share=0.12),
        ],
        "by_topic_long": [
            stat("portrait_histoire", videos=50, reach=1.45, share=0.11),
            stat("epargne_placements", videos=120, reach=0.78, share=0.26),
        ],
        "by_hook_short": [
            stat("contrarian", videos=30, reach=1.30, share=0.06),
            stat("question", videos=150, reach=0.92, share=0.30),
            stat("autorite", videos=40, reach=0.75, share=0.08),
        ],
        "by_hook_long": [
            stat("autorite", videos=80, reach=1.38, share=0.17),
            stat("question", videos=150, reach=0.88, share=0.33),
            stat("contrarian", videos=25, reach=0.81, share=0.05),
        ],
    }
    return PublicSignalReport(**{**base, **overrides})


# ---- headlines --------------------------------------------------------------


def test_headlines_derive_coverage_from_the_report() -> None:
    coverage, shorts, engagement = headlines(report())

    assert "926" in coverage.value
    # Indexed share is stated so the reader can weigh everything after it.
    assert "97" in coverage.note and "26" in coverage.note
    # The non-breaking space before % is French typography, not decoration:
    # a percentage that wraps onto the next line is a rendering bug.
    assert shorts.value == f"52{NBSP}%"
    # 3.3 % against 1.0 % — the ratio is derived, never asserted.
    assert engagement.value == "3,3× les Shorts"


def test_engagement_ratio_is_omitted_rather_than_divided_by_zero() -> None:
    """A format with no engagement is possible on a thin catalogue; a crash is not."""
    silent = report(
        by_format=[
            stat("short", engagement=0.0, share=0.52),
            stat("long", engagement=0.03, share=0.48),
        ]
    )
    labels = [headline.label for headline in headlines(silent)]

    assert "Engagement — format long" not in labels
    assert "Part de Shorts" in labels


def test_headlines_survive_a_report_with_no_format_split() -> None:
    assert len(headlines(report(by_format=[]))) == 1


# ---- findings ---------------------------------------------------------------


def test_all_three_findings_are_built_when_the_report_is_complete() -> None:
    built = findings(report())

    assert [finding.index for finding in built] == ["01", "02", "03"]
    assert [finding.title for finding in built] == [
        "Le format décide de l'accroche, pas l'inverse",
        "Le récit a besoin de durée",
        "Le plus gros pari éditorial est le moins diffusé",
    ]


def test_numbers_come_from_the_report() -> None:
    hook, narrative, volume = findings(report())

    assert "1,38" in hook.body  # autorité, format long
    assert "1,30" in hook.body  # contre-pied, Short
    assert f"31,5{NBSP}%" in hook.body  # share of production using the question hook
    assert "1,45" in narrative.body and "0,70" in narrative.body
    assert f"26{NBSP}%" in volume.body  # share of the long format


def test_ranks_are_read_from_the_list_that_holds_the_value() -> None:
    hook, narrative, _ = findings(report())

    # autorité leads by_hook_long, portrait_histoire leads by_topic_long.
    assert "rang 1 sur 3" in hook.body
    assert "rang 1 sur 2" in narrative.body


def test_a_finding_whose_inputs_are_missing_is_dropped_not_half_rendered() -> None:
    """The classifier vocabulary is versioned; a lookup here is allowed to fail."""
    without_hooks = report(by_hook_short=[], by_hook_long=[], by_hook=[])
    built = findings(without_hooks)

    assert len(built) == 2
    assert all("accroche" not in finding.title for finding in built)


def test_indices_are_assigned_after_the_drops() -> None:
    """A missing finding leaves 01/02 — never a gap at 02.

    Only the narrative topic is withdrawn here; the volume finding reads other
    rows of the same lists and must keep its place in the sequence.
    """
    built = findings(
        report(
            by_topic_short=[stat("epargne_placements", videos=60, reach=0.90, share=0.12)],
            by_topic_long=[stat("epargne_placements", videos=120, reach=0.78, share=0.26)],
        )
    )

    assert [finding.index for finding in built] == ["01", "02"]
    assert built[1].title == "Le plus gros pari éditorial est le moins diffusé"


def test_no_finding_renders_a_placeholder() -> None:
    for finding in findings(report()):
        assert "None" not in finding.body
        assert "None" not in finding.action
        assert finding.body.strip() and finding.action.strip()


def test_the_unanswerable_finding_is_marked_as_such() -> None:
    """Two conclusions and one open question must not read alike.

    The volume finding cannot be settled without signup data. Presenting it with
    the same confidence as the two measured findings is the failure the long
    form spends a whole section avoiding.
    """
    hook, narrative, volume = findings(report())

    assert hook.badge_kind == "fact"
    assert narrative.badge_kind == "fact"
    assert volume.badge_kind == "warning"
    assert "en interne" in volume.action


def test_findings_never_claim_a_signup_number() -> None:
    """`AGENTS.md` hard stop: signups are never inferred from public signals."""
    for finding in findings(report()):
        text = f"{finding.body} {finding.action}"
        # Mentioning the metric as the thing that is *missing* is the point;
        # asserting a value for it would be the violation.
        for sentence in text.split("."):
            if "inscription" in sentence:
                assert any(
                    marker in sentence
                    for marker in ("pas", "ne vois", "interne", "devrait")
                ), sentence
