"""Tests for thumbnail strip API endpoints."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.services.thumbnail import ThumbnailService
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.models import ThumbnailStrip, ThumbnailStripStatus
from tests.factories import make_test_video

pytestmark = pytest.mark.api


def _make_ready_strip(video_id: str, file_path: str | None = None) -> ThumbnailStrip:
    """Create a READY thumbnail strip for testing."""
    return ThumbnailStrip(
        id=ThumbnailStrip.new_id(),
        video_id=video_id,
        status=ThumbnailStripStatus.READY,
        created_at=datetime.now(timezone.utc),
        file_path=file_path,
        frame_count=20,
        frame_width=160,
        frame_height=90,
        interval_seconds=5.0,
        columns=10,
        rows=2,
    )


def _make_pending_strip(video_id: str) -> ThumbnailStrip:
    """Create a PENDING thumbnail strip for testing."""
    return ThumbnailStrip(
        id=ThumbnailStrip.new_id(),
        video_id=video_id,
        status=ThumbnailStripStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        frame_count=0,
        frame_width=160,
        frame_height=90,
        interval_seconds=5.0,
        columns=10,
        rows=0,
    )


@pytest.fixture
def mock_thumbnail_service() -> MagicMock:
    """Create a mock ThumbnailService."""
    svc = MagicMock(spec=ThumbnailService)
    svc.get_strip = MagicMock(return_value=None)
    svc.generate_strip = AsyncMock(return_value=None)
    return svc


@pytest.fixture
def video_repository() -> AsyncInMemoryVideoRepository:
    """Create in-memory video repository."""
    return AsyncInMemoryVideoRepository()


@pytest.fixture
def app(
    video_repository: AsyncInMemoryVideoRepository,
    mock_thumbnail_service: MagicMock,
) -> FastAPI:
    """Create test app with mock thumbnail service."""
    return create_app(
        video_repository=video_repository,
        thumbnail_service=mock_thumbnail_service,
    )


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    with TestClient(app) as c:
        yield c


# ---------- POST /videos/{video_id}/thumbnails/strip ----------


class TestGenerateStrip:
    """Tests for POST /api/v1/videos/{video_id}/thumbnails/strip."""

    async def test_returns_202_with_strip_id(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
    ) -> None:
        """POST returns 202 Accepted with strip_id in response body."""
        video = make_test_video()
        await video_repository.add(video)

        response = client.post(f"/api/v1/videos/{video.id}/thumbnails/strip")
        assert response.status_code == 202
        data = response.json()
        assert "strip_id" in data
        assert isinstance(data["strip_id"], str)
        assert data["status"] == "pending"

    async def test_missing_video_returns_404(
        self,
        client: TestClient,
    ) -> None:
        """POST for non-existent video returns 404."""
        response = client.post("/api/v1/videos/nonexistent/thumbnails/strip")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "NOT_FOUND"

    async def test_configurable_parameters(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
        mock_thumbnail_service: MagicMock,
    ) -> None:
        """POST body accepts optional interval_seconds, frame_width, frame_height."""
        video = make_test_video()
        await video_repository.add(video)

        response = client.post(
            f"/api/v1/videos/{video.id}/thumbnails/strip",
            json={
                "interval_seconds": 2.0,
                "frame_width": 200,
                "frame_height": 112,
            },
        )
        assert response.status_code == 202

        # Verify parameters were passed through to the service
        mock_thumbnail_service.generate_strip.assert_called_once()
        call_kwargs = mock_thumbnail_service.generate_strip.call_args.kwargs
        assert call_kwargs["interval"] == 2.0
        assert call_kwargs["frame_width"] == 200
        assert call_kwargs["frame_height"] == 112

    async def test_default_parameters_used(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
        mock_thumbnail_service: MagicMock,
    ) -> None:
        """POST with empty body passes default values to service."""
        video = make_test_video()
        await video_repository.add(video)

        response = client.post(f"/api/v1/videos/{video.id}/thumbnails/strip")
        assert response.status_code == 202

        call_kwargs = mock_thumbnail_service.generate_strip.call_args.kwargs
        assert call_kwargs["interval"] is None  # service uses its own default
        assert call_kwargs["frame_width"] == 160
        assert call_kwargs["frame_height"] == 90


# ---------- GET /videos/{video_id}/thumbnails/strip ----------


class TestGetStripMetadata:
    """Tests for GET /api/v1/videos/{video_id}/thumbnails/strip."""

    async def test_returns_metadata_with_all_fields(
        self,
        client: TestClient,
        mock_thumbnail_service: MagicMock,
    ) -> None:
        """GET metadata returns all six required fields plus strip_id and status."""
        strip = _make_ready_strip("vid-1")
        mock_thumbnail_service.get_strip.return_value = strip

        response = client.get("/api/v1/videos/vid-1/thumbnails/strip")
        assert response.status_code == 200
        data = response.json()

        assert data["strip_id"] == strip.id
        assert data["video_id"] == "vid-1"
        assert data["status"] == "ready"
        assert data["frame_count"] == 20
        assert data["frame_width"] == 160
        assert data["frame_height"] == 90
        assert data["interval_seconds"] == 5.0
        assert data["columns"] == 10
        assert data["rows"] == 2

    async def test_not_generated_returns_404(
        self,
        client: TestClient,
        mock_thumbnail_service: MagicMock,
    ) -> None:
        """GET metadata returns 404 when no strip exists."""
        mock_thumbnail_service.get_strip.return_value = None

        response = client.get("/api/v1/videos/vid-1/thumbnails/strip")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "STRIP_NOT_FOUND"

    async def test_columns_and_rows_for_coordinate_lookup(
        self,
        client: TestClient,
        mock_thumbnail_service: MagicMock,
    ) -> None:
        """columns and rows enable client-side sprite sheet coordinate calculation."""
        strip = _make_ready_strip("vid-1")
        strip.columns = 8
        strip.rows = 3
        mock_thumbnail_service.get_strip.return_value = strip

        response = client.get("/api/v1/videos/vid-1/thumbnails/strip")
        data = response.json()
        assert data["columns"] == 8
        assert data["rows"] == 3


# ---------- GET /videos/{video_id}/thumbnails/strip.jpg ----------


class TestGetStripImage:
    """Tests for GET /api/v1/videos/{video_id}/thumbnails/strip.jpg."""

    async def test_serves_jpeg_image(
        self,
        client: TestClient,
        mock_thumbnail_service: MagicMock,
    ) -> None:
        """GET strip.jpg serves image with content-type image/jpeg."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # minimal JPEG header
            tmp_path = f.name

        try:
            strip = _make_ready_strip("vid-1", file_path=tmp_path)
            mock_thumbnail_service.get_strip.return_value = strip

            response = client.get("/api/v1/videos/vid-1/thumbnails/strip.jpg")
            assert response.status_code == 200
            assert response.headers["content-type"] == "image/jpeg"
            assert len(response.content) > 0
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def test_not_generated_returns_404(
        self,
        client: TestClient,
        mock_thumbnail_service: MagicMock,
    ) -> None:
        """GET strip.jpg returns 404 when no strip exists."""
        mock_thumbnail_service.get_strip.return_value = None

        response = client.get("/api/v1/videos/vid-1/thumbnails/strip.jpg")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "STRIP_NOT_FOUND"

    async def test_file_missing_returns_404(
        self,
        client: TestClient,
        mock_thumbnail_service: MagicMock,
    ) -> None:
        """GET strip.jpg returns 404 when strip file doesn't exist on disk."""
        strip = _make_ready_strip("vid-1", file_path="/nonexistent/strip.jpg")
        mock_thumbnail_service.get_strip.return_value = strip

        response = client.get("/api/v1/videos/vid-1/thumbnails/strip.jpg")
        assert response.status_code == 404

    async def test_no_file_path_returns_404(
        self,
        client: TestClient,
        mock_thumbnail_service: MagicMock,
    ) -> None:
        """GET strip.jpg returns 404 when strip has no file_path (still generating)."""
        strip = _make_pending_strip("vid-1")
        mock_thumbnail_service.get_strip.return_value = strip

        response = client.get("/api/v1/videos/vid-1/thumbnails/strip.jpg")
        assert response.status_code == 404


# ---------- Parity with proxy/waveform API patterns ----------


class TestApiParity:
    """Verify thumbnail strip API follows established patterns."""

    async def test_post_returns_202_structure(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
    ) -> None:
        """POST returns 202 with consistent response structure."""
        video = make_test_video()
        await video_repository.add(video)

        response = client.post(f"/api/v1/videos/{video.id}/thumbnails/strip")
        assert response.status_code == 202
        data = response.json()
        # Response has an ID field for tracking (strip_id, analogous to job_id)
        assert "strip_id" in data
        assert "status" in data

    async def test_404_response_structure(
        self,
        client: TestClient,
        mock_thumbnail_service: MagicMock,
    ) -> None:
        """404 responses use consistent code/message structure."""
        mock_thumbnail_service.get_strip.return_value = None

        response = client.get("/api/v1/videos/missing/thumbnails/strip")
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "code" in detail
        assert "message" in detail
