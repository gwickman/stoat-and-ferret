"""Tests for waveform API endpoints."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.services.waveform import WaveformService
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.models import Waveform, WaveformFormat, WaveformStatus
from tests.factories import make_test_video

pytestmark = pytest.mark.api


def _make_ready_waveform(
    video_id: str,
    fmt: WaveformFormat = WaveformFormat.PNG,
    file_path: str | None = None,
) -> Waveform:
    """Create a READY waveform for testing."""
    return Waveform(
        id=Waveform.new_id(),
        video_id=video_id,
        format=fmt,
        status=WaveformStatus.READY,
        created_at=datetime.now(timezone.utc),
        file_path=file_path,
        duration=120.0,
        channels=2,
    )


@pytest.fixture
def mock_waveform_service() -> MagicMock:
    """Create a mock WaveformService."""
    svc = MagicMock(spec=WaveformService)
    svc.get_waveform = AsyncMock(return_value=None)
    return svc


@pytest.fixture
def video_repository() -> AsyncInMemoryVideoRepository:
    """Create in-memory video repository."""
    return AsyncInMemoryVideoRepository()


@pytest.fixture
def app(
    video_repository: AsyncInMemoryVideoRepository,
    mock_waveform_service: MagicMock,
) -> FastAPI:
    """Create test app with mock waveform service."""
    return create_app(
        video_repository=video_repository,
        waveform_service=mock_waveform_service,
    )


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    with TestClient(app) as c:
        yield c


# ---------- POST /videos/{video_id}/waveform ----------


class TestGenerateWaveform:
    """Tests for POST /api/v1/videos/{video_id}/waveform."""

    async def test_returns_202_with_waveform_id(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
    ) -> None:
        """POST returns 202 Accepted with waveform_id in response body."""
        video = make_test_video()
        await video_repository.add(video)

        response = client.post(f"/api/v1/videos/{video.id}/waveform")
        assert response.status_code == 202
        data = response.json()
        assert "waveform_id" in data
        assert isinstance(data["waveform_id"], str)
        assert data["status"] == "pending"

    async def test_format_png_accepted(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
    ) -> None:
        """POST with format=png returns 202."""
        video = make_test_video()
        await video_repository.add(video)

        response = client.post(
            f"/api/v1/videos/{video.id}/waveform",
            json={"format": "png"},
        )
        assert response.status_code == 202

    async def test_format_json_accepted(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
    ) -> None:
        """POST with format=json returns 202."""
        video = make_test_video()
        await video_repository.add(video)

        response = client.post(
            f"/api/v1/videos/{video.id}/waveform",
            json={"format": "json"},
        )
        assert response.status_code == 202

    async def test_invalid_format_rejected(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
    ) -> None:
        """POST with invalid format returns 422."""
        video = make_test_video()
        await video_repository.add(video)

        response = client.post(
            f"/api/v1/videos/{video.id}/waveform",
            json={"format": "wav"},
        )
        assert response.status_code == 422

    async def test_missing_video_returns_404(
        self,
        client: TestClient,
    ) -> None:
        """POST for non-existent video returns 404."""
        response = client.post("/api/v1/videos/nonexistent/waveform")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "NOT_FOUND"

    async def test_default_format_is_png(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
        mock_waveform_service: MagicMock,
    ) -> None:
        """POST with empty body defaults to PNG format."""
        video = make_test_video()
        await video_repository.add(video)

        response = client.post(f"/api/v1/videos/{video.id}/waveform")
        assert response.status_code == 202

        # generate_png should have been queued (via background tasks)
        mock_waveform_service.generate_png.assert_called_once()


# ---------- GET /videos/{video_id}/waveform ----------


class TestGetWaveformMetadata:
    """Tests for GET /api/v1/videos/{video_id}/waveform."""

    async def test_returns_metadata_with_all_fields(
        self,
        client: TestClient,
        mock_waveform_service: MagicMock,
    ) -> None:
        """GET metadata returns format, duration, channels, samples_per_second."""
        waveform = _make_ready_waveform("vid-1", WaveformFormat.JSON)
        mock_waveform_service.get_waveform.return_value = waveform

        response = client.get("/api/v1/videos/vid-1/waveform?format=json")
        assert response.status_code == 200
        data = response.json()

        assert data["waveform_id"] == waveform.id
        assert data["video_id"] == "vid-1"
        assert data["status"] == "ready"
        assert data["format"] == "json"
        assert data["duration"] == 120.0
        assert data["channels"] == 2
        assert data["samples_per_second"] == 10

    async def test_png_metadata_zero_samples_per_second(
        self,
        client: TestClient,
        mock_waveform_service: MagicMock,
    ) -> None:
        """GET PNG metadata returns samples_per_second=0."""
        waveform = _make_ready_waveform("vid-1", WaveformFormat.PNG)
        mock_waveform_service.get_waveform.return_value = waveform

        response = client.get("/api/v1/videos/vid-1/waveform?format=png")
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "png"
        assert data["samples_per_second"] == 0

    async def test_not_generated_returns_404(
        self,
        client: TestClient,
        mock_waveform_service: MagicMock,
    ) -> None:
        """GET metadata returns 404 when no waveform exists."""
        mock_waveform_service.get_waveform.return_value = None

        response = client.get("/api/v1/videos/vid-1/waveform")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "WAVEFORM_NOT_FOUND"


# ---------- GET /videos/{video_id}/waveform.png ----------


class TestGetWaveformImage:
    """Tests for GET /api/v1/videos/{video_id}/waveform.png."""

    async def test_serves_png_image(
        self,
        client: TestClient,
        mock_waveform_service: MagicMock,
    ) -> None:
        """GET waveform.png serves image with content-type image/png."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Minimal PNG header
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            tmp_path = f.name

        try:
            waveform = _make_ready_waveform("vid-1", WaveformFormat.PNG, file_path=tmp_path)
            mock_waveform_service.get_waveform.return_value = waveform

            response = client.get("/api/v1/videos/vid-1/waveform.png")
            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"
            assert len(response.content) > 0
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def test_not_generated_returns_404(
        self,
        client: TestClient,
        mock_waveform_service: MagicMock,
    ) -> None:
        """GET waveform.png returns 404 when no waveform exists."""
        mock_waveform_service.get_waveform.return_value = None

        response = client.get("/api/v1/videos/vid-1/waveform.png")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "WAVEFORM_NOT_FOUND"

    async def test_file_missing_returns_404(
        self,
        client: TestClient,
        mock_waveform_service: MagicMock,
    ) -> None:
        """GET waveform.png returns 404 when file doesn't exist on disk."""
        waveform = _make_ready_waveform(
            "vid-1", WaveformFormat.PNG, file_path="/nonexistent/waveform.png"
        )
        mock_waveform_service.get_waveform.return_value = waveform

        response = client.get("/api/v1/videos/vid-1/waveform.png")
        assert response.status_code == 404

    async def test_no_file_path_returns_404(
        self,
        client: TestClient,
        mock_waveform_service: MagicMock,
    ) -> None:
        """GET waveform.png returns 404 when waveform has no file_path."""
        waveform = _make_ready_waveform("vid-1", WaveformFormat.PNG)
        mock_waveform_service.get_waveform.return_value = waveform

        response = client.get("/api/v1/videos/vid-1/waveform.png")
        assert response.status_code == 404


