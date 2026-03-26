"""Tests for preview session management API endpoints."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import (
    Clip,
    PreviewQuality,
    PreviewSession,
    PreviewStatus,
)
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.proxy_repository import InMemoryProxyRepository
from stoat_ferret.db.timeline_repository import AsyncInMemoryTimelineRepository
from stoat_ferret.db.version_repository import AsyncInMemoryVersionRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue
from stoat_ferret.preview.manager import (
    PreviewManager,
    SessionExpiredError,
    SessionNotFoundError,
)
from tests.factories import make_test_video

pytestmark = pytest.mark.api


def _make_session(
    session_id: str = "test-session-id",
    project_id: str = "test-project-id",
    status: PreviewStatus = PreviewStatus.READY,
    manifest_path: str | None = None,
    error_message: str | None = None,
) -> PreviewSession:
    """Create a test PreviewSession with defaults."""
    now = datetime.now(timezone.utc)
    return PreviewSession(
        id=session_id,
        project_id=project_id,
        status=status,
        quality_level=PreviewQuality.MEDIUM,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=1),
        manifest_path=manifest_path,
        error_message=error_message,
    )


def _make_mock_preview_manager() -> MagicMock:
    """Create a mock PreviewManager with async methods."""
    manager = MagicMock(spec=PreviewManager)
    manager.start = AsyncMock()
    manager.get_status = AsyncMock()
    manager.seek = AsyncMock()
    manager.stop = AsyncMock()
    return manager


@pytest.fixture
def video_repository() -> AsyncInMemoryVideoRepository:
    """Create in-memory video repository."""
    return AsyncInMemoryVideoRepository()


@pytest.fixture
def project_repository() -> AsyncInMemoryProjectRepository:
    """Create in-memory project repository."""
    return AsyncInMemoryProjectRepository()


@pytest.fixture
def clip_repository() -> AsyncInMemoryClipRepository:
    """Create in-memory clip repository."""
    return AsyncInMemoryClipRepository()


@pytest.fixture
def mock_preview_manager() -> MagicMock:
    """Create a mock preview manager."""
    return _make_mock_preview_manager()


@pytest.fixture
def preview_app(
    video_repository: AsyncInMemoryVideoRepository,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    mock_preview_manager: MagicMock,
) -> FastAPI:
    """Create test app with preview manager injected."""
    app = create_app(
        video_repository=video_repository,
        project_repository=project_repository,
        clip_repository=clip_repository,
        timeline_repository=AsyncInMemoryTimelineRepository(),
        version_repository=AsyncInMemoryVersionRepository(),
        batch_repository=None,
        proxy_repository=InMemoryProxyRepository(),
        job_queue=InMemoryJobQueue(),
        preview_manager=mock_preview_manager,
    )
    return app


@pytest.fixture
def client(preview_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create test client for preview API requests."""
    with TestClient(preview_app) as c:
        yield c


async def _seed_project(project_repository: AsyncInMemoryProjectRepository) -> str:
    """Add a test project and return its ID."""
    from stoat_ferret.db.models import Project

    project_id = Project.new_id()
    now = datetime.now(timezone.utc)
    project = Project(
        id=project_id,
        name="Test Project",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)
    return project_id


async def _seed_clip(
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
    project_id: str,
) -> str:
    """Seed a clip with a backing video in the repositories."""
    video = make_test_video()
    await video_repository.add(video)

    now = datetime.now(timezone.utc)
    clip = Clip(
        id=Clip.new_id(),
        project_id=project_id,
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip)
    return video.id


# ---------- POST /projects/{project_id}/preview/start ----------


