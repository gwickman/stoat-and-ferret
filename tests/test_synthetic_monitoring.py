"""Tests for synthetic monitoring background task (BL-269).

Exercises :class:`SyntheticMonitoringTask` response mapping, metric
emission, error handling, cancellation, and lifespan gating. Uses
:class:`httpx.MockTransport` to avoid binding a real port, and
``prometheus_client.REGISTRY.get_sample_value`` to assert on metric
deltas.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from prometheus_client import REGISTRY

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.api.services.metrics import (
    SYNTHETIC_CHECK_DURATION_SECONDS,
    SYNTHETIC_CHECK_TOTAL,
)
from stoat_ferret.api.services.synthetic_monitoring import (
    HEALTH_READY_PATH,
    SYSTEM_STATE_PATH,
    VERSION_PATH,
    CheckResult,
    SyntheticMonitoringTask,
)
from stoat_ferret.api.settings import get_settings

CHECK_NAMES: tuple[str, ...] = ("health_ready", "version", "system_state")


def _counter_value(check_name: str, status: str) -> float:
    """Return current value of stoat_synthetic_check_total for labels."""
    val = REGISTRY.get_sample_value(
        "stoat_synthetic_check_total",
        {"check_name": check_name, "status": status},
    )
    return val if val is not None else 0.0


def _histogram_count(check_name: str) -> float:
    """Return sample count for stoat_synthetic_check_duration_seconds."""
    val = REGISTRY.get_sample_value(
        "stoat_synthetic_check_duration_seconds_count",
        {"check_name": check_name},
    )
    return val if val is not None else 0.0


def _mock_client(handler: httpx.MockTransport | object) -> httpx.AsyncClient:
    """Build an AsyncClient backed by a MockTransport handler."""
    if isinstance(handler, httpx.MockTransport):
        transport = handler
    else:
        transport = httpx.MockTransport(handler)  # type: ignore[arg-type]
    # NOSONAR: MockTransport is in-process, no network I/O.
    return httpx.AsyncClient(transport=transport, base_url="http://test")  # NOSONAR


# ---------------------------------------------------------------------------
# Stage 1: Metric definition
# ---------------------------------------------------------------------------


def test_metrics_registered() -> None:
    """Prometheus metrics expose the documented counter and histogram."""
    assert SYNTHETIC_CHECK_TOTAL is not None
    assert SYNTHETIC_CHECK_DURATION_SECONDS is not None
    # Touching labels with every combination keeps label cardinality
    # bounded at 18 (3 checks x 6 statuses) as designed.
    SYNTHETIC_CHECK_TOTAL.labels(check_name="health_ready", status="success").inc(0)
    SYNTHETIC_CHECK_DURATION_SECONDS.labels(check_name="health_ready").observe(0.0)
    assert _counter_value("health_ready", "success") >= 0


# ---------------------------------------------------------------------------
# Stage 3: Response mapping
# ---------------------------------------------------------------------------


async def test_health_check_emits_success_metric() -> None:
    """HTTP 200 on /health/ready maps to status='success'."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == HEALTH_READY_PATH
        return httpx.Response(200, json={"ready": True})

    before = _counter_value("health_ready", "success")
    async with _mock_client(handler) as client:
        task = SyntheticMonitoringTask(client=client, interval_seconds=1)
        result = await task.check_health_ready()

    assert isinstance(result, CheckResult)
    assert result.status == "success"
    assert result.check_name == "health_ready"
    assert _counter_value("health_ready", "success") == before + 1


async def test_health_check_maps_503_to_degraded() -> None:
    """HTTP 503 on /health/ready maps to status='degraded', not 'failure'."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"ready": False})

    before_degraded = _counter_value("health_ready", "degraded")
    before_failure = _counter_value("health_ready", "failure")
    async with _mock_client(handler) as client:
        task = SyntheticMonitoringTask(client=client, interval_seconds=1)
        result = await task.check_health_ready()

    assert result.status == "degraded"
    assert _counter_value("health_ready", "degraded") == before_degraded + 1
    # Explicitly assert the failure counter is untouched — the 503 mapping
    # exists so known-degraded states do not page operators.
    assert _counter_value("health_ready", "failure") == before_failure


async def test_system_state_check_handles_404() -> None:
    """HTTP 404 on /api/v1/system/state maps to status='not_implemented'."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == SYSTEM_STATE_PATH
        return httpx.Response(404)

    before = _counter_value("system_state", "not_implemented")
    async with _mock_client(handler) as client:
        task = SyntheticMonitoringTask(client=client, interval_seconds=1)
        result = await task.check_system_state()

    assert result.status == "not_implemented"
    assert _counter_value("system_state", "not_implemented") == before + 1


