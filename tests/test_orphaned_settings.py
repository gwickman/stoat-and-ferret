"""Tests for wiring orphaned settings (debug, ws_heartbeat_interval) to consumers."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.settings import get_settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue


def _make_test_app() -> FastAPI:
    """Create a test app with in-memory dependencies."""
    return create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        job_queue=InMemoryJobQueue(),
    )


class TestDebugModeFastAPI:
    """Tests for settings.debug controlling FastAPI debug mode."""

    def test_debug_false_by_default(self) -> None:
        """FastAPI app created with debug=False when settings.debug=False (default)."""
        get_settings.cache_clear()
        app = _make_test_app()
        assert app.debug is False

    def test_debug_true_from_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """FastAPI app created with debug=True when settings.debug=True."""
        monkeypatch.setenv("STOAT_DEBUG", "true")
        get_settings.cache_clear()
        app = _make_test_app()
        assert app.debug is True

    def test_debug_env_controls_app(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """STOAT_DEBUG=true enables FastAPI debug mode (system test)."""
        monkeypatch.setenv("STOAT_DEBUG", "true")
        get_settings.cache_clear()
        app = _make_test_app()
        assert app.debug is True

        # Verify env var controls the setting
        monkeypatch.setenv("STOAT_DEBUG", "false")
        get_settings.cache_clear()
        app = _make_test_app()
        assert app.debug is False


class TestHeartbeatInterval:
    """Tests for settings.ws_heartbeat_interval controlling WebSocket heartbeat."""

    @pytest.fixture
    def ws_manager(self) -> ConnectionManager:
        """Create a ConnectionManager for testing."""
        return ConnectionManager()

    @pytest.fixture
    def ws_app(self, ws_manager: ConnectionManager) -> FastAPI:
        """Create test app with WebSocket manager injected."""
        return create_app(
            video_repository=AsyncInMemoryVideoRepository(),
            project_repository=AsyncInMemoryProjectRepository(),
            clip_repository=AsyncInMemoryClipRepository(),
            job_queue=InMemoryJobQueue(),
            ws_manager=ws_manager,
        )

    @pytest.fixture
    def ws_client(self, ws_app: FastAPI) -> Generator[TestClient, None, None]:
        """Create test client for WebSocket testing."""
        with TestClient(ws_app) as c:
            yield c

    def test_heartbeat_reads_from_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ws.py reads ws_heartbeat_interval from settings instead of constant."""
        monkeypatch.setenv("STOAT_WS_HEARTBEAT_INTERVAL", "15")
        get_settings.cache_clear()

        settings = get_settings()
        assert settings.ws_heartbeat_interval == 15

    def test_default_heartbeat_constant_removed(self) -> None:
        """DEFAULT_HEARTBEAT_INTERVAL constant is no longer defined in ws.py."""
        from stoat_ferret.api.routers import ws

        assert not hasattr(ws, "DEFAULT_HEARTBEAT_INTERVAL")

    def test_heartbeat_uses_settings_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """WebSocket endpoint uses settings.ws_heartbeat_interval for heartbeat loop."""
        monkeypatch.setenv("STOAT_WS_HEARTBEAT_INTERVAL", "42")
        get_settings.cache_clear()

        with patch("stoat_ferret.api.routers.ws._heartbeat_loop") as mock_loop:
            # Make the mock return a coroutine so create_task works
            import asyncio

            mock_loop.return_value = asyncio.Future()
            mock_loop.return_value.set_result(None)

            ws_manager = ConnectionManager()
            app = create_app(
                video_repository=AsyncInMemoryVideoRepository(),
                project_repository=AsyncInMemoryProjectRepository(),
                clip_repository=AsyncInMemoryClipRepository(),
                job_queue=InMemoryJobQueue(),
                ws_manager=ws_manager,
            )

            with TestClient(app) as client, client.websocket_connect("/ws"):
                # The heartbeat loop should have been called with interval=42
                mock_loop.assert_called_once()
                assert mock_loop.call_args[0][1] == 42
