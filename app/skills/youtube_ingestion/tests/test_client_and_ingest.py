"""Tests for YouTube client + ingest orchestration (mocked HTTP)."""

from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from app.db.models import Video, VideoDailyMetric
from app.db.repositories import VideoRepository
from app.skills.youtube_ingestion.client import YouTubeApiError, YouTubeClient
from app.skills.youtube_ingestion.schemas import YouTubeIngestRequest
from app.skills.youtube_ingestion.skill import ingest_youtube_channel
from sqlalchemy import select


def _json_response(payload: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code,
        headers={"content-type": "application/json"},
        content=json.dumps(payload).encode("utf-8"),
    )


class _FakeTransport(httpx.BaseTransport):
    def __init__(self, routes: dict[str, list[httpx.Response]]) -> None:
        self._routes = routes
        self.calls: list[str] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.startswith("/youtube/v3"):
            path = path[len("/youtube/v3") :]
        self.calls.append(path)
        queue = self._routes.get(path)
        if not queue:
            return httpx.Response(404, text=f"no mock for {path}")
        return queue.pop(0)


def test_client_lists_videos_and_retries() -> None:
    sleeps: list[float] = []
    transport = _FakeTransport(
        {
            "/channels": [
                httpx.Response(503, text="busy"),
                _json_response(
                    {
                        "items": [
                            {
                                "contentDetails": {
                                    "relatedPlaylists": {"uploads": "UUuploads"}
                                }
                            }
                        ]
                    }
                ),
            ],
            "/playlistItems": [
                _json_response(
                    {
                        "items": [
                            {"contentDetails": {"videoId": "vid1"}},
                            {"contentDetails": {"videoId": "vid2"}},
                        ]
                    }
                )
            ],
            "/videos": [
                _json_response(
                    {
                        "items": [
                            {
                                "id": "vid1",
                                "snippet": {
                                    "title": "Crypto 101",
                                    "description": "",
                                    "publishedAt": "2024-02-01T00:00:00Z",
                                    "channelId": "UCch",
                                    "channelTitle": "Ch",
                                },
                                "contentDetails": {"duration": "PT2M"},
                                "statistics": {"viewCount": "10"},
                            }
                        ]
                    }
                )
            ],
        }
    )
    with YouTubeClient(
        "test-key", transport=transport, max_retries=2, sleep=sleeps.append
    ) as client:
        assert client.get_uploads_playlist_id("UCch") == "UUuploads"
        ids = client.list_playlist_video_ids("UUuploads", max_pages=1)
        assert ids == ["vid1", "vid2"]
        videos = client.get_videos(["vid1"])
        assert videos[0]["id"] == "vid1"
    assert sleeps  # retry happened


def test_client_missing_channel() -> None:
    transport = _FakeTransport({"/channels": [_json_response({"items": []})]})
    with YouTubeClient("test-key", transport=transport, max_retries=0) as client:
        with pytest.raises(YouTubeApiError, match="Channel not found"):
            client.get_uploads_playlist_id("missing")


def test_ingest_youtube_channel_idempotent(session) -> None:
    transport = _FakeTransport(
        {
            "/channels": [
                _json_response(
                    {
                        "items": [
                            {
                                "contentDetails": {
                                    "relatedPlaylists": {"uploads": "UUuploads"}
                                }
                            }
                        ]
                    }
                )
            ],
            "/playlistItems": [
                _json_response({"items": [{"contentDetails": {"videoId": "vidA"}}]})
            ],
            "/videos": [
                _json_response(
                    {
                        "items": [
                            {
                                "id": "vidA",
                                "snippet": {
                                    "title": "Budget tips",
                                    "description": "budgeting basics",
                                    "publishedAt": "2024-03-01T10:00:00Z",
                                    "channelId": "UCch",
                                    "channelTitle": "Money Ch",
                                },
                                "contentDetails": {"duration": "PT5M"},
                                "statistics": {
                                    "viewCount": "100",
                                    "likeCount": "9",
                                    "commentCount": "2",
                                },
                            }
                        ]
                    }
                )
            ],
        }
    )
    # Second ingest needs fresh route queues
    transport2 = _FakeTransport(
        {
            "/channels": [
                _json_response(
                    {
                        "items": [
                            {
                                "contentDetails": {
                                    "relatedPlaylists": {"uploads": "UUuploads"}
                                }
                            }
                        ]
                    }
                )
            ],
            "/playlistItems": [
                _json_response({"items": [{"contentDetails": {"videoId": "vidA"}}]})
            ],
            "/videos": [
                _json_response(
                    {
                        "items": [
                            {
                                "id": "vidA",
                                "snippet": {
                                    "title": "Budget tips (updated)",
                                    "description": "budgeting basics",
                                    "publishedAt": "2024-03-01T10:00:00Z",
                                    "channelId": "UCch",
                                    "channelTitle": "Money Ch",
                                },
                                "contentDetails": {"duration": "PT5M"},
                                "statistics": {
                                    "viewCount": "150",
                                    "likeCount": "11",
                                    "commentCount": "3",
                                },
                            }
                        ]
                    }
                )
            ],
        }
    )

    request = YouTubeIngestRequest(
        channel_id="UCch", metric_date=date(2026, 8, 20), max_pages=1
    )
    with YouTubeClient("test-key", transport=transport, max_retries=0) as client:
        first = ingest_youtube_channel(session, client, request)
    session.commit()
    assert first.videos_upserted == 1
    assert first.metrics_upserted == 1

    with YouTubeClient("test-key", transport=transport2, max_retries=0) as client:
        second = ingest_youtube_channel(session, client, request)
    session.commit()
    assert second.videos_upserted == 1

    videos = session.scalars(select(Video)).all()
    metrics = session.scalars(select(VideoDailyMetric)).all()
    assert len(videos) == 1
    assert len(metrics) == 1
    assert videos[0].title == "Budget tips (updated)"
    assert videos[0].is_synthetic is False
    assert videos[0].dataset_label == "youtube_api"
    assert metrics[0].views == 150
    assert VideoRepository(session).get_by_youtube_id("vidA") is not None