async def test_version_check_emits_success_on_200() -> None:
    """HTTP 200 on /api/v1/version maps to status='success'."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == VERSION_PATH
        return httpx.Response(200, json={"app_version": "0.3.0"})

    before = _counter_value("version", "success")
    async with _mock_client(handler) as client:
        task = SyntheticMonitoringTask(client=client, interval_seconds=1)
        result = await task.check_version()

    assert result.status == "success"
    assert _counter_value("version", "success") == before + 1


async def test_unexpected_500_maps_to_failure() -> None:
    """HTTP 500 (no degraded mapping) maps to status='failure'."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    before = _counter_value("version", "failure")
    async with _mock_client(handler) as client:
        task = SyntheticMonitoringTask(client=client, interval_seconds=1)
        result = await task.check_version()

    assert result.status == "failure"
    assert _counter_value("version", "failure") == before + 1


# ---------------------------------------------------------------------------
# Stage 3: Error + timeout handling
# ---------------------------------------------------------------------------


async def test_check_handles_timeout() -> None:
    """asyncio.TimeoutError from wait_for maps to status='timeout'."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=asyncio.TimeoutError)

    before = _counter_value("health_ready", "timeout")
    task = SyntheticMonitoringTask(client=client, interval_seconds=1, timeout_seconds=0.01)
    result = await task.check_health_ready()

    assert result.status == "timeout"
    assert _counter_value("health_ready", "timeout") == before + 1


async def test_check_handles_connection_error() -> None:
    """httpx.ConnectError maps to status='error' with warning log."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    before = _counter_value("version", "error")
    async with _mock_client(handler) as client:
        task = SyntheticMonitoringTask(client=client, interval_seconds=1)
        result = await task.check_version()

    assert result.status == "error"
    assert _counter_value("version", "error") == before + 1


async def test_check_handles_unexpected_exception() -> None:
    """Unexpected exceptions still map to status='error' (task stays alive)."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=RuntimeError("boom"))

    before = _counter_value("version", "error")
    task = SyntheticMonitoringTask(client=client, interval_seconds=1)
    result = await task.check_version()

    assert result.status == "error"
    assert _counter_value("version", "error") == before + 1


# ---------------------------------------------------------------------------
# Task lifecycle and cancellation
# ---------------------------------------------------------------------------


async def test_monitoring_task_cancelled_on_shutdown() -> None:
    """Cancelling the run() task propagates CancelledError cleanly."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    async with _mock_client(handler) as client:
        task = SyntheticMonitoringTask(client=client, interval_seconds=60)
        handle = asyncio.create_task(task.run())
        # Let the loop start (one scheduling round is enough for the
        # first probe cycle to begin).
        await asyncio.sleep(0.05)
        handle.cancel()
        with pytest.raises(asyncio.CancelledError):
            await handle


# ---------------------------------------------------------------------------
# Parity: all three checks emit metrics, all handle timeouts identically
# ---------------------------------------------------------------------------


async def test_all_checks_emit_metrics() -> None:
    """All three checks emit counter + histogram samples per probe."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    before_counters = {name: _counter_value(name, "success") for name in CHECK_NAMES}
    before_hist = {name: _histogram_count(name) for name in CHECK_NAMES}

    async with _mock_client(handler) as client:
        task = SyntheticMonitoringTask(client=client, interval_seconds=1)
        await task.check_health_ready()
        await task.check_version()
        await task.check_system_state()

    for name in CHECK_NAMES:
        assert _counter_value(name, "success") == before_counters[name] + 1, name
        assert _histogram_count(name) == before_hist[name] + 1, name


async def test_all_checks_handle_timeout() -> None:
    """All three checks map asyncio.TimeoutError to status='timeout'."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=asyncio.TimeoutError)

    before = {name: _counter_value(name, "timeout") for name in CHECK_NAMES}
    task = SyntheticMonitoringTask(client=client, interval_seconds=1, timeout_seconds=0.01)
    await task.check_health_ready()
    await task.check_version()
    await task.check_system_state()

    for name in CHECK_NAMES:
        assert _counter_value(name, "timeout") == before[name] + 1, name


