"""Tests for content_classification — no API key required."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.db.models import Video
from app.db.repositories import VideoClassificationRepository
from app.skills.content_classification import (
    ClassificationError,
    ClassifyContentRequest,
    ContentTopic,
    HookType,
    KeywordFallbackClassifier,
    VideoClassificationResult,
    VideoToClassify,
    build_classifier,
    classify_channel_content,
)
from app.skills.content_classification.classifier import ClaudeClassifier


def _make_video(session: Session, video_id: str, title: str, label: str = "youtube_api") -> Video:
    video = Video(
        youtube_video_id=video_id,
        title=title,
        description="",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        duration_seconds=600,
        channel_id="UC_test",
        channel_title="Test",
        topic="Personal Finance",
        is_synthetic=False,
        dataset_label=label,
    )
    session.add(video)
    session.flush()
    return video


class StubClassifier:
    """Deterministic stub standing in for Claude."""

    name = "stub-model"

    def __init__(self, *, fail: bool = False, extra_id: str | None = None) -> None:
        self.fail = fail
        self.extra_id = extra_id
        self.calls: list[list[VideoToClassify]] = []

    def classify_batch(self, videos: list[VideoToClassify]) -> list[VideoClassificationResult]:
        self.calls.append(videos)
        if self.fail:
            raise ClassificationError("boom")
        results = [
            VideoClassificationResult(
                youtube_video_id=video.youtube_video_id,
                topic=ContentTopic.CRYPTO,
                hook_type=HookType.QUESTION,
            )
            for video in videos
        ]
        if self.extra_id:
            results.append(
                VideoClassificationResult(
                    youtube_video_id=self.extra_id,
                    topic=ContentTopic.IMMOBILIER,
                    hook_type=HookType.RECIT,
                )
            )
        return results


def test_classifies_and_persists(session: Session) -> None:
    _make_video(session, "v1", "Faut-il acheter du Bitcoin ?")
    _make_video(session, "v2", "Investir 10 000 euros")

    result = classify_channel_content(session, StubClassifier())

    assert result.requested == 2
    assert result.classified == 2
    assert result.failed == 0
    assert result.used_fallback is False
    rows = VideoClassificationRepository(session).list_by_version(result.version)
    assert {row.topic for row in rows} == {ContentTopic.CRYPTO.value}
    assert {row.classified_by for row in rows} == {"stub-model"}


def test_is_idempotent(session: Session) -> None:
    _make_video(session, "v1", "Titre")
    classify_channel_content(session, StubClassifier())

    second = classify_channel_content(session, StubClassifier())

    assert second.requested == 0
    assert second.skipped_already_done == 1
    assert len(VideoClassificationRepository(session).list_by_version(second.version)) == 1


def test_force_reclassifies(session: Session) -> None:
    _make_video(session, "v1", "Titre")
    classify_channel_content(session, StubClassifier())

    forced = classify_channel_content(
        session, StubClassifier(), ClassifyContentRequest(force=True)
    )

    assert forced.requested == 1
    assert forced.classified == 1


def test_ignores_other_dataset_labels(session: Session) -> None:
    _make_video(session, "v1", "Réel", label="youtube_api")
    _make_video(session, "v2", "Synthétique", label="synthetic_v1")

    result = classify_channel_content(session, StubClassifier())

    assert result.requested == 1


def test_batches_respect_batch_size(session: Session) -> None:
    for index in range(5):
        _make_video(session, f"v{index}", f"Titre {index}")
    stub = StubClassifier()

    classify_channel_content(session, stub, ClassifyContentRequest(batch_size=2))

    assert [len(call) for call in stub.calls] == [2, 2, 1]


def test_failed_batch_is_reported_not_raised(session: Session) -> None:
    _make_video(session, "v1", "Titre")

    result = classify_channel_content(session, StubClassifier(fail=True))

    assert result.failed == 1
    assert result.classified == 0


def test_unknown_ids_from_model_are_dropped(session: Session) -> None:
    _make_video(session, "v1", "Titre")

    result = classify_channel_content(session, StubClassifier(extra_id="hallucinated"))

    assert result.classified == 1
    rows = VideoClassificationRepository(session).list_by_version(result.version)
    assert len(rows) == 1


def test_claude_reconcile_drops_unknown_and_duplicate_ids() -> None:
    videos = [VideoToClassify(youtube_video_id="v1", title="t")]
    results = [
        VideoClassificationResult(
            youtube_video_id="v1", topic=ContentTopic.CRYPTO, hook_type=HookType.QUESTION
        ),
        VideoClassificationResult(
            youtube_video_id="v1", topic=ContentTopic.IMMOBILIER, hook_type=HookType.RECIT
        ),
        VideoClassificationResult(
            youtube_video_id="ghost", topic=ContentTopic.CRYPTO, hook_type=HookType.CHIFFRE
        ),
    ]

    kept = ClaudeClassifier._reconcile(videos, results)

    assert [row.youtube_video_id for row in kept] == ["v1"]
    assert kept[0].topic is ContentTopic.CRYPTO


def test_fallback_used_without_api_key() -> None:
    classifier = build_classifier(None)

    assert isinstance(classifier, KeywordFallbackClassifier)


def test_fallback_is_deterministic() -> None:
    classifier = KeywordFallbackClassifier()
    videos = [VideoToClassify(youtube_video_id="v1", title="Faut-il acheter du Bitcoin ?")]

    first = classifier.classify_batch(videos)
    second = classifier.classify_batch(videos)

    assert first == second
    assert first[0].topic is ContentTopic.CRYPTO
    assert first[0].hook_type is HookType.QUESTION


def test_fallback_result_marks_backend(session: Session) -> None:
    _make_video(session, "v1", "Titre sans mot-clé")

    result = classify_channel_content(session, KeywordFallbackClassifier())

    assert result.used_fallback is True
    rows = VideoClassificationRepository(session).list_by_version(result.version)
    assert rows[0].classified_by == "keyword_fallback"


def test_claude_classifier_requires_key() -> None:
    with pytest.raises(ValueError):
        ClaudeClassifier("")
