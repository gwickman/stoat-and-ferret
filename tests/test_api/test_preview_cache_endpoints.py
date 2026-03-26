"""Tests for preview cache API endpoints."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.proxy_repository import InMemoryProxyRepository
from stoat_ferret.db.timeline_repository import AsyncInMemoryTimelineRepository
from stoat_ferret.db.version_repository import AsyncInMemoryVersionRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue
from stoat_ferret.preview.cache import CacheStatus, PreviewCache

pytestmark = pytest.mark.api


def _make_mock_preview_cache() -> MagicMock:
    """Create a mock PreviewCache with async methods."""
    cache = MagicMock(spec=PreviewCache)
    cache.status = AsyncMock()
    cache.clear_all = AsyncMock()
    return cache


@pytest.fixture
def mock_preview_cache() -> MagicMock:
    """Create a mock preview cache."""
    return _make_mock_preview_cache()


@pytest.fixture
def cache_app(mock_preview_cache: MagicMock) -> FastAPI:
    """Create test app with preview cache injected."""
    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        timeline_repository=AsyncInMemoryTimelineRepository(),
        version_repository=AsyncInMemoryVersionRepository(),
        batch_repository=None,
        proxy_repository=InMemoryProxyRepository(),
        job_queue=InMemoryJobQueue(),
        preview_cache=mock_preview_cache,
    )
    return app


@pytest.fixture
def client(cache_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create test client for cache API requests."""
    with TestClient(cache_app) as c:
        yield c


# ---------- GET /api/v1/preview/cache ----------


class TestGetCacheStatus:
    """Tests for GET /api/v1/preview/cache."""

    async def test_returns_cache_metrics(
        self,
        client: TestClient,
        mock_preview_cache: MagicMock,
    ) -> None:
        """GET returns all five cache status fields."""
        mock_preview_cache.status.return_value = CacheStatus(
            used_bytes=1024,
            max_bytes=1048576,
            usage_percent=0.10,
            active_sessions=["session-a", "session-b"],
        )

        response = client.get("/api/v1/preview/cache")
        assert response.status_code == 200
        data = response.json()
        assert data["active_sessions"] == 2
        assert data["used_bytes"] == 1024
        assert data["max_bytes"] == 1048576
        assert data["usage_percent"] == 0.10
        assert data["sessions"] == ["session-a", "session-b"]

    async def test_empty_cache_returns_zeros(
        self,
        client: TestClient,
        mock_preview_cache: MagicMock,
    ) -> None:
        """GET on empty cache returns zero values."""
        mock_preview_cache.status.return_value = CacheStatus(
            used_bytes=0,
            max_bytes=1048576,
            usage_percent=0.0,
            active_sessions=[],
        )

        response = client.get("/api/v1/preview/cache")
        assert response.status_code == 200
        data = response.json()
        assert data["active_sessions"] == 0
        assert data["used_bytes"] == 0
        assert data["sessions"] == []

    async def test_cache_unavailable_returns_503(self) -> None:
        """GET without cache injected returns 503."""
        app = create_app(
            video_repository=AsyncInMemoryVideoRepository(),
            project_repository=AsyncInMemoryProjectRepository(),
            clip_repository=AsyncInMemoryClipRepository(),
            timeline_repository=AsyncInMemoryTimelineRepository(),
            version_repository=AsyncInMemoryVersionRepository(),
            batch_repository=None,
            proxy_repository=InMemoryProxyRepository(),
            job_queue=InMemoryJobQueue(),
        )
        with TestClient(app) as c:
            response = c.get("/api/v1/preview/cache")
        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["code"] == "SERVICE_UNAVAILABLE"


# ---------- DELETE /api/v1/preview/cache ----------


class TestClearCache:
    """Tests for DELETE /api/v1/preview/cache."""

    async def test_clears_cache_and_returns_counts(
        self,
        client: TestClient,
        mock_preview_cache: MagicMock,
    ) -> None:
        """DELETE clears cache and returns cleared_sessions and freed_bytes."""
        mock_preview_cache.clear_all.return_value = (3, 4096)

        response = client.delete("/api/v1/preview/cache")
        assert response.status_code == 200
        data = response.json()
        assert data["cleared_sessions"] == 3
        assert data["freed_bytes"] == 4096
        mock_preview_cache.clear_all.assert_called_once()

    async def test_empty_cache_clear_returns_zeros(
        self,
        client: TestClient,
        mock_preview_cache: MagicMock,
    ) -> None:
        """DELETE on empty cache returns zero counts."""
        mock_preview_cache.clear_all.return_value = (0, 0)

        response = client.delete("/api/v1/preview/cache")
        assert response.status_code == 200
        data = response.json()
        assert data["cleared_sessions"] == 0
        assert data["freed_bytes"] == 0

    async def test_cache_unavailable_returns_503(self) -> None:
        """DELETE without cache injected returns 503."""
        app = create_app(
            video_repository=AsyncInMemoryVideoRepository(),
            project_repository=AsyncInMemoryProjectRepository(),
            clip_repository=AsyncInMemoryClipRepository(),
            timeline_repository=AsyncInMemoryTimelineRepository(),
            version_repository=AsyncInMemoryVersionRepository(),
            batch_repository=None,
            proxy_repository=InMemoryProxyRepository(),
            job_queue=InMemoryJobQueue(),
        )
        with TestClient(app) as c:
            response = c.delete("/api/v1/preview/cache")
        assert response.status_code == 503


# ---------- Error response format parity ----------


class TestCacheErrorResponseFormat:
    """Verify cache error responses follow the same format as other endpoints."""

    async def test_503_error_has_code_and_message(self) -> None:
        """503 error includes code and message in detail."""
        app = create_app(
            video_repository=AsyncInMemoryVideoRepository(),
            project_repository=AsyncInMemoryProjectRepository(),
            clip_repository=AsyncInMemoryClipRepository(),
            timeline_repository=AsyncInMemoryTimelineRepository(),
            version_repository=AsyncInMemoryVersionRepository(),
            batch_repository=None,
            proxy_repository=InMemoryProxyRepository(),
            job_queue=InMemoryJobQueue(),
        )
        with TestClient(app) as c:
            response = c.get("/api/v1/preview/cache")
        detail = response.json()["detail"]
        assert "code" in detail
        assert "message" in detail