# ---------- GET /videos/{video_id}/waveform.json ----------


class TestGetWaveformJson:
    """Tests for GET /api/v1/videos/{video_id}/waveform.json."""

    async def test_returns_samples_array(
        self,
        client: TestClient,
        mock_waveform_service: MagicMock,
    ) -> None:
        """GET waveform.json returns JSON with samples array."""
        json_data = {
            "video_id": "vid-1",
            "channels": 2,
            "samples_per_second": 10,
            "frames": [
                {"Peak_level": "-3.5", "RMS_level": "-12.1"},
                {"Peak_level": "-1.2", "RMS_level": "-8.3"},
            ],
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(json_data, f)
            tmp_path = f.name

        try:
            waveform = _make_ready_waveform("vid-1", WaveformFormat.JSON, file_path=tmp_path)
            mock_waveform_service.get_waveform.return_value = waveform

            response = client.get("/api/v1/videos/vid-1/waveform.json")
            assert response.status_code == 200
            data = response.json()

            assert data["video_id"] == "vid-1"
            assert data["channels"] == 2
            assert data["samples_per_second"] == 10
            assert len(data["samples"]) == 2
            assert data["samples"][0]["Peak_level"] == "-3.5"
            assert data["samples"][0]["RMS_level"] == "-12.1"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def test_not_generated_returns_404(
        self,
        client: TestClient,
        mock_waveform_service: MagicMock,
    ) -> None:
        """GET waveform.json returns 404 when no JSON waveform exists."""
        mock_waveform_service.get_waveform.return_value = None

        response = client.get("/api/v1/videos/vid-1/waveform.json")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "WAVEFORM_NOT_FOUND"

    async def test_file_missing_returns_404(
        self,
        client: TestClient,
        mock_waveform_service: MagicMock,
    ) -> None:
        """GET waveform.json returns 404 when data file doesn't exist."""
        waveform = _make_ready_waveform(
            "vid-1", WaveformFormat.JSON, file_path="/nonexistent/waveform.json"
        )
        mock_waveform_service.get_waveform.return_value = waveform

        response = client.get("/api/v1/videos/vid-1/waveform.json")
        assert response.status_code == 404


# ---------- Parity with thumbnail strip API ----------


class TestApiParity:
    """Verify waveform API follows same patterns as thumbnail strip API."""

    async def test_post_returns_202_structure(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
    ) -> None:
        """POST returns 202 with consistent response structure."""
        video = make_test_video()
        await video_repository.add(video)

        response = client.post(f"/api/v1/videos/{video.id}/waveform")
        assert response.status_code == 202
        data = response.json()
        # Response has an ID field for tracking (waveform_id, analogous to strip_id)
        assert "waveform_id" in data
        assert "status" in data

    async def test_404_response_structure(
        self,
        client: TestClient,
        mock_waveform_service: MagicMock,
    ) -> None:
        """404 responses use consistent code/message structure."""
        mock_waveform_service.get_waveform.return_value = None

        response = client.get("/api/v1/videos/missing/waveform")
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "code" in detail
        assert "message" in detail
