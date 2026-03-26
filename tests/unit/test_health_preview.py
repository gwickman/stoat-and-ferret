"""Tests for preview and proxy health check functions.

Verifies _check_preview() and _check_proxy() return correct structure,
degraded status semantics, and overall health status logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.routers.health import (
    _CACHE_DEGRADED_THRESHOLD,
    _check_preview,
    _check_proxy,
)


@dataclass
class FakeCacheStatus:
    """Minimal CacheStatus stand-in for testing."""

    used_bytes: int
    max_bytes: int
    usage_percent: float
    active_sessions: list[str] = field(default_factory=list)


def _make_request(
    *,
    preview_cache: object | None = None,
    proxy_service: object | None = None,
    proxy_repository: object | None = None,
) -> MagicMock:
    """Build a mock Request with app.state attributes."""
    request = MagicMock()
    request.app.state.preview_cache = preview_cache
    request.app.state.proxy_service = proxy_service
    request.app.state.proxy_repository = proxy_repository
    return request


# ---------------------------------------------------------------------------
# _check_preview tests
# ---------------------------------------------------------------------------


class TestCheckPreview:
    """Tests for _check_preview() health check function."""

    async def test_returns_ok_when_no_preview_cache(self) -> None:
        """When preview_cache is not on app.state, return ok defaults."""
        request = _make_request(preview_cache=None)
        result = await _check_preview(request)

        assert result["status"] == "ok"
        assert result["active_sessions"] == 0
        assert result["cache_usage_percent"] == 0.0
        assert result["cache_healthy"] is True

    async def test_returns_ok_when_cache_below_threshold(self) -> None:
        """Cache under 90% reports ok."""
        cache = AsyncMock()
        cache.status.return_value = FakeCacheStatus(
            used_bytes=100,
            max_bytes=1000,
            usage_percent=10.0,
            active_sessions=["sess-1"],
        )
        request = _make_request(preview_cache=cache)
        result = await _check_preview(request)

        assert result["status"] == "ok"
        assert result["active_sessions"] == 1
        assert result["cache_usage_percent"] == 10.0
        assert result["cache_healthy"] is True

    async def test_returns_degraded_when_cache_above_threshold(self) -> None:
        """Cache over 90% reports degraded."""
        cache = AsyncMock()
        cache.status.return_value = FakeCacheStatus(
            used_bytes=950,
            max_bytes=1000,
            usage_percent=95.0,
            active_sessions=["s1", "s2"],
        )
        request = _make_request(preview_cache=cache)
        result = await _check_preview(request)

        assert result["status"] == "degraded"
        assert result["active_sessions"] == 2
        assert result["cache_usage_percent"] == 95.0
        assert result["cache_healthy"] is False

    async def test_returns_ok_at_exactly_threshold(self) -> None:
        """Cache at exactly 90% is still ok (threshold is >90%)."""
        cache = AsyncMock()
        cache.status.return_value = FakeCacheStatus(
            used_bytes=900,
            max_bytes=1000,
            usage_percent=_CACHE_DEGRADED_THRESHOLD,
            active_sessions=[],
        )
        request = _make_request(preview_cache=cache)
        result = await _check_preview(request)

        assert result["status"] == "ok"
        assert result["cache_healthy"] is True

    async def test_returns_degraded_on_exception(self) -> None:
        """Exception in cache status reports degraded with error."""
        cache = AsyncMock()
        cache.status.side_effect = RuntimeError("cache broken")
        request = _make_request(preview_cache=cache)
        result = await _check_preview(request)

        assert result["status"] == "degraded"
        assert "cache broken" in result["error"]

    async def test_response_structure(self) -> None:
        """Verify all required fields are present."""
        cache = AsyncMock()
        cache.status.return_value = FakeCacheStatus(
            used_bytes=0,
            max_bytes=1000,
            usage_percent=0.0,
            active_sessions=[],
        )
        request = _make_request(preview_cache=cache)
        result = await _check_preview(request)

        assert "status" in result
        assert "active_sessions" in result
        assert "cache_usage_percent" in result
        assert "cache_healthy" in result


# ---------------------------------------------------------------------------
# _check_proxy tests
# ---------------------------------------------------------------------------


class TestCheckProxy:
    """Tests for _check_proxy() health check function."""

    async def test_returns_ok_when_no_proxy_service(self) -> None:
        """When proxy_service is not on app.state, return ok defaults."""
        request = _make_request(proxy_service=None)
        result = await _check_proxy(request)

        assert result["status"] == "ok"
        assert result["proxy_dir_writable"] is True
        assert result["pending_proxies"] == 0

    async def test_returns_ok_when_dir_writable(self) -> None:
        """Writable proxy dir with zero pending reports ok."""
        proxy_svc = MagicMock()
        proxy_svc._proxy_dir = "/tmp/test-proxies"

        proxy_repo = AsyncMock()
        proxy_repo.count_by_status.return_value = 0

        request = _make_request(proxy_service=proxy_svc, proxy_repository=proxy_repo)

        with (
            patch("stoat_ferret.api.routers.health.os.path.isdir", return_value=True),
            patch("stoat_ferret.api.routers.health.os.access", return_value=True),
        ):
            result = await _check_proxy(request)

        assert result["status"] == "ok"
        assert result["proxy_dir_writable"] is True
        assert result["pending_proxies"] == 0

    async def test_returns_degraded_when_dir_not_writable(self) -> None:
        """Non-writable proxy dir reports degraded."""
        proxy_svc = MagicMock()
        proxy_svc._proxy_dir = "/nonexistent"

        proxy_repo = AsyncMock()
        proxy_repo.count_by_status.return_value = 0

        request = _make_request(proxy_service=proxy_svc, proxy_repository=proxy_repo)

        with patch("stoat_ferret.api.routers.health.os.path.isdir", return_value=False):
            result = await _check_proxy(request)

        assert result["status"] == "degraded"
        assert result["proxy_dir_writable"] is False

    async def test_counts_pending_and_generating(self) -> None:
        """Pending proxies is sum of PENDING + GENERATING statuses."""
        from stoat_ferret.db.models import ProxyStatus

        proxy_svc = MagicMock()
        proxy_svc._proxy_dir = "/tmp/proxies"

        proxy_repo = AsyncMock()
        proxy_repo.count_by_status.side_effect = lambda s: {
            ProxyStatus.PENDING: 2,
            ProxyStatus.GENERATING: 3,
        }[s]

        request = _make_request(proxy_service=proxy_svc, proxy_repository=proxy_repo)

        with (
            patch("stoat_ferret.api.routers.health.os.path.isdir", return_value=True),
            patch("stoat_ferret.api.routers.health.os.access", return_value=True),
        ):
            result = await _check_proxy(request)

        assert result["pending_proxies"] == 5

    async def test_returns_degraded_on_exception(self) -> None:
        """Exception in proxy check reports degraded with error."""
        proxy_svc = MagicMock()
        proxy_svc._proxy_dir = property(lambda s: (_ for _ in ()).throw(RuntimeError("fail")))

        request = _make_request(proxy_service=proxy_svc)

        # Force an exception by making _proxy_dir access raise
        type(proxy_svc)._proxy_dir = property(lambda s: (_ for _ in ()).throw(RuntimeError("fail")))
        result = await _check_proxy(request)

        assert result["status"] == "degraded"
        assert "error" in result

    async def test_response_structure(self) -> None:
        """Verify all required fields are present."""
        proxy_svc = MagicMock()
        proxy_svc._proxy_dir = "/tmp/proxies"

        proxy_repo = AsyncMock()
        proxy_repo.count_by_status.return_value = 0

        request = _make_request(proxy_service=proxy_svc, proxy_repository=proxy_repo)

        with (
            patch("stoat_ferret.api.routers.health.os.path.isdir", return_value=True),
            patch("stoat_ferret.api.routers.health.os.access", return_value=True),
        ):
            result = await _check_proxy(request)

        assert "status" in result
        assert "proxy_dir_writable" in result
        assert "pending_proxies" in result


# ---------------------------------------------------------------------------
# Readiness endpoint integration tests
# ---------------------------------------------------------------------------


class TestReadinessWithPreviewProxy:
    """Tests for /health/ready endpoint including preview and proxy checks."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client with injected dependencies."""
        app = create_app()
        app.state._deps_injected = True
        with TestClient(app) as c:
            yield c

    def test_readiness_includes_preview_and_proxy_keys(self, client: TestClient) -> None:
        """Response contains preview and proxy check keys."""
        with (
            patch("stoat_ferret.api.routers.health.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("stoat_ferret.api.routers.health.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="ffmpeg version 6.0\n")
            response = client.get("/health/ready")

        data = response.json()
        assert "preview" in data["checks"]
        assert "proxy" in data["checks"]

    def test_overall_degraded_not_unhealthy_when_preview_degraded(
        self,
        client: TestClient,
    ) -> None:
        """Overall status is degraded (not unhealthy) when preview cache is high."""
        # Inject a mock preview_cache that reports high usage
        mock_cache = AsyncMock()
        mock_cache.status.return_value = FakeCacheStatus(
            used_bytes=950,
            max_bytes=1000,
            usage_percent=95.0,
            active_sessions=["s1"],
        )
        client.app.state.preview_cache = mock_cache  # type: ignore[union-attr]

        with (
            patch("stoat_ferret.api.routers.health.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("stoat_ferret.api.routers.health.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="ffmpeg version 6.0\n")
            response = client.get("/health/ready")

        assert response.status_code == 200  # Not 503!
        data = response.json()
        assert data["status"] == "degraded"
        assert data["checks"]["preview"]["status"] == "degraded"

        # Clean up
        del client.app.state.preview_cache  # type: ignore[union-attr]

    def test_overall_ok_when_all_healthy(self, client: TestClient) -> None:
        """Overall status is ok when all checks pass."""
        with (
            patch("stoat_ferret.api.routers.health.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("stoat_ferret.api.routers.health.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="ffmpeg version 6.0\n")
            response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_503_when_critical_fails_even_with_preview_ok(
        self,
        client: TestClient,
    ) -> None:
        """Database failure causes 503 regardless of preview/proxy status."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("DB down")
        client.app.state.db = mock_db  # type: ignore[union-attr]

        with (
            patch("stoat_ferret.api.routers.health.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("stoat_ferret.api.routers.health.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="ffmpeg version 6.0\n")
            response = client.get("/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"

        del client.app.state.db  # type: ignore[union-attr]

    def test_readiness_response_preserves_existing_keys(
        self,
        client: TestClient,
    ) -> None:
        """Existing database and ffmpeg check keys are still present."""
        with (
            patch("stoat_ferret.api.routers.health.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("stoat_ferret.api.routers.health.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="ffmpeg version 6.0\n")
            response = client.get("/health/ready")

        data = response.json()
        assert "database" in data["checks"]
        assert "ffmpeg" in data["checks"]
        assert "preview" in data["checks"]
        assert "proxy" in data["checks"]
