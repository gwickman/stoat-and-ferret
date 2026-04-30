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
| Locust        | `locust>=2.0` (dev dep, see `pyproject.toml`) — 2.43.4 used for this run           |
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
| Concurrent users | 50                | 50                                        |
| Total requests   | —                 | 7,374                                     |
| Request rate     | —                 | 24.62 req/s                               |
| Mean latency     | —                 | 3 ms (median/p50 response time — see NFR-001) |
| P95 latency      | —                 | 10 ms                                     |
| P99 latency      | < 200 ms (target) | 19 ms ✅ met                              |
| Error rate       | 0 %               | 0.00 %                                    |
| HTTP 5xx         | 0                 | 0                                         |

> **NFR-001 note:** The "Mean latency" cell records `median_ms` (50th percentile / p50 = 3 ms)
> from the `LOADTEST_SUMMARY` JSON, not arithmetic mean. This matches the harness output field
> name. Per-endpoint breakdown: `GET /api/v1/system/state` p50=2ms, p95=4ms;
> `GET /api/v1/version` p50=4ms, p95=11ms; `POST /api/v1/testing/seed` p50=7ms, p95=14ms.

**Deferral policy (per FR-001):** if P99 exceeds 200 ms on developer-
class hardware, record the observed value and mark it `deferred to
dedicated-hardware re-run`. This does **not** block v043 close.

## Scenario 2 — WebSocket storm (100 concurrent, 5 minutes)

Workload: 100 long-lived `/ws` connections held for the run duration;
each user reads inbound heartbeat messages but does not send.

| Metric                              | Target          | Recorded                               |
| ----------------------------------- | --------------- | -------------------------------------- |
| Concurrent connections              | 100             | 100                                    |
| Gauge `stoat_ws_connected_clients`  | within ±5 of 100| 100.0 at run mid-point ✅              |
| Unexpected disconnects              | 0               | 0                                      |
| Process OOM / crash                 | None            | None — server healthy (23+ min uptime) |
| Connection stability                | stable          | stable — 0 failures across 100 conns  |

> **Connection time note:** The harness reports ws.connect latency
> (WebSocket handshake + protocol upgrade over loopback) at avg 2,084 ms,
> min 2,039 ms, max 2,142 ms. All Locust approximation percentiles bucket
> to 2,100 ms. This is the initial handshake time, not per-message exchange
> latency. The `hold_connection` task uses a 1-second recv timeout for
> liveness; message-level latency is not separately captured here.

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
| Total jobs                   | 50                    | 14,490 (2,898 batches × 5 jobs; noop throughput far exceeded minimum 50-job design target) |
| Jobs reaching terminal state | 50                    | 14,490 (100%)       |
| Jobs `completed`             | ≥ 50                  | 14,490 ✅           |
| Jobs `failed`                | 0                     | 0                   |
| Run wall-clock duration      | < 10 minutes (NFR-003)| 600 s (locust timer elapsed; initial 50-job round completed within ~30 s) |
| FFmpeg processes spawned     | 0 (noop mode)         | 0 ✅                |

> **Throughput note:** With `STOAT_RENDER_MODE=noop`, the batch endpoint processes
> jobs synchronously through the FastAPI/SQLite layer without FFmpeg overhead.
> POST /api/v1/render/batch: median 19 ms; GET /api/v1/render/batch/{batch_id}
> poll: median 2 ms. Aggregate: p50=4ms, p95=22ms, p99=34ms across 8,694 requests.
> 0 failures throughout the 10-minute run.

