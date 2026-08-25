"""Tests for the title-rewrite join — pure, no Streamlit runtime.

The rewrites are prose, so what is worth asserting is not their wording but the
discipline around them: that a proposal can only ever be paired with the video
it was written for, that a citation of an earlier video reads a live number
rather than a remembered one, and that the page degrades to fewer cards instead
of to blank ones.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.services.public_signals import IndexedVideo, TitleEvidence
from app.skills.public_signal_analysis import DimensionStat, PublicVideoSignal
from dashboard.rewrites import REWRITES, gap_sentence, proposals, unwritten


def signal(
    video_id: str,
    *,
    title: str = "Un titre ?",
    hook: str = "question",
    topic: str = "epargne_placements",
    duration: int = 900,
    year: int = 2024,
) -> PublicVideoSignal:
    return PublicVideoSignal(
        youtube_video_id=video_id,
        title=title,
        published_at=datetime(year, 6, 1, tzinfo=UTC),
        duration_seconds=duration,
        views=50_000,
        likes=1_000,
        comments=100,
        topic=topic,
        hook_type=hook,
    )


def stat(value: str, *, videos: int = 20, reach: float = 1.0) -> DimensionStat:
    return DimensionStat(
        value=value,
        videos=videos,
        median_reach_index=reach,
        median_engagement_rate=0.02,
        total_views=1_000,
        share_of_catalogue=0.1,
    )


def evidence(
    *,
    candidates: list[IndexedVideo] | None = None,
    longs: list[IndexedVideo] | None = None,
    by_hook_long: list[DimensionStat] | None = None,
    by_hook_series: list[DimensionStat] | None = None,
) -> TitleEvidence:
    candidates = candidates if candidates is not None else []
    return TitleEvidence(
        by_hook_long=by_hook_long
        if by_hook_long is not None
        else [stat("autorite", reach=1.39), stat("question", videos=74, reach=0.93)],
        by_hook_series=by_hook_series
        if by_hook_series is not None
        else [stat("chiffre", videos=45, reach=0.93), stat("question", videos=14, reach=0.80)],
        series_videos=107,
        candidates=candidates,
        exemplars=[],
        longs=longs if longs is not None else list(candidates),
    )


# ---- the join ---------------------------------------------------------------


def test_proposal_is_paired_with_the_video_it_was_written_for():
    """Rewrites are keyed by id, so re-ranking cannot shuffle them onto the wrong video."""
    first, second = tuple(REWRITES)[:2]
    items = [
        IndexedVideo(signal=signal(second, title="Second"), reach_index=0.8),
        IndexedVideo(signal=signal(first, title="First"), reach_index=0.4),
    ]
    built = proposals(evidence(candidates=items))

    assert [p.youtube_video_id for p in built] == [second, first]
    assert built[0].proposal == REWRITES[second].proposal
    assert built[1].proposal == REWRITES[first].proposal


def test_candidate_without_a_written_rewrite_is_dropped_not_blanked():
    items = [
        IndexedVideo(signal=signal("unknown-id", title="Pas encore rédigé ?"), reach_index=0.5),
        IndexedVideo(signal=signal(next(iter(REWRITES))), reach_index=0.6),
    ]
    ev = evidence(candidates=items)

    assert len(proposals(ev)) == 1
    assert unwritten(ev) == ("Pas encore rédigé ?",)


def test_no_rewrite_invents_a_figure_without_marking_it_as_a_slot():
    """Bracketed slots are the contract: a bare euro amount would be fabricated."""
    for video_id, rewrite in REWRITES.items():
        if "€" in rewrite.proposal or "M€" in rewrite.proposal:
            has_slot = "[" in rewrite.proposal
            # The one exception is a figure already present in the original title,
            # which is quoted rather than invented.
            quoted = video_id == "SZEGxjm64Hw"
            assert has_slot or quoted, f"{video_id} carries an unmarked figure"


# ---- precedents -------------------------------------------------------------


def test_precedent_reads_a_live_index_and_computes_the_ratio():
    target = "bY2P4DLT9Yg"
    precedent_id = REWRITES[target].precedent_id
    assert precedent_id is not None

    candidate = IndexedVideo(signal=signal(target), reach_index=0.74)
    prior = IndexedVideo(
        signal=signal(precedent_id, title="Il investit son crédit étudiant en bourse"),
        reach_index=1.81,
    )
    built = proposals(evidence(candidates=[candidate], longs=[candidate, prior]))

    assert built[0].precedent is not None
    assert built[0].precedent.reach_index == pytest.approx(1.81)
    assert built[0].precedent.ratio == pytest.approx(1.81 / 0.74)


def test_precedent_is_dropped_when_the_cited_video_left_the_indexed_set():
    """Better no citation than one rendered from a number nothing still supports."""
    target = "bY2P4DLT9Yg"
    candidate = IndexedVideo(signal=signal(target), reach_index=0.74)
    built = proposals(evidence(candidates=[candidate], longs=[candidate]))

    assert built[0].precedent is None


# ---- the gap statement ------------------------------------------------------


def test_gap_sentence_reports_both_rankings_because_they_disagree():
    sentence = gap_sentence(evidence())

    assert sentence is not None
    assert "0,93" in sentence  # catalogue-wide question hook
    assert "0,80" in sentence  # the same hook inside the series
    assert "chiffre" in sentence.lower()  # the register that wins there instead


def test_gap_sentence_skips_a_thin_leader_for_a_well_supported_register():
    """An 8-video median leads the real series ranking; it must not drive the rule."""
    sentence = gap_sentence(
        evidence(
            by_hook_series=[
                stat("contrarian", videos=8, reach=1.00),
                stat("chiffre", videos=45, reach=0.93),
                stat("question", videos=14, reach=0.80),
            ]
        )
    )

    assert sentence is not None
    assert "chiffre" in sentence.lower()
    assert "contre-pied" not in sentence.lower()


def test_gap_sentence_is_dropped_when_the_hook_left_the_report():
    """A vocabulary change in the classifier must not render a sentence with a hole."""
    assert gap_sentence(evidence(by_hook_series=[stat("chiffre")])) is None
    assert gap_sentence(evidence(by_hook_long=[stat("autorite")])) is None
