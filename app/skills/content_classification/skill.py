"""Classify video titles into topic + hook_type, then persist idempotently."""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.repositories import VideoClassificationRepository, VideoRepository
from app.skills.content_classification.classifier import (
    ClassificationError,
    Classifier,
    KeywordFallbackClassifier,
)
from app.skills.content_classification.schemas import (
    CLASSIFICATION_VERSION,
    ClassifyContentResult,
    VideoToClassify,
)

logger = logging.getLogger(__name__)


class ClassifyContentRequest(BaseModel):
    """Skill input."""

    dataset_label: str = "youtube_api"
    batch_size: int = Field(default=40, ge=1, le=100)
    limit: int | None = Field(default=None, ge=1)
    version: str = CLASSIFICATION_VERSION
    force: bool = False


def classify_channel_content(
    session: Session,
    classifier: Classifier,
    request: ClassifyContentRequest | None = None,
) -> ClassifyContentResult:
    """
    Classify not-yet-classified videos for a dataset label.

    Idempotent: videos already classified at this version are skipped unless
    `force` is set. A failed batch does not abort the run — the remaining
    batches still commit, and the failure count is reported.
    """
    request = request or ClassifyContentRequest()
    video_repo = VideoRepository(session)
    classification_repo = VideoClassificationRepository(session)

    videos = list(video_repo.list_by_dataset_label(request.dataset_label))
    already_done = (
        set() if request.force else classification_repo.classified_video_ids(request.version)
    )
    pending = [video for video in videos if video.id not in already_done]
    skipped = len(videos) - len(pending)
    if request.limit is not None:
        pending = pending[: request.limit]

    by_youtube_id = {video.youtube_video_id: video for video in pending}
    classified = 0
    failed = 0

    for start in range(0, len(pending), request.batch_size):
        chunk = pending[start : start + request.batch_size]
        payload = [
            VideoToClassify(youtube_video_id=video.youtube_video_id, title=video.title)
            for video in chunk
        ]
        try:
            results = classifier.classify_batch(payload)
        except ClassificationError as exc:
            failed += len(chunk)
            logger.error("classification_batch_failed size=%s error=%s", len(chunk), exc)
            continue

        for result in results:
            video = by_youtube_id.get(result.youtube_video_id)
            if video is None:
                continue
            classification_repo.upsert(
                video_id=video.id,
                topic=result.topic.value,
                hook_type=result.hook_type.value,
                version=request.version,
                classified_by=classifier.name,
            )
            classified += 1

        # Commit per batch so a later failure never discards earlier paid-for work.
        session.commit()
        logger.info(
            "classification_batch_done batch=%s classified=%s",
            start // request.batch_size + 1,
            len(results),
        )

    return ClassifyContentResult(
        requested=len(pending),
        classified=classified,
        skipped_already_done=skipped,
        failed=failed,
        model=classifier.name,
        version=request.version,
        used_fallback=isinstance(classifier, KeywordFallbackClassifier),
    )
