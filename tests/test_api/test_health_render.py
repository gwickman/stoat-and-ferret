"""Tests for render health check in /health/ready endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_WHICH = "stoat_ferret.api.routers.health.shutil.which"
_SUBPROC = "stoat_ferret.api.routers.health.subprocess.run"
_DISK = "stoat_ferret.api.routers.health.shutil.disk_usage"
_MKDIR = "stoat_ferret.api.routers.health.Path.mkdir"

_FFMPEG_OK = MagicMock(stdout="ffmpeg version 6.0 Copyright (c) 2000-2023\n")


def _make_disk_usage(used: int, total: int) -> MagicMock:
    """Create a mock disk usage result."""
    return MagicMock(used=used, total=total, free=total - used)


@pytest.mark.api
class TestRenderHealthComponent:
    """Tests for render component in /health/ready."""

    def test_render_component_present_in_health_response(self, client: TestClient) -> None:
        """Health response includes render component."""
        with (
            patch(_WHICH, return_value="/usr/bin/ffmpeg"),
            patch(_SUBPROC, return_value=_FFMPEG_OK),
        ):
            response = client.get("/health/ready")

        assert "render" in response.json()["checks"]

    def test_render_component_has_expected_fields(self, client: TestClient) -> None:
        """Render component has active_jobs, queue_depth, disk_usage_percent, encoder_available."""
        with (
            patch(_WHICH, return_value="/usr/bin/ffmpeg"),
            patch(_SUBPROC, return_value=_FFMPEG_OK),
        ):
            response = client.get("/health/ready")

        render = response.json()["checks"]["render"]
        assert "status" in render
        assert "active_jobs" in render
        assert "queue_depth" in render
        assert "disk_usage_percent" in render
        assert "encoder_available" in render

    def test_render_ok_when_no_queue_and_ffmpeg_available(self, client: TestClient) -> None:
        """Render reports ok when no render_queue is wired and FFmpeg is present."""
        with (
            patch(_WHICH, return_value="/usr/bin/ffmpeg"),
            patch(_SUBPROC, return_value=_FFMPEG_OK),
        ):
            response = client.get("/health/ready")

        render = response.json()["checks"]["render"]
        assert render["status"] == "ok"
        assert render["active_jobs"] == 0
        assert render["queue_depth"] == 0
        assert render["encoder_available"] is True


@pytest.mark.api
class TestRenderDegraded:
    """Tests for render degraded conditions."""

    def test_degraded_when_disk_exceeds_threshold(self, client: TestClient) -> None:
        """Render reports degraded when disk usage exceeds 90%."""
        mock_queue = AsyncMock()
        mock_queue.get_active_count = AsyncMock(return_value=1)
        mock_queue.get_queue_depth = AsyncMock(return_value=5)
        mock_queue._max_depth = 50
        client.app.state.render_queue = mock_queue  # type: ignore[union-attr]

        with (
            patch(_WHICH, return_value="/usr/bin/ffmpeg"),
            patch(_SUBPROC, return_value=_FFMPEG_OK),
            patch(_DISK, return_value=_make_disk_usage(950, 1000)),
            patch(_MKDIR),
        ):
            response = client.get("/health/ready")

        render = response.json()["checks"]["render"]
        assert render["status"] == "degraded"
        assert response.status_code == 200

        del client.app.state.render_queue  # type: ignore[union-attr]

    def test_degraded_when_queue_near_capacity(self, client: TestClient) -> None:
        """Render reports degraded when queue exceeds 80% of max_depth."""
        mock_queue = AsyncMock()
        mock_queue.get_active_count = AsyncMock(return_value=2)
        mock_queue.get_queue_depth = AsyncMock(return_value=42)  # 42/50 = 84% > 80%
        mock_queue._max_depth = 50
        client.app.state.render_queue = mock_queue  # type: ignore[union-attr]

        with (
            patch(_WHICH, return_value="/usr/bin/ffmpeg"),
            patch(_SUBPROC, return_value=_FFMPEG_OK),
            patch(_DISK, return_value=_make_disk_usage(400, 1000)),
            patch(_MKDIR),
        ):
            response = client.get("/health/ready")

        render = response.json()["checks"]["render"]
        assert render["status"] == "degraded"
        assert render["queue_depth"] == 42
        assert response.status_code == 200

        del client.app.state.render_queue  # type: ignore[union-attr]


@pytest.mark.api
class TestRenderUnavailable:
    """Tests for render unavailable when FFmpeg is missing."""

    def test_unavailable_when_ffmpeg_missing_no_queue(self, client: TestClient) -> None:
        """Render is unavailable when FFmpeg not found."""
        with patch(_WHICH, return_value=None):
            response = client.get("/health/ready")

        render = response.json()["checks"]["render"]
        assert render["status"] == "unavailable"
        assert render["encoder_available"] is False

    def test_unavailable_when_ffmpeg_missing_with_queue(self, client: TestClient) -> None:
        """Render is unavailable when FFmpeg not found, with queue wired."""
        mock_queue = AsyncMock()
        mock_queue.get_active_count = AsyncMock(return_value=0)
        mock_queue.get_queue_depth = AsyncMock(return_value=0)
        mock_queue._max_depth = 50
        client.app.state.render_queue = mock_queue  # type: ignore[union-attr]

        with (
            patch(_WHICH, return_value=None),
            patch(_SUBPROC, side_effect=FileNotFoundError("ffmpeg not found")),
            patch(_DISK, return_value=_make_disk_usage(400, 1000)),
            patch(_MKDIR),
        ):
            response = client.get("/health/ready")

        render = response.json()["checks"]["render"]
        assert render["status"] == "unavailable"
        assert render["encoder_available"] is False

        del client.app.state.render_queue  # type: ignore[union-attr]

    def test_render_unavailable_does_not_cause_503(self, client: TestClient) -> None:
        """Per LRN-136, render unavailable -> overall HTTP 200 when critical checks pass.

        Patch _check_render directly to isolate render unavailability from the
        critical FFmpeg check (both use shutil.which).
        """
        with (
            patch(_WHICH, return_value="/usr/bin/ffmpeg"),
            patch(_SUBPROC, return_value=_FFMPEG_OK),
            patch(
                "stoat_ferret.api.routers.health._check_render",
                return_value={
                    "status": "unavailable",
                    "active_jobs": 0,
                    "queue_depth": 0,
                    "disk_usage_percent": 0.0,
                    "encoder_available": False,
                },
            ),
        ):
            response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["checks"]["render"]["status"] == "unavailable"
        assert data["status"] in ("ok", "degraded")


@pytest.mark.api
class TestRenderNonBlocking:
    """Tests verifying render health check is non-blocking."""

    def test_no_subprocess_calls_in_render_check(self, client: TestClient) -> None:
        """Render health check uses shutil.which (PATH lookup), not subprocess.run."""
        mock_queue = AsyncMock()
        mock_queue.get_active_count = AsyncMock(return_value=0)
        mock_queue.get_queue_depth = AsyncMock(return_value=0)
        mock_queue._max_depth = 50
        client.app.state.render_queue = mock_queue  # type: ignore[union-attr]

        with (
            patch(_WHICH, return_value="/usr/bin/ffmpeg"),
            patch(_SUBPROC, return_value=_FFMPEG_OK),
            patch(_DISK, return_value=_make_disk_usage(400, 1000)),
            patch(_MKDIR),
        ):
            response = client.get("/health/ready")

        # The render check uses shutil.which (PATH lookup) and shutil.disk_usage,
        # not subprocess.run — it reads cached/filesystem state only.
        assert response.status_code == 200
        render = response.json()["checks"]["render"]
        assert render["status"] == "ok"

        del client.app.state.render_queue  # type: ignore[union-attr]


@pytest.mark.api
class TestRenderParity:
    """Render health follows same degraded-but-healthy pattern as preview/proxy."""

    def test_render_degraded_returns_http_200(self, client: TestClient) -> None:
        """Like preview/proxy, render degraded -> HTTP 200 not 503."""
        mock_queue = AsyncMock()
        mock_queue.get_active_count = AsyncMock(return_value=1)
        mock_queue.get_queue_depth = AsyncMock(return_value=45)  # 90% > 80%
        mock_queue._max_depth = 50
        client.app.state.render_queue = mock_queue  # type: ignore[union-attr]

        with (
            patch(_WHICH, return_value="/usr/bin/ffmpeg"),
            patch(_SUBPROC, return_value=_FFMPEG_OK),
            patch(_DISK, return_value=_make_disk_usage(400, 1000)),
            patch(_MKDIR),
        ):
            response = client.get("/health/ready")

        assert response.status_code == 200
        render = response.json()["checks"]["render"]
        assert render["status"] == "degraded"

        del client.app.state.render_queue  # type: ignore[union-attr]

    def test_render_response_structure_matches_pattern(self, client: TestClient) -> None:
        """Render response has status and detail fields like preview/proxy."""
        with (
            patch(_WHICH, return_value="/usr/bin/ffmpeg"),
            patch(_SUBPROC, return_value=_FFMPEG_OK),
        ):
            response = client.get("/health/ready")

        data = response.json()

        # All non-critical checks have "status" field
        for component in ("preview", "proxy", "render"):
            assert "status" in data["checks"][component]

        # Render has its specific detail fields
        render = data["checks"]["render"]
        assert "active_jobs" in render
        assert "queue_depth" in render
        assert "disk_usage_percent" in render
        assert "encoder_available" in render

    def test_render_included_alongside_existing_components(self, client: TestClient) -> None:
        """Render appears alongside database, ffmpeg, preview, proxy."""
        with (
            patch(_WHICH, return_value="/usr/bin/ffmpeg"),
            patch(_SUBPROC, return_value=_FFMPEG_OK),
        ):
            response = client.get("/health/ready")

        checks = response.json()["checks"]
        expected = {"database", "ffmpeg", "preview", "proxy", "render", "rust_core", "filesystem"}
        assert set(checks.keys()) == expected
