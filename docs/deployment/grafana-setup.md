# Grafana Setup for stoat-and-ferret

Pre-built SLI dashboard at [`grafana/dashboard.json`](../../grafana/dashboard.json)
covering Phase 6 service-level indicators: API latency, error rate,
render throughput, WebSocket health, synthetic probes, and active jobs.
Includes two SLO alert rules (P99 latency > 200 ms, 5xx error rate > 1%).

The dashboard is **artifact-only** — there is no automated provisioning
or container deployment in this repo. Operators import it manually into
their Grafana instance (BL-290).

## Prerequisites

- Grafana **9.x or later** (tested schema version 38; compatible with 9.x,
  10.x, and 11.x).
- A Prometheus data source named `Prometheus` with UID `prometheus`. If
  the UID differs in your Grafana, edit each panel's `datasource.uid`
  after import or remap on the import dialog.
- Prometheus configured to scrape the application's `/metrics` endpoint
  (default scrape interval 15 s recommended).
- Application metrics middleware enabled — see
  [`src/stoat_ferret/api/middleware/metrics.py`](../../src/stoat_ferret/api/middleware/metrics.py)
  for the full registered metric set.

## Dashboard Import

1. **Open Grafana**: navigate to **Dashboards → New → Import**.
2. **Upload JSON**: paste the contents of `grafana/dashboard.json`, or
   click *Upload JSON file* and select the file directly. (You can also
   drop the raw URL of the file in this repo if your Grafana instance
   has internet egress.)
3. **Map the data source**: when prompted for the Prometheus data
   source, select your existing one. If your data source UID is not
   `prometheus`, Grafana will offer a remap step.
4. **Click Import**. The dashboard appears with the title
   *stoat-and-ferret SLI Dashboard*. UID is fixed at `stoat-sli-v043`,
   so re-importing the same JSON updates the dashboard in place rather
   than creating duplicates.
5. **Verify**: all 7 panels should render. Empty panels with "No data"
   are normal until Prometheus has scraped the application at least
   once.

## Panels

| # | Panel | Query / metric | Notes |
|---|-------|----------------|-------|
| 1 | Request Latency P99 | `histogram_quantile(0.99, …)` over `http_request_duration_seconds`, `stoat_system_state_duration_seconds`, `stoat_seed_duration_seconds`, `stoat_migration_duration_seconds` | 200 ms threshold line driven by panel field config |
| 2 | Error Rate (5xx / total) | `http_requests_total{status=~"5.."}` ratio | 1% threshold line driven by panel field config |
| 3 | Render Throughput (jobs/min) | `stoat_active_jobs_count` rate by `job_type`, plus seed-job rate | Multiplied by 60 to express as per-minute |
| 4 | WebSocket Connections | `stoat_ws_connected_clients` gauge | Should track concurrent client count |
| 5 | WebSocket Buffer Utilization | `stoat_ws_buffer_size` gauge | Number of buffered replay events |
| 6 | Synthetic Checks | `/health` probe rate and `stoat_feature_flag_state` gauges | Combines availability + flag visibility |
| 7 | Active Jobs by Type | `stoat_active_jobs_count` grouped by `job_type` | Donut piechart |

## Alert Rules

The dashboard JSON ships two SLO alert definitions in the top-level
`alerts` array:

| Rule | Condition | For | Severity |
|------|-----------|-----|----------|
| **P99 Latency SLO Breach** | `histogram_quantile(0.99, …http_request_duration_seconds_bucket) > 0.2` | 5 m | warning |
| **Error Budget Exceeded**  | `(5xx rate / total rate) > 0.01` | 5 m | warning |

These are PromQL-style conditions intended for evaluation by Grafana
managed alerting. To activate them in your environment:

1. Navigate to **Alerting → Alert rules → New rule**.
2. Recreate each rule using the PromQL `expr` shown above (or import
   the JSON via Grafana's API), pointing the rule at your Prometheus
   data source.
3. Attach a notification channel under **Alerting → Contact points**
   (Slack, PagerDuty, email, etc. — none is configured in this repo).
4. Choose an evaluation interval consistent with your Prometheus
   scrape interval (e.g. 30 s).

> **Why not provisioned?** Alert routing and contact points are
> tenant-specific — they depend on your notification stack. Shipping
> them in JSON would either be useless (placeholder UIDs) or wrong
> (someone else's Slack webhook).

## Metric Reference

Phase 6 metrics emitted by the application
(see [`metrics.py`](../../src/stoat_ferret/api/middleware/metrics.py)):

| Metric | Type | Labels | Source |
|--------|------|--------|--------|
| `http_requests_total` | Counter | method, path, status | `MetricsMiddleware` |
| `http_request_duration_seconds` | Histogram | method, path | `MetricsMiddleware` |
| `stoat_seed_duration_seconds` | Histogram | — | `POST /api/v1/testing/seed` |
| `stoat_system_state_duration_seconds` | Histogram | — | `GET /api/v1/system/state` |
| `stoat_ws_buffer_size` | Gauge | — | `ConnectionManager` replay buffer |
| `stoat_ws_connected_clients` | Gauge | — | `ConnectionManager` |
| `stoat_active_jobs_count` | Gauge | `job_type` | Asyncio job queue |
| `stoat_feature_flag_state` | Gauge | `flag` | `Settings` flag values |
| `stoat_migration_duration_seconds` | Histogram | `result` | Alembic upgrade |

## Updating the Dashboard

The dashboard JSON is the single source of truth. To modify it:

1. Edit `grafana/dashboard.json` directly — the file is hand-curated,
   not exported from a running Grafana.
2. Run the validation tests:
   ```bash
   uv run pytest tests/test_grafana_dashboard.py -v
   ```
   These guarantee JSON validity, panel structure, alert rule presence,
   and that every metric referenced is registered in
   `metrics.py` (no hallucinated names).
3. Commit; on next import, the dashboard updates in place because the
   `uid` is stable.

## Troubleshooting

- **All panels show "No data"** — Prometheus is not yet scraping the
  app. Check **Configuration → Data sources → Prometheus → Save & test**,
  then verify the app's `/metrics` endpoint returns content.
- **Some panels show "No data"** — the corresponding metric has not yet
  been observed. Histograms (`*_duration_seconds`) only emit after the
  endpoint has been called at least once.
- **Datasource UID mismatch on import** — Grafana will surface a
  remap dialog; pick your data source. To make the change permanent,
  edit the imported JSON in **Dashboard settings → JSON model**, or
  re-export and replace the bundled JSON.
- **Alert rules don't appear** — the JSON's `alerts` array is for
  reference only; Grafana managed alerts must be created via
  **Alerting → Alert rules** (see *Alert Rules* above).
