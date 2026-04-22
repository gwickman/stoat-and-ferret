"""Smoke tests for synthetic monitoring background task (BL-269).

Confirms default behaviour (flag=false → no task, /metrics still served).
The smoke_client fixture does not set STOAT_SYNTHETIC_MONITORING=true,
so these tests exercise the disabled path. Enabled-path behaviour is
covered by ``tests/test_synthetic_monitoring.py`` which runs the
lifespan directly.
"""

from __future__ import annotations

import httpx


async def test_monitoring_disabled_by_default(smoke_client: httpx.AsyncClient) -> None:
    """With no STOAT_SYNTHETIC_MONITORING env, the app starts without a task."""
    transport: httpx.ASGITransport = smoke_client._transport  # type: ignore[assignment]
    app_state = transport.app.state  # type: ignore[union-attr]

    assert getattr(app_state, "synthetic_monitoring_task_handle", None) is None
    assert getattr(app_state, "synthetic_monitoring_client", None) is None


async def test_metrics_endpoint_available(smoke_client: httpx.AsyncClient) -> None:
    """GET /metrics is reachable even when synthetic monitoring is off.

    The Prometheus exposition endpoint is mounted as a sub-application,
    which issues a 307 to the trailing-slash form. Following redirects
    keeps the assertion honest while still exercising the same entry
    point an operator would probe.
    """
    resp = await smoke_client.get("/metrics", follow_redirects=True)
    assert resp.status_code == 200
    # The counter/histogram definitions register at import time, so they
    # appear in the exposition output even before any probe runs.
    body = resp.text
    assert "stoat_synthetic_check_total" in body
    assert "stoat_synthetic_check_duration_seconds" in body
