# Performance Baselines — v043 (BL-288)

This document records the initial performance baselines for stoat-and-ferret
captured during the BL-288 / Phase 6 work. The numbers feed downstream
load-testing (BL-289) and observability (BL-290) features.

## How to Reproduce

```bash
uv run pytest tests/benchmarks/ --benchmark-only --no-cov -v
```

The default test suite excludes `tests/benchmarks/` (`addopts = --ignore=tests/benchmarks`
in `pyproject.toml`). pytest-benchmark prints a min/mean/max/median table at the
end of the run.

To verify the seven Phase 6 metrics are exposed at `/metrics`:

```bash
uv run pytest tests/test_api/test_metrics_phase6.py -v --no-cov
```

This test runs in default CI and asserts every metric is registered.

## Executor Hardware Specs (initial capture)

| Field | Value |
|-------|-------|
| CPU | 12th Gen Intel Core i9-12950HX |
| Cores | 16 physical / 24 logical |
| RAM | 31.7 GB |
| OS | Windows 11 |
| Python | 3.13.11 (CI matrix covers 3.10 / 3.11 / 3.12) |
| Network | Loopback (`fastapi.testclient.TestClient`, no socket I/O) |
| Captured | 2026-04-27 |

CI runners use different hardware (GitHub-hosted ubuntu/macos/windows-latest);
expect the absolute numbers to drift, but the relative ordering and the
acceptance-criteria targets should hold.

## Baseline Metrics

| Metric | Target | Measured (mean) | Measured (max) | Pass |
|--------|--------|-----------------|----------------|------|
| `GET /api/v1/system/state` (100 projects) | < 500 ms (mean) | 0.79 ms | 27.2 ms | yes |
| `GET /api/v1/version` | < 100 ms (P99) | 2.35 ms | 9.0 ms (max ≥ P99) | yes |
| `ConnectionManager.replay_since` (1000 events, mid-buffer) | < 200 ms (mean) | 0.33 ms | 3.5 ms | yes |

**Headroom note.** All three results are roughly 30×–600× faster than
their targets on the dev box. The targets are deliberately set at the
"would-fail-the-canary" threshold rather than at the observed baseline so
CI runners (which are slower than the dev laptop) still leave room before
flagging a regression. Tighten the targets only after BL-289 load-testing
quantifies multi-client overhead.

## Phase 6 Prometheus Metrics

All seven metrics registered by `src/stoat_ferret/api/middleware/metrics.py`:

| Metric | Type | Labels | Emitted From |
|--------|------|--------|--------------|
| `stoat_seed_duration_seconds` | Histogram | — | `routers/testing.py` (POST `/api/v1/testing/seed`) |
| `stoat_system_state_duration_seconds` | Histogram | — | `routers/system.py` (GET `/api/v1/system/state`) |
| `stoat_ws_buffer_size` | Gauge | — | `websocket/manager.py::ConnectionManager.broadcast` |
| `stoat_ws_connected_clients` | Gauge | — | `websocket/manager.py::ConnectionManager.connect`/`disconnect` |
| `stoat_active_jobs_count` | Gauge | `job_type` | `jobs/queue.py::AsyncioJobQueue.submit` and `process_jobs` (terminal) |
| `stoat_feature_flag_state` | Gauge | `flag` | `lifespan.py::record_feature_flags` (startup) and `routers/flags.py` (per request) |
| `stoat_migration_duration_seconds` | Histogram | `result` | `services/migrations.py::MigrationService.apply_pending_sync` |

All metrics live in the prometheus-client default registry and are exposed via
`prometheus_client.make_asgi_app()` mounted at `/metrics` in `api/app.py`.

## Notes

- The dev-laptop numbers above are wall-clock readings via
  `pytest-benchmark`'s `time.perf_counter` timer with GC enabled. The
  benchmarks call live FastAPI / `ConnectionManager` code (no mocks) per
  LRN-250 and BL-288 NFR-003.
- `seeded_100_projects` and `replay_buffer_1000_events` are session-scoped
  fixtures so the heavy setup (100 seed POSTs / 1000 deque appends) runs
  once per session rather than once per benchmark.
- `replay_since(mid_event_id)` returns 499 events — i.e. the second half
  of the buffer — so the benchmark exercises the full deque scan, the
  TTL filter, and the slice operation.
- The `/api/v1/version` benchmark uses `pytest-benchmark`'s `max` as a
  conservative substitute for P99 because the plugin does not surface
  P99 directly; if `max` is under 100 ms, P99 is too.
