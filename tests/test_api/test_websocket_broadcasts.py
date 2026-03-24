"""Tests for WebSocket broadcast wiring in API operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.services.scan import make_scan_handler
from stoat_ferret.api.websocket.events import EventType
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue


@pytest.fixture
def mock_ws_manager() -> ConnectionManager:
    """Create a ConnectionManager with mocked broadcast.

    Returns:
        ConnectionManager with broadcast replaced by AsyncMock.
    """
    manager = ConnectionManager()
    manager.broadcast = AsyncMock()  # type: ignore[assignment]
    return manager


@pytest.fixture
def broadcast_app(mock_ws_manager: ConnectionManager) -> FastAPI:
    """Create test app with mocked ws_manager injected.

    Args:
        mock_ws_manager: ConnectionManager with mocked broadcast.

    Returns:
        Configured FastAPI application for testing broadcasts.
    """
    video_repo = AsyncInMemoryVideoRepository()
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()
    job_queue = InMemoryJobQueue()
    return create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        job_queue=job_queue,
        ws_manager=mock_ws_manager,
    )


@pytest.fixture
def broadcast_client(broadcast_app: FastAPI) -> TestClient:
    """Create test client for broadcast tests.

    Args:
        broadcast_app: FastAPI application with mocked ws_manager.

    Returns:
        Test client for making HTTP requests.
    """
    with TestClient(broadcast_app) as c:
        yield c  # type: ignore[misc]


class TestProjectCreatedBroadcast:
    """Tests for PROJECT_CREATED broadcast on project creation."""

    @pytest.mark.api
    def test_broadcast_called_on_project_creation(
        self,
        broadcast_client: TestClient,
        mock_ws_manager: ConnectionManager,
    ) -> None:
        """Verify broadcast is called when a project is created."""
        response = broadcast_client.post(
            "/api/v1/projects",
            json={"name": "Test Project"},
        )
        assert response.status_code == 201

        mock_ws_manager.broadcast.assert_called_once()  # type: ignore[union-attr]

    @pytest.mark.api
    def test_broadcast_event_type_is_project_created(
        self,
        broadcast_client: TestClient,
        mock_ws_manager: ConnectionManager,
    ) -> None:
        """Verify broadcast event type is project_created."""
        broadcast_client.post(
            "/api/v1/projects",
            json={"name": "Test Project"},
        )

        event = mock_ws_manager.broadcast.call_args[0][0]  # type: ignore[union-attr]
        assert event["type"] == EventType.PROJECT_CREATED.value

    @pytest.mark.api
    def test_broadcast_payload_contains_project_id_and_name(
        self,
        broadcast_client: TestClient,
        mock_ws_manager: ConnectionManager,
    ) -> None:
        """Verify broadcast payload includes project_id and name."""
        response = broadcast_client.post(
            "/api/v1/projects",
            json={"name": "My Video Project"},
        )
        project_id = response.json()["id"]

        event = mock_ws_manager.broadcast.call_args[0][0]  # type: ignore[union-attr]
        assert event["payload"]["project_id"] == project_id
        assert event["payload"]["name"] == "My Video Project"

    @pytest.mark.api
    def test_broadcast_event_has_timestamp(
        self,
        broadcast_client: TestClient,
        mock_ws_manager: ConnectionManager,
    ) -> None:
        """Verify broadcast event includes a timestamp."""
        broadcast_client.post(
            "/api/v1/projects",
            json={"name": "Test Project"},
        )

        event = mock_ws_manager.broadcast.call_args[0][0]  # type: ignore[union-attr]
        assert "timestamp" in event

    @pytest.mark.api
    def test_no_broadcast_without_ws_manager(self) -> None:
        """Verify no crash when ws_manager is not set."""
        app = create_app(
            video_repository=AsyncInMemoryVideoRepository(),
            project_repository=AsyncInMemoryProjectRepository(),
            clip_repository=AsyncInMemoryClipRepository(),
            job_queue=InMemoryJobQueue(),
        )
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/projects",
                json={"name": "No WS Project"},
            )
            assert response.status_code == 201


class TestScanBroadcasts:
    """Tests for SCAN_STARTED and SCAN_COMPLETED broadcasts during scan."""

    @pytest.mark.api
    async def test_scan_started_broadcast(self) -> None:
        """Verify SCAN_STARTED broadcast is sent at start of scan."""
        mock_manager = ConnectionManager()
        mock_manager.broadcast = AsyncMock()  # type: ignore[assignment]
        video_repo = AsyncInMemoryVideoRepository()

        handler = make_scan_handler(video_repo, ws_manager=mock_manager)

        with patch(
            "stoat_ferret.api.services.scan.scan_directory",
        ) as mock_scan:
            from stoat_ferret.api.schemas.video import ScanResponse

            mock_scan.return_value = ScanResponse(scanned=0, new=0, updated=0, skipped=0, errors=[])
            await handler("scan", {"path": "/tmp/videos", "recursive": True})

        calls = mock_manager.broadcast.call_args_list  # type: ignore[union-attr]
        assert len(calls) == 2

        started_event = calls[0][0][0]
        assert started_event["type"] == EventType.SCAN_STARTED.value
        assert started_event["payload"]["path"] == "/tmp/videos"

    @pytest.mark.api
    async def test_scan_completed_broadcast(self) -> None:
        """Verify SCAN_COMPLETED broadcast is sent after scan finishes."""
        mock_manager = ConnectionManager()
        mock_manager.broadcast = AsyncMock()  # type: ignore[assignment]
        video_repo = AsyncInMemoryVideoRepository()

        handler = make_scan_handler(video_repo, ws_manager=mock_manager)

        with patch(
            "stoat_ferret.api.services.scan.scan_directory",
        ) as mock_scan:
            from stoat_ferret.api.schemas.video import ScanResponse

            mock_scan.return_value = ScanResponse(scanned=5, new=3, updated=2, skipped=0, errors=[])
            await handler("scan", {"path": "/tmp/videos", "recursive": True})

        calls = mock_manager.broadcast.call_args_list  # type: ignore[union-attr]
        completed_event = calls[1][0][0]
        assert completed_event["type"] == EventType.SCAN_COMPLETED.value
        assert completed_event["payload"]["path"] == "/tmp/videos"
        assert completed_event["payload"]["video_count"] == 5

    @pytest.mark.api
    async def test_scan_completed_video_count_is_new_plus_updated(self) -> None:
        """Verify video_count in SCAN_COMPLETED is new + updated."""
        mock_manager = ConnectionManager()
        mock_manager.broadcast = AsyncMock()  # type: ignore[assignment]
        video_repo = AsyncInMemoryVideoRepository()

        handler = make_scan_handler(video_repo, ws_manager=mock_manager)

        with patch(
            "stoat_ferret.api.services.scan.scan_directory",
        ) as mock_scan:
            from stoat_ferret.api.schemas.video import ScanResponse

            mock_scan.return_value = ScanResponse(
                scanned=10, new=4, updated=3, skipped=3, errors=[]
            )
            await handler("scan", {"path": "/tmp/vids"})

        completed_event = mock_manager.broadcast.call_args_list[1][0][0]  # type: ignore[union-attr]
        assert completed_event["payload"]["video_count"] == 7

    @pytest.mark.api
    async def test_no_broadcast_without_ws_manager(self) -> None:
        """Verify scan works without ws_manager (no crash)."""
        video_repo = AsyncInMemoryVideoRepository()
        handler = make_scan_handler(video_repo)

        with patch(
            "stoat_ferret.api.services.scan.scan_directory",
        ) as mock_scan:
            from stoat_ferret.api.schemas.video import ScanResponse

            mock_scan.return_value = ScanResponse(scanned=0, new=0, updated=0, skipped=0, errors=[])
            result = await handler("scan", {"path": "/tmp/videos"})

        assert result["scanned"] == 0

    @pytest.mark.api
    async def test_job_progress_broadcast_during_scan(self) -> None:
        """Verify JOB_PROGRESS events are broadcast during scan execution."""
        mock_manager = ConnectionManager()
        mock_manager.broadcast = AsyncMock()  # type: ignore[assignment]
        video_repo = AsyncInMemoryVideoRepository()
        job_queue = InMemoryJobQueue()

        handler = make_scan_handler(video_repo, ws_manager=mock_manager, queue=job_queue)

        with patch(
            "stoat_ferret.api.services.scan.scan_directory",
        ) as mock_scan:
            from stoat_ferret.api.schemas.video import ScanResponse

            mock_scan.return_value = ScanResponse(scanned=3, new=3, updated=0, skipped=0, errors=[])
            await handler("scan", {"path": "/tmp/videos", "_job_id": "job-42"})

        calls = mock_manager.broadcast.call_args_list  # type: ignore[union-attr]
        # SCAN_STARTED + JOB_PROGRESS(complete) + SCAN_COMPLETED = 3
        assert len(calls) == 3
        assert calls[0][0][0]["type"] == EventType.SCAN_STARTED.value
        assert calls[1][0][0]["type"] == EventType.JOB_PROGRESS.value
        assert calls[1][0][0]["payload"]["status"] == "complete"
        assert calls[2][0][0]["type"] == EventType.SCAN_COMPLETED.value

    @pytest.mark.api
    async def test_job_progress_broadcast_payload_structure(self) -> None:
        """Verify JOB_PROGRESS events have correct payload with job_id, progress, status."""
        mock_manager = ConnectionManager()
        mock_manager.broadcast = AsyncMock()  # type: ignore[assignment]
        video_repo = AsyncInMemoryVideoRepository()
        job_queue = InMemoryJobQueue()

        handler = make_scan_handler(video_repo, ws_manager=mock_manager, queue=job_queue)

        from stoat_ferret.api.schemas.video import ScanResponse

        async def fake_scan(**kwargs: Any) -> ScanResponse:
            """Fake scan that invokes progress_callback to test broadcast wiring."""
            cb = kwargs.get("progress_callback")
            if cb:
                await cb(0.5)
                await cb(1.0)
            return ScanResponse(scanned=2, new=2, updated=0, skipped=0, errors=[])

        with patch(
            "stoat_ferret.api.services.scan.scan_directory",
            side_effect=fake_scan,
        ):
            await handler("scan", {"path": "/tmp/videos", "_job_id": "job-99"})

        # Find JOB_PROGRESS events among broadcasts
        progress_events = [
            c[0][0]
            for c in mock_manager.broadcast.call_args_list  # type: ignore[union-attr]
            if c[0][0]["type"] == EventType.JOB_PROGRESS.value
        ]
        # 2 running progress events + 1 complete event = 3
        assert len(progress_events) == 3
        for evt in progress_events:
            assert evt["payload"]["job_id"] == "job-99"
            assert "timestamp" in evt
        assert progress_events[0]["payload"]["progress"] == 0.5
        assert progress_events[0]["payload"]["status"] == "running"
        assert progress_events[1]["payload"]["progress"] == 1.0
        assert progress_events[1]["payload"]["status"] == "running"
        assert progress_events[2]["payload"]["progress"] == 1.0
        assert progress_events[2]["payload"]["status"] == "complete"

    @pytest.mark.api
    async def test_broadcast_events_use_build_event_structure(self) -> None:
        """Verify broadcast events follow build_event structure."""
        mock_manager = ConnectionManager()
        mock_manager.broadcast = AsyncMock()  # type: ignore[assignment]
        video_repo = AsyncInMemoryVideoRepository()

        handler = make_scan_handler(video_repo, ws_manager=mock_manager)

        with patch(
            "stoat_ferret.api.services.scan.scan_directory",
        ) as mock_scan:
            from stoat_ferret.api.schemas.video import ScanResponse

            mock_scan.return_value = ScanResponse(scanned=1, new=1, updated=0, skipped=0, errors=[])
            await handler("scan", {"path": "/tmp/videos"})

        for call in mock_manager.broadcast.call_args_list:  # type: ignore[union-attr]
            event = call[0][0]
            assert "type" in event
            assert "payload" in event
            assert "timestamp" in event
            assert isinstance(event["payload"], dict)