class TestStartPreview:
    """Tests for POST /projects/{project_id}/preview/start."""

    async def test_returns_202_with_session_id(
        self,
        client: TestClient,
        project_repository: AsyncInMemoryProjectRepository,
        clip_repository: AsyncInMemoryClipRepository,
        video_repository: AsyncInMemoryVideoRepository,
        mock_preview_manager: MagicMock,
    ) -> None:
        """POST returns 202 Accepted with session_id."""
        project_id = await _seed_project(project_repository)
        await _seed_clip(clip_repository, video_repository, project_id)

        session = _make_session(project_id=project_id, status=PreviewStatus.GENERATING)
        mock_preview_manager.start.return_value = session

        response = client.post(f"/api/v1/projects/{project_id}/preview/start")
        assert response.status_code == 202
        data = response.json()
        assert "session_id" in data
        assert data["session_id"] == session.id

    async def test_nonexistent_project_returns_404(
        self,
        client: TestClient,
    ) -> None:
        """POST for non-existent project returns 404."""
        response = client.post("/api/v1/projects/nonexistent/preview/start")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "NOT_FOUND"

    async def test_empty_timeline_returns_422(
        self,
        client: TestClient,
        project_repository: AsyncInMemoryProjectRepository,
    ) -> None:
        """POST for project with empty timeline returns 422 EMPTY_TIMELINE."""
        project_id = await _seed_project(project_repository)

        response = client.post(f"/api/v1/projects/{project_id}/preview/start")
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["code"] == "EMPTY_TIMELINE"

    async def test_session_limit_returns_429(
        self,
        client: TestClient,
        project_repository: AsyncInMemoryProjectRepository,
        clip_repository: AsyncInMemoryClipRepository,
        video_repository: AsyncInMemoryVideoRepository,
        mock_preview_manager: MagicMock,
    ) -> None:
        """POST when session limit reached returns 429."""
        from stoat_ferret.preview.manager import SessionLimitError

        project_id = await _seed_project(project_repository)
        await _seed_clip(clip_repository, video_repository, project_id)

        mock_preview_manager.start.side_effect = SessionLimitError("limit reached")

        response = client.post(f"/api/v1/projects/{project_id}/preview/start")
        assert response.status_code == 429
        data = response.json()
        assert data["detail"]["code"] == "SESSION_LIMIT"


# ---------- GET /preview/{session_id} ----------


