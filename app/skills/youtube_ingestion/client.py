"""YouTube Data API v3 HTTP client with timeouts and bounded retries."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeApiError(RuntimeError):
    """Raised when the YouTube API returns an error payload or HTTP failure."""


class YouTubeClient:
    """Thin client over YouTube Data API v3 (API key auth only)."""

    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        ca_bundle_path: str | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("YouTube API key is required")
        self._api_key = api_key
        self._max_retries = max(0, max_retries)
        self._sleep = sleep
        client_kwargs: dict[str, Any] = {
            "base_url": YOUTUBE_API_BASE,
            "timeout": timeout_seconds,
            "transport": transport,
        }
        # Behind a TLS-intercepting proxy the default certifi bundle lacks the
        # corporate root CA and every request dies with an SSL EOF. Ignored when
        # a transport is injected, since tests supply their own.
        if ca_bundle_path and transport is None:
            client_kwargs["verify"] = ca_bundle_path
        self._client = httpx.Client(**client_kwargs)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> YouTubeClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_uploads_playlist_id(self, channel_id: str) -> str:
        payload = self._get(
            "/channels",
            params={"part": "contentDetails", "id": channel_id},
        )
        items = payload.get("items") or []
        if not items:
            raise YouTubeApiError(f"Channel not found: {channel_id}")
        try:
            return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        except (KeyError, TypeError) as exc:
            raise YouTubeApiError("Channel response missing uploads playlist") from exc

    def list_playlist_video_ids(self, playlist_id: str, *, max_pages: int = 10) -> list[str]:
        video_ids: list[str] = []
        page_token: str | None = None
        pages = 0
        while pages < max_pages:
            params: dict[str, str | int] = {
                "part": "contentDetails",
                "playlistId": playlist_id,
                "maxResults": 50,
            }
            if page_token:
                params["pageToken"] = page_token
            payload = self._get("/playlistItems", params=params)
            for item in payload.get("items") or []:
                video_id = (item.get("contentDetails") or {}).get("videoId")
                if video_id:
                    video_ids.append(video_id)
            page_token = payload.get("nextPageToken")
            pages += 1
            if not page_token:
                break
        return video_ids

    def get_videos(self, video_ids: list[str]) -> list[dict[str, Any]]:
        if not video_ids:
            return []
        results: list[dict[str, Any]] = []
        # videos.list allows up to 50 ids per call
        for start in range(0, len(video_ids), 50):
            chunk = video_ids[start : start + 50]
            payload = self._get(
                "/videos",
                params={
                    "part": "snippet,contentDetails,statistics",
                    "id": ",".join(chunk),
                },
            )
            results.extend(payload.get("items") or [])
        return results

    def _get(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        query = {**params, "key": self._api_key}
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.get(path, params=query)
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise YouTubeApiError(
                        f"Retryable YouTube HTTP {response.status_code}: {response.text[:200]}"
                    )
                response.raise_for_status()
                payload = response.json()
                if "error" in payload:
                    raise YouTubeApiError(str(payload["error"]))
                return payload
            except (httpx.TimeoutException, httpx.TransportError, YouTubeApiError) as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    break
                backoff = 0.5 * (2**attempt)
                logger.warning(
                    "youtube_api_retry path=%s attempt=%s error=%s",
                    path,
                    attempt + 1,
                    exc,
                )
                self._sleep(backoff)
        assert last_error is not None
        raise YouTubeApiError(f"YouTube request failed for {path}: {last_error}") from last_error
