"""Tests for proxy management API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.models import ProxyFile, ProxyQuality, ProxyStatus
from stoat_ferret.db.proxy_repository import InMemoryProxyRepository
from tests.factories import make_test_video

pytestmark = pytest.mark.api


def _make_ready_proxy(video_id: str, **kwargs: object) -> ProxyFile:
    """Create a ready proxy record for testing."""
    now = datetime.now(timezone.utc)
    defaults: dict[str, object] = {
        "id": ProxyFile.new_id(),
        "source_video_id": video_id,
        "quality": ProxyQuality.MEDIUM,
        "file_path": f"/proxies/{video_id}_medium.mp4",
        "file_size_bytes": 50_000,
        "status": ProxyStatus.READY,
        "source_checksum": "abc123",
        "generated_at": now,
        "last_accessed_at": now,
    }
    defaults.update(kwargs)
    return ProxyFile(**defaults)  # type: ignore[arg-type]


# ---------- POST /videos/{video_id}/proxy ----------


class TestGenerateProxy:
    """Tests for POST /videos/{video_id}/proxy."""

    async def test_returns_202_with_job_id(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
    ) -> None:
        """POST returns 202 Accepted with job_id in response body."""
        video = make_test_video()
        await video_repository.add(video)

        response = client.post(f"/api/v1/videos/{video.id}/proxy")
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert isinstance(data["job_id"], str)

    async def test_missing_video_returns_404(
        self,
        client: TestClient,
    ) -> None:
        """POST for non-existent video returns 404."""
        response = client.post("/api/v1/videos/nonexistent/proxy")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "NOT_FOUND"

    async def test_duplicate_returns_409(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
        proxy_repository: InMemoryProxyRepository,
    ) -> None:
        """POST for video with existing active proxy returns 409."""
        video = make_test_video()
        await video_repository.add(video)

        proxy = _make_ready_proxy(video.id)
        await proxy_repository.add(proxy)

        response = client.post(f"/api/v1/videos/{video.id}/proxy")
        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["code"] == "PROXY_ALREADY_EXISTS"


# ---------- GET /videos/{video_id}/proxy ----------


class TestGetProxyStatus:
    """Tests for GET /videos/{video_id}/proxy."""

    async def test_returns_proxy_status(
        self,
        client: TestClient,
        proxy_repository: InMemoryProxyRepository,
    ) -> None:
        """GET returns proxy status with required fields."""
        video_id = "test-video-id"
        proxy = _make_ready_proxy(video_id)
        await proxy_repository.add(proxy)

        response = client.get(f"/api/v1/videos/{video_id}/proxy")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == proxy.id
        assert data["source_video_id"] == video_id
        assert data["status"] == "ready"
        assert data["quality"] == "medium"
        assert data["file_size_bytes"] == 50_000
        assert data["generated_at"] is not None

    async def test_missing_proxy_returns_404(
        self,
        client: TestClient,
    ) -> None:
        """GET for video with no proxy returns 404."""
        response = client.get("/api/v1/videos/nonexistent/proxy")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "NOT_FOUND"


# ---------- DELETE /videos/{video_id}/proxy ----------


class TestDeleteProxy:
    """Tests for DELETE /videos/{video_id}/proxy."""

    async def test_returns_freed_bytes(
        self,
        client: TestClient,
        proxy_repository: InMemoryProxyRepository,
    ) -> None:
        """DELETE returns freed_bytes and removes DB record."""
        video_id = "test-video-id"
        proxy = _make_ready_proxy(video_id, file_size_bytes=75_000)
        await proxy_repository.add(proxy)

        response = client.delete(f"/api/v1/videos/{video_id}/proxy")
        assert response.status_code == 200
        data = response.json()
        assert data["freed_bytes"] == 75_000

        # Verify DB record is gone
        remaining = await proxy_repository.list_by_video(video_id)
        assert len(remaining) == 0

    async def test_missing_proxy_returns_404(
        self,
        client: TestClient,
    ) -> None:
        """DELETE for video with no proxy returns 404."""
        response = client.delete("/api/v1/videos/nonexistent/proxy")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "NOT_FOUND"


# ---------- POST /proxy/batch ----------


class TestBatchGenerateProxies:
    """Tests for POST /proxy/batch."""

    async def test_queues_and_skips(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
        proxy_repository: InMemoryProxyRepository,
    ) -> None:
        """POST batch queues videos without proxies and skips those with ready proxies."""
        video1 = make_test_video()
        video2 = make_test_video()
        await video_repository.add(video1)
        await video_repository.add(video2)

        # video2 already has a ready proxy
        proxy = _make_ready_proxy(video2.id)
        await proxy_repository.add(proxy)

        response = client.post(
            "/api/v1/proxy/batch",
            json={"video_ids": [video1.id, video2.id]},
        )
        assert response.status_code == 202
        data = response.json()
        assert video1.id in data["queued"]
        assert video2.id in data["skipped"]

    async def test_skips_missing_videos(
        self,
        client: TestClient,
    ) -> None:
        """POST batch skips video IDs that don't exist."""
        response = client.post(
            "/api/v1/proxy/batch",
            json={"video_ids": ["nonexistent-1", "nonexistent-2"]},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["queued"] == []
        assert len(data["skipped"]) == 2


# ---------- Error response format parity ----------


class TestErrorFormatParity:
    """Verify proxy error responses match JSON:API-style pattern."""

    async def test_404_error_format(
        self,
        client: TestClient,
    ) -> None:
        """404 responses use {"detail": {"code": ..., "message": ...}} structure."""
        response = client.get("/api/v1/videos/nonexistent/proxy")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "code" in data["detail"]
        assert "message" in data["detail"]

    async def test_409_error_format(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
        proxy_repository: InMemoryProxyRepository,
    ) -> None:
        """409 responses use {"detail": {"code": ..., "message": ...}} structure."""
        video = make_test_video()
        await video_repository.add(video)

        proxy = _make_ready_proxy(video.id)
        await proxy_repository.add(proxy)

        response = client.post(f"/api/v1/videos/{video.id}/proxy")
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        assert data["detail"]["code"] == "PROXY_ALREADY_EXISTS"
        assert "message" in data["detail"]


# ---------- Full lifecycle ----------


class TestProxyLifecycle:
    """System test: full proxy lifecycle POST -> GET -> DELETE -> GET 404."""

    async def test_full_lifecycle(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
        proxy_repository: InMemoryProxyRepository,
    ) -> None:
        """Full proxy lifecycle: generate -> status -> delete -> 404."""
        video = make_test_video()
        await video_repository.add(video)

        # Step 1: POST generates proxy (returns 202)
        response = client.post(f"/api/v1/videos/{video.id}/proxy")
        assert response.status_code == 202

        # Manually seed a ready proxy to simulate completion
        proxy = _make_ready_proxy(video.id)
        await proxy_repository.add(proxy)

        # Step 2: GET returns proxy status
        response = client.get(f"/api/v1/videos/{video.id}/proxy")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["quality"] == "medium"
        assert data["file_size_bytes"] > 0
        assert data["generated_at"] is not None

        # Step 3: DELETE removes proxy
        response = client.delete(f"/api/v1/videos/{video.id}/proxy")
        assert response.status_code == 200
        assert response.json()["freed_bytes"] > 0

        # Step 4: GET returns 404
        response = client.get(f"/api/v1/videos/{video.id}/proxy")
        assert response.status_code == 404
