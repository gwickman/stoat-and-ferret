"""API latency benchmarks (BL-288, FR-001 / FR-005).

These benchmarks call live FastAPI handlers via :class:`TestClient` (no
mocks, per LRN-250 / NFR-003) and assert against the targets in
``docs/benchmarks/baseline.md``:

- ``GET /api/v1/system/state`` with 100 seeded projects: mean < 500ms.
- ``GET /api/v1/version``: P99 < 100ms.

Run with::

    uv run pytest tests/benchmarks/test_api_latency.py --benchmark-only --no-cov -v

The ``benchmark`` marker keeps these tests out of the default suite
(``addopts = --ignore=tests/benchmarks`` in ``pyproject.toml``).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# Targets — keep in sync with docs/benchmarks/baseline.md and the
# acceptance criteria in BL-288.
SYSTEM_STATE_MEAN_TARGET_S = 0.500
VERSION_P99_TARGET_S = 0.100


@pytest.mark.benchmark
def test_system_state_latency(
    benchmark: object,
    benchmark_client: TestClient,
    seeded_100_projects: list[str],
) -> None:
    """GET /api/v1/system/state with 100 projects must average < 500ms.

    The endpoint reads only in-memory job and WebSocket state — the
    seeded projects exist purely to load the in-memory project repo.
    The benchmark fixture from ``pytest-benchmark`` runs the call
    multiple times and reports mean, stddev, min, max, and median.
    """
    assert len(seeded_100_projects) == 100

    def _call() -> int:
        response = benchmark_client.get("/api/v1/system/state")
        return response.status_code

    status_code = benchmark(_call)  # type: ignore[operator]
    assert status_code == 200

    stats = benchmark.stats.stats  # type: ignore[attr-defined]
    assert stats.mean < SYSTEM_STATE_MEAN_TARGET_S, (
        f"system/state mean {stats.mean * 1000:.1f}ms exceeds "
        f"{SYSTEM_STATE_MEAN_TARGET_S * 1000:.0f}ms target"
    )


@pytest.mark.benchmark
def test_version_endpoint_latency(
    benchmark: object,
    benchmark_client: TestClient,
) -> None:
    """GET /api/v1/version must complete with P99 < 100ms.

    The version handler issues a single indexed sqlite read against
    ``alembic_version`` and returns compile-time constants from the Rust
    core, so it should be sub-millisecond on the dev box. The 100ms P99
    target leaves headroom for CI runners and cold-cache reads.
    """

    def _call() -> int:
        response = benchmark_client.get("/api/v1/version")
        return response.status_code

    status_code = benchmark(_call)  # type: ignore[operator]
    assert status_code == 200

    stats = benchmark.stats.stats  # type: ignore[attr-defined]
    # pytest-benchmark does not expose a built-in P99, but max is a
    # strict upper bound on P99 — if max is under target, P99 is too.
    assert stats.max < VERSION_P99_TARGET_S, (
        f"version endpoint max {stats.max * 1000:.1f}ms exceeds "
        f"{VERSION_P99_TARGET_S * 1000:.0f}ms P99 target"
    )
