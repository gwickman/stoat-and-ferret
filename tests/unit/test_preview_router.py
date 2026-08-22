# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for preview router InvalidTransitionError handling.

Verifies that seek_preview returns HTTP 409 Conflict with structured error
response when InvalidTransitionError is raised, instead of propagating to
Starlette as HTTP 500.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, PreviewQuality, PreviewSession, PreviewStatus, Video
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.proxy_repository import InMemoryProxyRepository
from stoat_ferret.db.timeline_repository import AsyncInMemoryTimelineRepository
from stoat_ferret.db.version_repository import AsyncInMemoryVersionRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue
from stoat_ferret.preview.manager import (
    InvalidTransitionError,
    PreviewManager,
)

_WHICH = "stoat_ferret.api.routers.preview.shutil.which"

_NOW = datetime(2026, 8, 22, 0, 0, 0, tzinfo=timezone.utc)


def _make_mock_preview_manager() -> MagicMock:
    """Create a mock PreviewManager with async seek method."""
    manager = MagicMock(spec=PreviewManager)
    manager.start = AsyncMock()
    manager.get_status = AsyncMock()
    manager.seek = AsyncMock()
    manager.stop = AsyncMock()
    return manager


@pytest.fixture
def mock_manager() -> MagicMock:
    """Mock PreviewManager."""
    return _make_mock_preview_manager()


@pytest.fixture
def preview_app(mock_manager: MagicMock) -> object:
    """FastAPI app with mock preview manager injected."""
    return create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        timeline_repository=AsyncInMemoryTimelineRepository(),
        version_repository=AsyncInMemoryVersionRepository(),
        batch_repository=None,
        proxy_repository=InMemoryProxyRepository(),
        job_queue=InMemoryJobQueue(),
        preview_manager=mock_manager,
    )


@pytest.fixture
def preview_app_with_seek_session(mock_manager: MagicMock) -> object:
    """FastAPI app seeded with a clip + session so seek endpoint reaches manager.seek().

    The seek endpoint (BL-798) re-fetches clips from the DB before calling
    manager.seek(). This fixture seeds one video + clip and configures
    mock_manager.get_status to return a session with a matching project_id,
    allowing tests to exercise the InvalidTransitionError path without hitting
    422 NO_PLACEABLE_CLIPS first.
    """
    video_repo = AsyncInMemoryVideoRepository()
    clip_repo = AsyncInMemoryClipRepository()

    video = Video(
        id="vid-router-test",
        path="/test/video.mp4",
        filename="video.mp4",
        duration_frames=60,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=640,
        height=360,
        video_codec="h264",
        file_size=100_000,
        created_at=_NOW,
        updated_at=_NOW,
        audio_codec=None,
    )
    clip = Clip(
        id="clip-router-test",
        project_id="test-project-1",
        source_video_id="vid-router-test",
        in_point=0,
        out_point=60,
        timeline_position=0,
        timeline_start=0.0,
        timeline_end=2.0,
        created_at=_NOW,
        updated_at=_NOW,
    )

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(video_repo.add(video))
        loop.run_until_complete(clip_repo.add(clip))
    finally:
        loop.close()

    mock_manager.get_status = AsyncMock(
        return_value=PreviewSession(
            id="test-session-id",
            project_id="test-project-1",
            status=PreviewStatus.READY,
            manifest_path=None,
            error_message=None,
            created_at=_NOW,
            updated_at=_NOW,
            expires_at=_NOW + timedelta(hours=1),
            quality_level=PreviewQuality.MEDIUM,
        )
    )

    return create_app(
        video_repository=video_repo,
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=clip_repo,
        timeline_repository=AsyncInMemoryTimelineRepository(),
        version_repository=AsyncInMemoryVersionRepository(),
        batch_repository=None,
        proxy_repository=InMemoryProxyRepository(),
        job_queue=InMemoryJobQueue(),
        preview_manager=mock_manager,
    )


class TestSeekPreviewInvalidTransition:
    """Tests for seek_preview handler — InvalidTransitionError path."""

    @patch(_WHICH, return_value="/usr/bin/ffmpeg")
    def test_invalid_transition_returns_409(
        self,
        _mock_which: MagicMock,
        preview_app_with_seek_session: object,
        mock_manager: MagicMock,
    ) -> None:
        """seek_preview returns 409 Conflict when seek raises InvalidTransitionError."""
        mock_manager.seek.side_effect = InvalidTransitionError(
            "invalid transition from error to seeking"
        )

        with TestClient(preview_app_with_seek_session) as client:
            response = client.post(
                "/api/v1/preview/test-session-id/seek",
                json={"position": 5.0},
            )

        assert response.status_code == 409

    @patch(_WHICH, return_value="/usr/bin/ffmpeg")
    def test_invalid_transition_response_has_code_and_message(
        self,
        _mock_which: MagicMock,
        preview_app_with_seek_session: object,
        mock_manager: MagicMock,
    ) -> None:
        """409 response detail contains code and message fields."""
        mock_manager.seek.side_effect = InvalidTransitionError(
            "invalid transition from error to seeking"
        )

        with TestClient(preview_app_with_seek_session) as client:
            response = client.post(
                "/api/v1/preview/test-session-id/seek",
                json={"position": 5.0},
            )

        detail = response.json()["detail"]
        assert detail["code"] == "INVALID_STATE_TRANSITION"
        assert "message" in detail

    @patch(_WHICH, return_value="/usr/bin/ffmpeg")
    def test_invalid_transition_message_does_not_expose_internals(
        self,
        _mock_which: MagicMock,
        preview_app_with_seek_session: object,
        mock_manager: MagicMock,
    ) -> None:
        """Error message does not leak state machine exception text."""
        mock_manager.seek.side_effect = InvalidTransitionError(
            "invalid transition from error to seeking"
        )

        with TestClient(preview_app_with_seek_session) as client:
            response = client.post(
                "/api/v1/preview/test-session-id/seek",
                json={"position": 5.0},
            )

        message = response.json()["detail"]["message"]
        assert "invalid transition from error to seeking" not in message
