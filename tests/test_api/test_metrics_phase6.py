"""Verify the seven Phase 6 metrics are exposed at GET /metrics (BL-288).

These are *contract* checks for FR-003 / NFR-002. Latency benchmarks live
under ``tests/benchmarks/`` and are excluded from default CI; this module
runs in the regular suite to keep the metric vocabulary stable.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

PHASE6_METRIC_NAMES = (
    "stoat_seed_duration_seconds",
    "stoat_system_state_duration_seconds",
    "stoat_ws_buffer_size",
    "stoat_ws_connected_clients",
    "stoat_active_jobs_count",
    "stoat_feature_flag_state",
    "stoat_migration_duration_seconds",
)


@pytest.mark.api
def test_phase6_metrics_registered_at_metrics_endpoint(client: TestClient) -> None:
    """All seven Phase 6 metrics appear in the /metrics scrape (FR-003).

    The metrics middleware registers Counter/Histogram/Gauge instruments
    at module import time. This test asserts each instrument is present
    in the Prometheus exposition by name — even before any value has
    been observed, the HELP/TYPE preamble is emitted, so a metric that
    is registered but never updated still shows up.
    """
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    missing = [name for name in PHASE6_METRIC_NAMES if name not in body]
    assert not missing, f"Missing Phase 6 metrics from /metrics: {missing}"


@pytest.mark.api
def test_system_state_metric_emitted_after_endpoint_call(client: TestClient) -> None:
    """Calling GET /api/v1/system/state increments the Phase 6 histogram.

    Verifies the instrumentation is wired (not just registered): after
    one call, the histogram's _count series for the endpoint must
    appear with a non-zero value.
    """
    client.get("/api/v1/system/state")
    response = client.get("/metrics")
    body = response.text
    # The Histogram emits a `_count` line; a fresh registry would show 0,
    # but after one call it should be >= 1.
    count_line = next(
        (
            line
            for line in body.splitlines()
            if line.startswith("stoat_system_state_duration_seconds_count")
        ),
        None,
    )
    assert count_line is not None, "stoat_system_state_duration_seconds_count not exposed"
    value = float(count_line.rsplit(" ", 1)[-1])
    assert value >= 1.0, f"Expected count >=1 after one call, got {value} (line: {count_line!r})"


@pytest.mark.api
def test_feature_flag_gauge_populated_after_flags_endpoint(client: TestClient) -> None:
    """GET /api/v1/flags refreshes the stoat_feature_flag_state gauge.

    The handler updates one labelled gauge sample per flag on every
    call. After one request, every flag name from FEATURE_FLAG_NAMES
    should appear as a labelled time series.
    """
    client.get("/api/v1/flags")
    response = client.get("/metrics")
    body = response.text
    for flag in ("testing_mode", "seed_endpoint", "synthetic_monitoring", "batch_rendering"):
        needle = f'stoat_feature_flag_state{{flag="{flag}"}}'
        assert needle in body, f"Gauge sample missing for flag={flag!r}"