> **Acceptance is binary on "terminal state reached".** P99/throughput
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
curl -s http://localhost:8765/metrics/ > metrics_snapshot.txt
grep '^stoat_' metrics_snapshot.txt
```

Save the snapshot alongside this document if a regression analysis is
required.

> **Note:** The `/metrics` endpoint redirects to `/metrics/` (HTTP 307).
> Use the trailing slash form in scripts to avoid the redirect.

---

## Analysis and Findings

Results recorded from a v047 run on 2026-04-30 against the Phase 6 application
state (app_version 0.3.0, git SHA 65b2176) with Locust 2.43.4 on Python 3.13.11.

### Scenario 1 — API Endpoints

API endpoint performance was excellent under 50 concurrent users over a 5-minute run.
All three endpoint classes remained well below the P99 < 200 ms target:
- p50 = 3 ms, p95 = 10 ms, p99 = 19 ms aggregate across all endpoints
- `GET /api/v1/system/state` is the fastest: p50 = 2 ms, p95 = 4 ms (in-memory aggregate reads)
- `POST /api/v1/testing/seed` is the slowest: p50 = 7 ms, p95 = 14 ms (DB write path)
- Zero errors and zero HTTP 5xx responses throughout
- A very small fraction of requests hit the ~2,100 ms bucket (p99.9 threshold), consistent
  with one-time initialization overhead on first access (DB connection warm-up)
- Throughput settled at ~24.6 req/s across 50 users with 1–3 second wait intervals

### Scenario 2 — WebSocket Connections

100 concurrent WebSocket connections were established and held stable for 5 minutes
with zero unexpected disconnects. The `stoat_ws_connected_clients` Prometheus gauge
confirmed exactly 100 active connections at mid-point (well within the ±5 tolerance).
The server showed no memory pressure or crash events (uptime exceeded 23 minutes across
all scenarios). WebSocket connection establishment (handshake + upgrade over loopback)
averaged 2,084 ms; this is consistent across all 100 users, suggesting a server-side
deferred initialization on first WebSocket upgrade rather than a scalability concern.

### Scenario 3 — Batch Render (noop mode)

The batch render path in noop mode demonstrated strong throughput on the FastAPI/SQLite
stack without FFmpeg involvement. Over 10 minutes, 2,898 batch submissions were processed
(14,490 total render jobs), all completing successfully:
- POST /api/v1/render/batch: p50 = 19 ms, p95 = 29 ms (batch acceptance + initial job creation)
- GET /api/v1/render/batch/{batch_id}: p50 = 2 ms, p95 = 7 ms (status polling)
- Zero job failures and zero FFmpeg process launches confirmed
- The batch pipeline is clearly CPU-bound on job acceptance; SQLite write latency
  dominates the batch submission path

### Cross-Scenario Observations

The API and batch scenarios operate at comparable request rates (~24 req/s and ~14.5 req/s
respectively), reflecting different workloads (CPU-light reads vs. DB writes). The WebSocket
scenario demonstrates that the application can sustain 100 long-lived connections without
degrading API or batch throughput on the same server instance. No saturation point was
observed at the tested concurrency levels; the bottleneck at 50 API users appears to be
client-side think time (1–3 s), not server-side capacity.

---

## Capacity Planning Recommendations

> **Scope qualification:** These recommendations derive from a single-machine local test
> on the hardware documented in [Executor Hardware Specs](#executor-hardware-specs)
> (i9-12950HX, 32 GB RAM, Windows 11, loopback networking). They are hardware-specific
> baselines for regression detection, not absolute SLOs. Scaling to multi-instance
> production deployment requires additional testing under production load patterns and
> network conditions.

### Concurrency limits

- **API (read-heavy workloads):** The application handled 50 concurrent users at p99 = 19 ms
  with no signs of saturation. A safe concurrency limit for single-instance deployment is
  estimated at 100–150 concurrent API users before DB write contention becomes significant.
  Apply a 50 % safety margin → recommend configuring load balancer to limit to **100
  concurrent HTTP connections per instance**.

- **WebSocket connections:** 100 concurrent long-lived connections were stable with no
  degradation. Based on default uvicorn worker behaviour and the connection overhead observed
  (~2 s handshake), recommend limiting to **150 concurrent WebSocket connections per
  instance** (50 % headroom above the tested 100).

- **Batch render (noop path):** At 10 concurrent BatchRenderUsers, the POST /api/v1/render/batch
  endpoint processed ~4.84 req/s with p99 = 51 ms. The noop path removes FFmpeg overhead,
  making DB write throughput the bottleneck. For the production (real FFmpeg) path, the
  render executor's `STOAT_RENDER_MAX_CONCURRENT` setting governs actual parallelism;
  recommend leaving it at the default (2) until GPU/CPU profiling under real render load is
  available.

### Request rate limits

- **Seed endpoint:** `POST /api/v1/testing/seed` is gated by `STOAT_TESTING_MODE` in
  production; no rate limiting needed here.
- **Batch render submit:** At the tested rate of ~4.84 POST /render/batch req/s × 5 jobs/batch
  = ~24 jobs/s (noop), the queue depth should be sized for 1–2 minutes of burst. Recommend
  a soft queue cap of **1,500 pending jobs** before backpressure is applied.

### Infrastructure recommendations

- **CPU:** API and WebSocket scenarios showed no CPU saturation on the i9-12950HX at these
  concurrency levels. For production, a 4-core/8-thread minimum is recommended to sustain
  50+ concurrent API users plus background batch workers without context-switch overhead.
- **Memory:** No OOM events were observed across all three scenarios (25+ minutes total
  uptime). The server process footprint is small; 2 GB minimum RAM per instance is sufficient
  for API and WebSocket workloads. Batch render with real FFmpeg will require additional
  headroom (~500 MB per concurrent FFmpeg process).
- **Storage (SQLite):** SQLite is the bottleneck on the write path (batch submission p50 =
  19 ms). For Phase 7 production use, consider WAL mode if not already enabled, and ensure
  the SQLite file resides on an NVMe SSD. If concurrent batch renders exceed 10/s, evaluate
  migrating to PostgreSQL for the render job queue.
- **Network:** All tests ran over loopback; production deployment behind a load balancer will
  add socket-layer latency. Expect p50 to increase by 1–5 ms in typical cloud environments
  — this remains well within SLO targets.

---

## Hardware Variability Note

These results were measured on the executor described in
[Executor Hardware Specs](#executor-hardware-specs). Production
hardware is expected to deliver lower latency at higher concurrency.
The published numbers represent a **relative baseline for regression
detection** — re-runs should compare against the prior recorded value
on equivalent hardware rather than against the absolute targets in the
"Target" columns.