class TestGetPreviewStatus:
    """Tests for GET /preview/{session_id}."""

    async def test_returns_status_with_manifest_url(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
    ) -> None:
        """GET returns status with manifest_url when ready."""
        session = _make_session(
            status=PreviewStatus.READY,
            manifest_path="/tmp/previews/test-session-id/manifest.m3u8",
        )
        mock_preview_manager.get_status.return_value = session

        response = client.get("/api/v1/preview/test-session-id")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-id"
        assert data["status"] == "ready"
        assert data["manifest_url"] == "/api/v1/preview/test-session-id/manifest.m3u8"

    async def test_generating_status_no_manifest_url(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
    ) -> None:
        """GET returns status without manifest_url when not ready."""
        session = _make_session(status=PreviewStatus.GENERATING)
        mock_preview_manager.get_status.return_value = session

        response = client.get("/api/v1/preview/test-session-id")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "generating"
        assert data["manifest_url"] is None

    async def test_nonexistent_session_returns_404(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
    ) -> None:
        """GET for non-existent session returns 404."""
        mock_preview_manager.get_status.side_effect = SessionNotFoundError("not found")

        response = client.get("/api/v1/preview/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "NOT_FOUND"

    async def test_expired_session_returns_404(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
    ) -> None:
        """GET for expired session returns 404."""
        mock_preview_manager.get_status.side_effect = SessionExpiredError("expired")

        response = client.get("/api/v1/preview/expired-session")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "SESSION_EXPIRED"


# ---------- POST /preview/{session_id}/seek ----------


class TestSeekPreview:
    """Tests for POST /preview/{session_id}/seek."""

    async def test_returns_seeking_status(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
    ) -> None:
        """POST seek returns 200 with seeking status."""
        session = _make_session(status=PreviewStatus.SEEKING)
        mock_preview_manager.seek.return_value = session

        response = client.post(
            "/api/v1/preview/test-session-id/seek",
            json={"position": 5.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-id"
        assert data["status"] == "seeking"

    async def test_validates_position(
        self,
        client: TestClient,
    ) -> None:
        """POST seek with negative position returns 422."""
        response = client.post(
            "/api/v1/preview/test-session-id/seek",
            json={"position": -1.0},
        )
        assert response.status_code == 422

    async def test_missing_position_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """POST seek without position returns 422."""
        response = client.post(
            "/api/v1/preview/test-session-id/seek",
            json={},
        )
        assert response.status_code == 422

    async def test_nonexistent_session_returns_404(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
    ) -> None:
        """POST seek for non-existent session returns 404."""
        mock_preview_manager.seek.side_effect = SessionNotFoundError("not found")

        response = client.post(
            "/api/v1/preview/nonexistent/seek",
            json={"position": 5.0},
        )
        assert response.status_code == 404


# ---------- DELETE /preview/{session_id} ----------


class TestStopPreview:
    """Tests for DELETE /preview/{session_id}."""

    async def test_returns_confirmation(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
    ) -> None:
        """DELETE returns 200 with confirmation."""
        mock_preview_manager.stop.return_value = None

        response = client.delete("/api/v1/preview/test-session-id")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-id"
        assert data["stopped"] is True

    async def test_nonexistent_session_returns_404(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
    ) -> None:
        """DELETE for non-existent session returns 404."""
        mock_preview_manager.stop.side_effect = SessionNotFoundError("not found")

        response = client.delete("/api/v1/preview/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "NOT_FOUND"


# ---------- GET /preview/{session_id}/manifest.m3u8 ----------


class TestGetManifest:
    """Tests for GET /preview/{session_id}/manifest.m3u8."""

    async def test_serves_manifest_with_correct_content_type(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """GET manifest serves HLS manifest with correct Content-Type."""
        manifest_file = tmp_path / "manifest.m3u8"
        manifest_content = (
            "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:2\n"
            "#EXTINF:2.0,\nsegment_000.ts\n#EXT-X-ENDLIST\n"
        )
        manifest_file.write_text(manifest_content)

        session = _make_session(
            status=PreviewStatus.READY,
            manifest_path=str(manifest_file),
        )
        mock_preview_manager.get_status.return_value = session

        response = client.get("/api/v1/preview/test-session-id/manifest.m3u8")
        assert response.status_code == 200
        assert "application/vnd.apple.mpegurl" in response.headers["content-type"]
        assert "#EXTM3U" in response.text

    async def test_not_ready_returns_404(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
    ) -> None:
        """GET manifest when session not ready returns 404."""
        session = _make_session(status=PreviewStatus.GENERATING, manifest_path=None)
        mock_preview_manager.get_status.return_value = session

        response = client.get("/api/v1/preview/test-session-id/manifest.m3u8")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "NOT_READY"

    async def test_nonexistent_session_returns_404(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
    ) -> None:
        """GET manifest for non-existent session returns 404."""
        mock_preview_manager.get_status.side_effect = SessionNotFoundError("not found")

        response = client.get("/api/v1/preview/nonexistent/manifest.m3u8")
        assert response.status_code == 404


# ---------- GET /preview/{session_id}/segment_{index}.ts ----------


class TestGetSegment:
    """Tests for GET /preview/{session_id}/segment_{index}.ts."""

    async def test_serves_segment_with_correct_content_type(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """GET segment serves MPEG-TS with correct Content-Type."""
        # Create a fake segment file
        segment_file = tmp_path / "segment_000.ts"
        segment_content = b"\x47" * 188  # TS sync byte
        segment_file.write_bytes(segment_content)

        manifest_file = tmp_path / "manifest.m3u8"
        manifest_file.write_text("#EXTM3U\n")

        session = _make_session(
            status=PreviewStatus.READY,
            manifest_path=str(manifest_file),
        )
        mock_preview_manager.get_status.return_value = session

        response = client.get("/api/v1/preview/test-session-id/segment_0.ts")
        assert response.status_code == 200
        assert response.headers["content-type"] == "video/MP2T"
        assert response.content == segment_content

    async def test_missing_segment_returns_404(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """GET for non-existent segment returns 404."""
        manifest_file = tmp_path / "manifest.m3u8"
        manifest_file.write_text("#EXTM3U\n")

        session = _make_session(
            status=PreviewStatus.READY,
            manifest_path=str(manifest_file),
        )
        mock_preview_manager.get_status.return_value = session

        response = client.get("/api/v1/preview/test-session-id/segment_99.ts")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "NOT_FOUND"

    async def test_not_ready_returns_404(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
    ) -> None:
        """GET segment when session not ready returns 404."""
        session = _make_session(status=PreviewStatus.GENERATING, manifest_path=None)
        mock_preview_manager.get_status.return_value = session

        response = client.get("/api/v1/preview/test-session-id/segment_0.ts")
        assert response.status_code == 404


# ---------- Error response format parity ----------


class TestErrorResponseFormat:
    """Verify error responses follow the same format as proxy endpoints."""

    async def test_404_error_has_code_and_message(
        self,
        client: TestClient,
        mock_preview_manager: MagicMock,
    ) -> None:
        """404 error includes code and message in detail."""
        mock_preview_manager.get_status.side_effect = SessionNotFoundError("not found")

        response = client.get("/api/v1/preview/nonexistent")
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "code" in detail
        assert "message" in detail

    async def test_422_empty_timeline_has_code_and_message(
        self,
        client: TestClient,
        project_repository: AsyncInMemoryProjectRepository,
    ) -> None:
        """422 EMPTY_TIMELINE includes code and message in detail."""
        project_id = await _seed_project(project_repository)

        response = client.post(f"/api/v1/projects/{project_id}/preview/start")
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["code"] == "EMPTY_TIMELINE"
        assert "message" in detail
