# Load Test Results — v043 (BL-289)

This document captures the load-test harness, scenarios, and the **last
recorded result set**. Hardware specs are documented up-front so future
runs can establish a relative baseline rather than chasing absolute SLOs
on heterogeneous hardware.

> **How to run:** see [Reproducing the run](#reproducing-the-run) below.
> The harness lives at [`tests/loadtests/locustfile.py`](../../tests/loadtests/locustfile.py)
> and is excluded from the default pytest suite (`pyproject.toml`
> `addopts = "… --ignore=tests/loadtests"`). Operators paste their own
> measurements into the [scenario tables](#scenario-1--api-users-50-concurrent-5-minutes)
> after each run.

---

## Executor Hardware Specs

| Property      | Value                                                                              |
| ------------- | ---------------------------------------------------------------------------------- |
| CPU           | 12th Gen Intel Core i9-12950HX — 16 physical cores / 24 logical, 2.30 GHz nominal  |
| RAM           | 32 GB (31.7 GB visible)                                                            |
| OS            | Windows 11 Pro 24H2 (build 26200)                                                  |
| Python        | 3.13.11 (target matrix: 3.10/3.11/3.12)                                            |
| Locust        | `locust>=2.0` (dev dep, see `pyproject.toml`)                                      |
| Network       | Loopback (`127.0.0.1` — no socket-layer latency)                                   |
| Executor role | Developer laptop                                                                   |

> ⚠️ **Hardware variability note:** Risk 4 from the v043 risk
> assessment classifies the P99 < 200 ms target as aspirational on
> developer-class hardware. The CI runners (2-core, 7 GB) cannot
> sustain 100 concurrent WebSocket connections, so this scenario is
> only run on developer-class or production-class machines. Treat
> result tables as **relative baselines** for regression detection,
> not absolute SLOs.

---

## Scenario 1 — API users (50 concurrent, 5 minutes)

Workload mix per virtual user (3:2:1 weight):

* `GET /api/v1/system/state`
* `GET /api/v1/version`
* `POST /api/v1/testing/seed`

| Metric           | Target            | Recorded                                  |
| ---------------- | ----------------- | ----------------------------------------- |
| Concurrent users | 50                | _record actual_                           |
| Total requests   | —                 | _record actual_                           |
| Request rate     | —                 | _record actual_ req/s                     |
| Mean latency     | —                 | _record actual_ ms                        |
| P95 latency      | —                 | _record actual_ ms                        |
| P99 latency      | < 200 ms (target) | _record actual_ ms (✅ met / ⚠️ deferred) |
| Error rate       | 0 %               | _record actual_ %                         |
| HTTP 5xx         | 0                 | _record actual_                           |

**Deferral policy (per FR-001):** if P99 exceeds 200 ms on developer-
class hardware, record the observed value and mark it `deferred to
dedicated-hardware re-run`. This does **not** block v043 close.

## Scenario 2 — WebSocket storm (100 concurrent, 5 minutes)

Workload: 100 long-lived `/ws` connections held for the run duration;
each user reads inbound heartbeat messages but does not send.

| Metric                              | Target          | Recorded                               |
| ----------------------------------- | --------------- | -------------------------------------- |
| Concurrent connections              | 100             | _record actual_                        |
| Gauge `stoat_ws_connected_clients`  | within ±5 of 100| _record actual_ at run mid-point       |
| Unexpected disconnects              | 0               | _record actual_                        |
| Process OOM / crash                 | None            | _record actual_                        |
| Connection stability                | stable          | _record actual_                        |

**Metric validation procedure (FR-004):** during the run, poll
`GET /metrics` once every 5 seconds and grep for
`stoat_ws_connected_clients`:

```bash
while true; do
  curl -s http://localhost:8765/metrics \
    | grep '^stoat_ws_connected_clients '
  sleep 5
done
```

The reported gauge value must remain within ±5 of the locust-reported
connection count for the duration of the steady-state phase (the ramp
phase is intentionally excluded from the comparison since it inflates
both numerator and denominator transiently).

## Scenario 3 — Batch render (50 jobs, synthetic mode)

Workload: 10 concurrent `BatchRenderUser` virtual users each submit one
batch of five jobs (50 jobs total) and poll the batch endpoint until
every job reaches `completed` or `failed`. The server must run with
`STOAT_RENDER_MODE=noop` so renders short-circuit without spawning
FFmpeg.

| Metric                       | Target                | Recorded            |
| ---------------------------- | --------------------- | ------------------- |
| Total jobs                   | 50                    | _record actual_     |
| Jobs reaching terminal state | 50                    | _record actual_     |
| Jobs `completed`             | ≥ 50                  | _record actual_     |
| Jobs `failed`                | 0                     | _record actual_     |
| Run wall-clock duration      | < 10 minutes (NFR-003)| _record actual_ s   |
| FFmpeg processes spawned     | 0 (noop mode)         | _record actual_     |

> **Acceptance is binary on “terminal state reached”.** P99/throughput
> on the noop path is informational — once FFmpeg short-circuits, the
> bottleneck is FastAPI/SQLite throughput, not the render path.

---

## Reproducing the run

### 1. Start the server in synthetic mode

```bash
STOAT_RENDER_MODE=noop \
STOAT_TESTING_MODE=true \
STOAT_SEED_ENDPOINT=true \
uv run python -m stoat_ferret.api
```

`STOAT_RENDER_MODE=noop` enables the synthetic short-circuit added in
this release (`src/stoat_ferret/render/service.py`). `STOAT_TESTING_MODE`
and `STOAT_SEED_ENDPOINT` are required so `POST /api/v1/testing/seed`
returns 201 instead of 403.

### 2. Run each scenario from a separate terminal

Locust 2.x lets you select a single User class via positional argument so
you can run scenarios serially without restarting the server:

```bash
# Scenario 1 — API users
locust -f tests/loadtests/locustfile.py -u 50 -r 10 -t 5m \
    --headless --host http://localhost:8765 APIUser

# Scenario 2 — WebSocket storm (run after scenario 1 settles)
locust -f tests/loadtests/locustfile.py -u 100 -r 20 -t 5m \
    --headless --host http://localhost:8765 WebSocketUser

# Scenario 3 — batch render (requires STOAT_RENDER_MODE=noop)
locust -f tests/loadtests/locustfile.py -u 10 -r 1 -t 10m \
    --headless --host http://localhost:8765 BatchRenderUser
```

Locust prints a `LOADTEST_SUMMARY {…}` JSON line on stdout at the end of
each run. Paste the recorded numbers into the tables above after each
scenario completes.

### 3. (Optional) Capture metric snapshots

```bash
curl -s http://localhost:8765/metrics > metrics_snapshot.txt
grep '^stoat_' metrics_snapshot.txt
```

Save the snapshot alongside this document if a regression analysis is
required.

---

## Analysis and Findings

> _Operators: paste a paragraph after each run summarising surprises,
> regressions, or capacity limits observed. Empty until the first run is
> recorded._

## Capacity Planning Recommendations

> _Operators: paste capacity-planning conclusions after the first run.
> Examples: maximum concurrent renders the noop path can sustain on
> dev-class hardware; whether 100 WebSocket connections approach the
> default uvicorn worker capacity; whether `STOAT_RENDER_MAX_CONCURRENT`
> needs adjustment before Phase 7 GUI work._

## Hardware Variability Note

These results were measured on the executor described in
[Executor Hardware Specs](#executor-hardware-specs). Production
hardware is expected to deliver lower latency at higher concurrency.
The published numbers represent a **relative baseline for regression
detection** — re-runs should compare against the prior recorded value
on equivalent hardware rather than against the absolute targets in the
"Target" columns.