# ---------------------------------------------------------------------------
# Integration: continuous execution with a tight interval
# ---------------------------------------------------------------------------


async def test_monitoring_task_continuous_execution() -> None:
    """With interval=0.05s, the loop completes multiple cycles per second."""

    call_counts: dict[str, int] = {
        HEALTH_READY_PATH: 0,
        VERSION_PATH: 0,
        SYSTEM_STATE_PATH: 0,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        call_counts[path] = call_counts.get(path, 0) + 1
        # Return heterogeneous responses so all three mapping branches
        # exercise during the loop.
        if path == SYSTEM_STATE_PATH:
            return httpx.Response(404)
        return httpx.Response(200, json={})

    async with _mock_client(handler) as client:
        # timeout_seconds=0.1 keeps each probe fast; on Python 3.10 macOS,
        # asyncio.wait_for cancellation can stall up to timeout_seconds per
        # probe if the outer task cancel doesn't propagate immediately.
        task = SyntheticMonitoringTask(client=client, interval_seconds=0.05, timeout_seconds=0.1)
        handle = asyncio.create_task(task.run())
        # Allow a handful of cycles to run then shut down.
        await asyncio.sleep(0.25)
        handle.cancel()
        with pytest.raises(asyncio.CancelledError):
            await handle

    assert call_counts[HEALTH_READY_PATH] >= 2
    assert call_counts[VERSION_PATH] >= 2
    assert call_counts[SYSTEM_STATE_PATH] >= 2


# ---------------------------------------------------------------------------
# Lifespan gating: flag=false means no task, flag=true means task running
# ---------------------------------------------------------------------------


@pytest.fixture
def _isolated_env(tmp_path: Path) -> Generator[None, None, None]:
    """Point Settings at an isolated SQLite + thumbnails path for the test."""
    saved: dict[str, str] = {}
    for name in (
        "STOAT_DATABASE_PATH",
        "STOAT_THUMBNAIL_DIR",
        "STOAT_SYNTHETIC_MONITORING",
        "STOAT_SYNTHETIC_MONITORING_INTERVAL_SECONDS",
    ):
        if name in os.environ:
            saved[name] = os.environ.pop(name)
    os.environ["STOAT_DATABASE_PATH"] = str(tmp_path / "synth.db")
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")
    get_settings.cache_clear()
    try:
        yield
    finally:
        for name in (
            "STOAT_DATABASE_PATH",
            "STOAT_THUMBNAIL_DIR",
            "STOAT_SYNTHETIC_MONITORING",
            "STOAT_SYNTHETIC_MONITORING_INTERVAL_SECONDS",
        ):
            os.environ.pop(name, None)
        for name, value in saved.items():
            os.environ[name] = value
        get_settings.cache_clear()


async def test_monitoring_does_not_start_when_flag_false(
    _isolated_env: None,
) -> None:
    """STOAT_SYNTHETIC_MONITORING=false (default) creates no task."""
    os.environ["STOAT_SYNTHETIC_MONITORING"] = "false"
    get_settings.cache_clear()

    app = create_app()
    async with lifespan(app):
        assert getattr(app.state, "synthetic_monitoring_task_handle", None) is None
        assert getattr(app.state, "synthetic_monitoring_client", None) is None


async def test_monitoring_starts_when_flag_true(
    _isolated_env: None,
) -> None:
    """STOAT_SYNTHETIC_MONITORING=true creates the asyncio task and client."""
    os.environ["STOAT_SYNTHETIC_MONITORING"] = "true"
    os.environ["STOAT_SYNTHETIC_MONITORING_INTERVAL_SECONDS"] = "60"
    get_settings.cache_clear()

    app = create_app()
    async with lifespan(app):
        handle = getattr(app.state, "synthetic_monitoring_task_handle", None)
        client = getattr(app.state, "synthetic_monitoring_client", None)
        assert handle is not None
        assert client is not None
        assert not handle.done()

    # After lifespan exit the task handle should be cancelled/finalised.
    assert handle is not None and handle.done()
