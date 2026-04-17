# Phase 6: Test Strategy

## Rust Unit Tests

### `version.rs`

```rust
#[test]
fn version_info_returns_valid_semver() {
    let info = VersionInfo::current();
    assert!(semver::Version::parse(&info.core_version).is_ok());
}

#[test]
fn version_info_has_build_timestamp() {
    let info = VersionInfo::current();
    assert!(!info.build_timestamp.is_empty());
}
```

### `schema.rs`

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn all_effects_have_valid_parameter_types(
        effect_name in prop::sample::select(KNOWN_EFFECTS.to_vec())
    ) {
        let schemas = get_effect_parameter_schemas(&effect_name);
        assert!(!schemas.is_empty(), "Effect {effect_name} has no parameters");
        for schema in &schemas {
            assert!(
                ["float", "int", "string", "enum", "bool"].contains(&schema.param_type.as_str()),
                "Invalid type: {}", schema.param_type
            );
        }
    }
}
```

## Python Smoke Tests

### Deployment Endpoints

| Test File | Scenarios |
|-----------|-----------|
| `tests/smoke/test_version.py` | Version endpoint returns valid semver, core_version present, database_version is integer |
| `tests/smoke/test_system_state.py` | State snapshot returns all sections, empty state is valid, includes queue_status |
| `tests/smoke/test_seed.py` | Seed creates fixtures when testing_mode=true, returns 404 when disabled, teardown clears all seeded data |
| `tests/smoke/test_flags.py` | Feature flags endpoint returns all flags, flags match Settings |
| `tests/smoke/test_schema.py` | Schema endpoint returns valid JSON Schema for each resource, 404 for unknown resource |

### WebSocket Enhancements

| Test File | Scenarios |
|-----------|-----------|
| `tests/smoke/test_ws_replay.py` | Connect with last_event_id receives replay, connect without gets no replay, expired events not replayed |
| `tests/smoke/test_ws_event_ids.py` | All events include event_id and timestamp, event_ids are monotonically increasing per job |

### Long-Poll

| Test File | Scenarios |
|-----------|-----------|
| `tests/smoke/test_long_poll.py` | Terminal job returns immediately, pending job waits then returns on completion, timeout returns current status |

## Contract Tests

### Migration Safety

```python
# tests/test_contract/test_migration.py
async def test_migration_creates_backup():
    """Verify migration creates backup before applying."""

async def test_migration_records_history():
    """Verify migration_history row created with rollback_sql."""

async def test_migration_rollback_restores_state():
    """Verify rollback_sql reverses the migration."""
```

### WebSocket Replay Buffer

```python
# tests/test_contract/test_ws_replay.py
async def test_replay_buffer_respects_size_limit():
    """Buffer evicts oldest events when full."""

async def test_replay_buffer_respects_ttl():
    """Events older than TTL are not replayed."""

async def test_replay_delivers_events_in_order():
    """Replayed events maintain insertion order."""
```

### System State Snapshot

```python
# tests/test_contract/test_system_state.py
async def test_state_includes_all_active_jobs():
    """State snapshot reflects all running jobs."""

async def test_state_reflects_project_changes():
    """Creating/deleting a project updates state snapshot."""
```

## Black Box Tests

### New Scenarios

| File | Scenario | Purpose |
|------|----------|---------|
| `test_deployment_workflow.py` | Start app → check version → check health → run synthetic check | M6.1/M6.2 deployment verification |
| `test_agent_workflow.py` | Seed → create project → add clip → render → wait (long-poll) → verify output | M6.7 agent testability E2E |
| `test_ws_reconnection.py` | Connect → trigger render → disconnect → reconnect with last_event_id → verify replay | M6.7 WebSocket hardening |

## UAT Journeys (Playwright)

### New Journeys

| ID | Journey | Steps | Milestone |
|----|---------|-------|-----------|
| J601 | Workspace layout | Open app → switch presets → resize panels → verify persistence on reload | M6.6 |
| J602 | Settings panel | Open settings → change theme → rebind shortcut → verify applied | M6.6 |
| J603 | Batch panel | Open render page → switch to batch tab → submit batch → verify progress | M6.6 |
| J604 | Keyboard navigation | Tab through all panels → verify focus indicators → use shortcuts | M6.9 |
| J605 | Screen reader | Navigate with ARIA landmarks → verify announcements on state changes | M6.9 |
| J606 | Agent seed workflow | Seed via API → verify data in Library → render → verify in render queue | M6.7 |

### Existing Journey Updates

| ID | Change |
|----|--------|
| J401–J404 | Verify works with new workspace layout wrapping |
| J501–J504 | Add batch panel tab navigation |

## Security Review (M6.5)

### Scope

| Area | Focus |
|------|-------|
| Python API | Input validation, auth boundaries, seed endpoint guard, SQL injection (parameterised queries) |
| Rust core | Unsafe blocks audit, panic paths, FFmpeg command injection (sanitize module) |
| WebSocket | Event replay doesn't leak cross-session data, buffer bounds enforced |
| Dockerfile | No secrets in image layers, non-root user, minimal attack surface |
| Dependencies | `pip-audit` + `cargo audit` for known CVEs |

### Performance Benchmarks (M6.5)

| Benchmark | Target | Tool |
|-----------|--------|------|
| API latency P99 | < 100ms (non-render endpoints) | `locust` or `k6` |
| System state endpoint | < 500ms with 100 projects | `pytest-benchmark` |
| WebSocket replay | < 200ms for 1000-event replay | `pytest-benchmark` |
| Render throughput | Baseline established | `hyperfine` wrapping CLI |
| Container startup | < 10s to healthy | `time` + health poll |
| Bundle size | < 500KB gzipped | `vite-bundle-analyzer` |

### Load Testing

| Scenario | Concurrent Users | Duration | Success Criteria |
|----------|-----------------|----------|------------------|
| API baseline | 50 | 5 min | P99 < 200ms, 0 errors |
| WebSocket storm | 100 connections | 5 min | All events delivered, no OOM |
| Batch rendering | 10 batches of 5 jobs | 10 min | All complete, progress accurate |
