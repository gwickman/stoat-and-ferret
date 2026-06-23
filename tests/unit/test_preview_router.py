# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for preview router InvalidTransitionError handling.

Verifies that seek_preview returns HTTP 409 Conflict with structured error
response when InvalidTransitionError is raised, instead of propagating to
Starlette as HTTP 500.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
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


class TestSeekPreviewInvalidTransition:
    """Tests for seek_preview handler — InvalidTransitionError path."""

    @patch(_WHICH, return_value="/usr/bin/ffmpeg")
    def test_invalid_transition_returns_409(
        self,
        _mock_which: MagicMock,
        preview_app: object,
        mock_manager: MagicMock,
    ) -> None:
        """seek_preview returns 409 Conflict when seek raises InvalidTransitionError."""
        mock_manager.seek.side_effect = InvalidTransitionError(
            "invalid transition from error to seeking"
        )

        with TestClient(preview_app) as client:
            response = client.post(
                "/api/v1/preview/test-session-id/seek",
                json={"position": 5.0},
            )

        assert response.status_code == 409

    @patch(_WHICH, return_value="/usr/bin/ffmpeg")
    def test_invalid_transition_response_has_code_and_message(
        self,
        _mock_which: MagicMock,
        preview_app: object,
        mock_manager: MagicMock,
    ) -> None:
        """409 response detail contains code and message fields."""
        mock_manager.seek.side_effect = InvalidTransitionError(
            "invalid transition from error to seeking"
        )

        with TestClient(preview_app) as client:
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
        preview_app: object,
        mock_manager: MagicMock,
    ) -> None:
        """Error message does not leak state machine exception text."""
        mock_manager.seek.side_effect = InvalidTransitionError(
            "invalid transition from error to seeking"
        )

        with TestClient(preview_app) as client:
            response = client.post(
                "/api/v1/preview/test-session-id/seek",
                json={"position": 5.0},
            )

        message = response.json()["detail"]["message"]
        assert "invalid transition from error to seeking" not in message
