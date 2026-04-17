# Phase 6: Observability & Operations

## Structured Log Events

### Deployment Events

| Event | Level | Fields | When |
|-------|-------|--------|------|
| `deployment.startup` | INFO | `app_version`, `core_version`, `git_sha`, `database_version` | Application startup |
| `deployment.migration` | INFO | `from_version`, `to_version`, `backup_path`, `duration_ms` | Migration applied |
| `deployment.migration_rollback` | WARN | `version`, `rollback_sql_len`, `reason` | Migration rolled back |
| `deployment.health_check` | DEBUG | `live`, `ready`, `database`, `rust_core` | Health endpoint called |
| `deployment.feature_flag` | INFO | `flag_name`, `flag_value` | Flag state logged at startup |

### Testability Events

| Event | Level | Fields | When |
|-------|-------|--------|------|
| `testing.seed_created` | INFO | `fixture_name`, `project_count`, `video_count` | Seed endpoint called |
| `testing.seed_cleared` | INFO | `items_removed` | Seed teardown called |
| `testing.seed_blocked` | WARN | `reason` | Seed called with testing_mode=false |

### WebSocket Events

| Event | Level | Fields | When |
|-------|-------|--------|------|
| `ws.replay_requested` | INFO | `client_id`, `last_event_id`, `events_replayed` | Client reconnects with replay |
| `ws.replay_gap` | WARN | `client_id`, `last_event_id`, `oldest_buffered_id` | Requested event no longer in buffer |
| `ws.buffer_full` | WARN | `buffer_size`, `oldest_event_age_s` | Ring buffer at capacity |

## Prometheus Metrics

### Counters

| Metric | Labels | Purpose |
|--------|--------|---------|
| `stoat_deployment_startups_total` | `version` | Track deployment frequency |
| `stoat_migrations_total` | `version`, `status` | Migration success/failure |
| `stoat_seed_requests_total` | `fixture_name`, `status` | Seed endpoint usage |
| `stoat_ws_replays_total` | `status` (success/gap) | WebSocket replay requests |
| `stoat_ws_events_total` | `event_type` | Total events through WebSocket |
| `stoat_long_poll_requests_total` | `endpoint`, `result` (immediate/waited/timeout) | Long-poll usage |

### Histograms

| Metric | Labels | Buckets | Purpose |
|--------|--------|---------|---------|
| `stoat_migration_duration_seconds` | `version` | 0.1, 0.5, 1, 5, 10, 30 | Migration timing |
| `stoat_seed_duration_seconds` | `fixture_name` | 0.1, 0.5, 1, 5, 10 | Seed creation timing |
| `stoat_system_state_duration_seconds` | — | 0.01, 0.05, 0.1, 0.5, 1 | State snapshot latency |
| `stoat_long_poll_wait_seconds` | `endpoint` | 1, 5, 10, 15, 30 | Long-poll actual wait |

### Gauges

| Metric | Labels | Purpose |
|--------|--------|---------|
| `stoat_ws_buffer_size` | — | Current events in replay buffer |
| `stoat_ws_buffer_oldest_age_seconds` | — | Age of oldest buffered event |
| `stoat_ws_connected_clients` | — | Current WebSocket connections |
| `stoat_feature_flag_state` | `flag_name` | 1=enabled, 0=disabled |
| `stoat_active_jobs_count` | `job_type` | Current running jobs |

## Health Check Extensions

### GET /health/ready (enhanced)

```json
{
  "status": "ok",
  "database": "ok",
  "database_version": 15,
  "rust_core": "ok",
  "core_version": "0.6.0",
  "ws_buffer_utilization": 0.12,
  "uptime_seconds": 3600
}
```

New fields: `database_version`, `core_version`, `ws_buffer_utilization`, `uptime_seconds`.

### Synthetic Monitoring

When `STOAT_SYNTHETIC_MONITORING=true`, a background task runs every 60 seconds:

1. `GET /health/ready` — verify all subsystems healthy
2. `GET /api/v1/system/state` — verify state endpoint responds < 500ms
3. `GET /api/v1/version` — verify version matches expected deployment

Results emitted as `stoat_synthetic_check_total{check_name, status}` counter and `stoat_synthetic_check_duration_seconds{check_name}` histogram.

## Graceful Degradation

| Failure | Impact | Degradation |
|---------|--------|-------------|
| Replay buffer full | New events evict oldest | Log warning, increment `ws_buffer_full` counter |
| Seed endpoint misconfigured | 404 returned | Log `testing.seed_blocked` warning |
| Migration failure | Startup aborted | Log error with rollback SQL, exit with code 1 |
| System state query slow (>1s) | Agent timeout | Return partial snapshot with `degraded: true` flag |

## Quality Metrics Dashboard

M6.5 delivers a Prometheus/Grafana dashboard configuration:

| Panel | Query | Purpose |
|-------|-------|---------|
| Request latency P99 | `histogram_quantile(0.99, stoat_request_duration_seconds)` | SLI: API latency |
| Error rate | `rate(stoat_request_errors_total[5m])` | SLI: Error budget |
| Render throughput | `rate(stoat_render_jobs_total{status="completed"}[1h])` | Throughput tracking |
| WebSocket health | `stoat_ws_connected_clients` / `stoat_ws_replays_total` | Connection stability |
| Test coverage | External badge from CI | Quality gate metric |
