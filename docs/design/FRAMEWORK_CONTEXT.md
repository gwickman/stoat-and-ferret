# FRAMEWORK_CONTEXT.md

Framework guidance for stoat-and-ferret.

---

## 1. Purpose and Scope

This document provides current framework guidance for all stoat-and-ferret design tasks. It covers
dependency versions (pinned and resolved), canonical code patterns, banned anti-patterns, and known
migration debt. Maintained exclusively by task 002 (framework-context-analysis). All downstream design
tasks should read this document before specifying implementation details.

---

## 2. Current Framework Stack

### Python (`pyproject.toml` / `uv.lock`)

| Package | Range | Resolved |
|---------|-------|---------|
| Python | >=3.10 | 3.10–3.12 (CI matrix) |
| fastapi | >=0.109 | 0.128.0 |
| pydantic | (transitive) | 2.12.5 |
| pydantic-settings | >=2.0 | 2.x |
| uvicorn[standard] | >=0.27 | 0.40.0 |
| structlog | >=24.0 | 25.5.0 |
| aiosqlite | >=0.19 | 0.22.1 |
| alembic | >=1.13 | 1.18.1 |
| sqlalchemy | (via alembic) | 2.0.46 |
| prometheus-client | >=0.20 | 0.20.x |
| jsonschema | >=4.26.0 | 4.26.x |
| playwright | >=1.58,<2.0 | UAT only |

Dev tools:

| Package | Range | Notes |
|---------|-------|-------|
| pytest | >=8.0 | asyncio_mode=auto |
| pytest-asyncio | >=0.23 | 1.3.0 resolved |
| pytest-cov | >=4.0 | 80% minimum coverage |
| pytest-timeout | >=2.0 | execution timeout guard |
| httpx | >=0.26 | async HTTP test client |
| hypothesis | >=6.100 | property-based testing |
| ruff | >=0.4 | lint + format (rules: E F I UP B SIM ASYNC) |
| mypy | >=1.10 | strict mode, python_version=3.10 |
| maturin | >=1.0 | Rust extension build |
| types-jsonschema | >=4.26.0.20260202 | mypy stubs for jsonschema |

### Rust (`Cargo.toml` / `Cargo.lock`)

| Crate | Version | Notes |
|-------|---------|-------|
| pyo3 | 0.26 | abi3-py310 stable ABI |
| pyo3-stub-gen | 0.17 | type stub generation |
| regex | 1 (1.12.3) | pattern matching |
| criterion | 0.5 | benchmarks (dev) |
| proptest | 1.0 | property tests (dev) |

### Frontend (`package.json`)

| Package | Range | Notes |
|---------|-------|-------|
| react | ^19.2.0 | UI framework |
| react-dom | ^19.2.0 | DOM renderer |
| react-router-dom | ^7.13.0 | client-side routing |
| zustand | ^5.0.11 | state management |
| hls.js | ^1.6.15 | HLS video playback |
| typescript | ~5.9.3 | type checking |
| vite | ^7.3.1 | build tool |
| vitest | ^4.0.18 | unit test runner |
| tailwindcss | ^4.1.18 | utility CSS framework |
| eslint | ^9.39.1 | JS/TS linting |
| openapi-typescript | ^7.13.0 | API type generation |

---

## 3. Preferred Patterns

### Python

- **Logging**: `logger = structlog.get_logger(__name__)`. Semantic event style: `logger.info("event_name", key=value)`.
- **DI**: Services on `app.state` during lifespan; injected via `FastAPI.Depends()`. Test mode: `app.state._deps_injected = True` bypasses lifespan.
- **Async timeouts**: Use `asyncio.TimeoutError` (not `builtins.TimeoutError`) with `asyncio.wait_for()` — distinct types in Python 3.10.
- **Pydantic V2**: `ConfigDict(from_attributes=True)` for ORM model mapping. `BaseSettings` with `STOAT_` env prefix via `SettingsConfigDict`.
- **Repository pattern**: Abstract `Protocol` types for repos; pluggable SQLite implementations.
- **Forward refs**: `from __future__ import annotations` on all public modules.
- **Error suppression**: `contextlib.suppress()` (SIM105 rule enforces this over bare try/except/pass).
- **Test fixtures**: Session-scoped fixtures for expensive setup; `asyncio_mode = "auto"` eliminates manual event loop handling.

### Rust / PyO3

- **Method naming**: `py_` prefix for Rust method names, `#[pyo3(name = "...")]` to expose clean Python names.
- **Error handling**: Return `PyResult<T>`; use `?` operator; no `unwrap()` in library code.
- **Stubs**: After any PyO3 binding change, run `cargo run --bin stub_gen` and manually update `stubs/stoat_ferret_core/_core.pyi`.
- **Incremental bindings**: Implement Rust type AND PyO3 bindings in the same feature — never defer.
- **Attributes**: `#[pyo3(get)]` for read-only Python properties.

### WebSocket Replay

- **Buffer scope**: In-memory replay buffer MUST be server-global (shared on `ConnectionManager`). All clients are buffered to a single deque; there is no per-connection buffer or per-client filtering at the buffer level.
- **Client identity**: Transient only; client identity at reconnect is derived from the `Last-Event-ID` HTTP header value (containing the event's `event_id` field). No session cookie, session ID, or other durable identity mechanism is maintained.
- **Replay flow**: On reconnect, parse `Last-Event-ID` header → call `manager.replay_since(last_event_id)` → apply TTL filter (exclude events older than `ws_replay_ttl_seconds`) → find the supplied `event_id` in the fresh events → return events strictly after it (or all fresh if not found).
- **Memory model**: O(ws_replay_buffer_size) total, not O(buffer_size × connection_count). Events survive connection disconnect but NOT server restart (in-memory only).

### WebSocket Client Identity

- **Token format**: 32-char lowercase hex string, generated via `secrets.token_hex(16)`. Non-hex or wrong-length tokens are rejected with WebSocket close code 4400.
- **Transport**: Token is passed as a query parameter on WebSocket connect: `/ws?subscribe_token=<token>`. Clients generate and store the token locally before initiating the connection.
- **Storage**: In-memory dict keyed by `client_id` (the token value), managed by `ConnectionManager`. No disk persistence or external store.
- **Lifecycle**: Entry created on successful token validation and WebSocket connect. Entry cleared on disconnect. Identity does not survive server restart.
- **Reconnection semantics**: On reconnect, the client provides the same token → `ConnectionManager` looks up the prior entry. If found, the prior entry is retrieved (enabling state continuity for future rate limiting or event filtering). If not found (e.g., after server restart), a new entry is created.
- **Backwards-compatible fallback**: If `subscribe_token` is absent, the connection proceeds via the existing Last-Event-ID legacy path unchanged. The `Last-Event-ID` header is read independently of token presence — replay logic has no token dependency. See [WebSocket Replay](#websocket-replay) for replay mechanics.
- **Upgrade triggers**: Switch to session cookies if per-session rate limiting requires cookie-based identity. Add Redis-backed storage if multi-process deployment requires cross-process identity lookup. v056 implements per-connection in-memory storage only; multi-process and persistence are explicitly deferred.

### Frontend

- **State**: Zustand stores for cross-component state; `useState` for component-local state.
- **Styling**: Tailwind utility classes only; no inline styles.
- **API types**: Run `npm run generate:types` to regenerate from `openapi.json` after API changes.
- **Testing**: Vitest for unit tests; Playwright for UAT.
  - **Multi-phase hook tests require async `act()`** (LRN-189): hooks that trigger multiple render cycles (e.g., `useWebSocket`, `useRenderJob`) must be tested with `await act(async () => {})`. Using sync `act()` silently passes tests that assert stale intermediate state.

    ```typescript
    // WRONG — sync act() leaves state at intermediate phase
    act(() => { result.current.sendMessage("ping"); });
    expect(result.current.messages).toHaveLength(1); // may assert stale state

    // CORRECT — await act(async () => {}) drains all async updates
    await act(async () => { result.current.sendMessage("ping"); });
    expect(result.current.messages).toHaveLength(1); // asserts final state
    ```

### Startup Initialization Sequence

The FastAPI `lifespan()` function in `src/stoat_ferret/api/app.py:126` implements a 14-phase initialization sequence that is a correctness contract for any new service or background task. Inserting a service before its dependencies causes silent failures or startup crashes.

**Phases (lines 126–337 of `src/stoat_ferret/api/app.py`):**

| Phase | Name | Lines | Purpose |
|-------|------|-------|---------|
| 1 | Logging & Settings | 141–147 | Configure structlog and load `Settings`; all subsequent phases may log |
| 2 | WebSocket Manager | 150–151 | Create `ConnectionManager` (idempotent: skipped if already on `app.state`) |
| 3 | Startup Gate Armed | 154–155 | Set `app.state._startup_ready = False`; `/health` returns 503 until Phase 13 |
| 4 | Test-Mode Bypass | 158–163 | If `app.state._deps_injected = True`, set gate ready and yield immediately — skips Phases 5–14 |
| 5 | Alembic Migrations | 167 | Copy-on-absent bootstrap: if `data/stoat.db` is absent, copy fixture from `tests/fixtures/stoat.seed.db` and emit `deployment.bootstrap`. Then apply pending migrations via `run_startup_migrations()`. Must precede DB open. Failure modes: (a) fixture absent → `FileNotFoundError`; (b) schema mismatch → `deployment.migration.failed` at critical level. |
| 6 | Database Connection | 170–171 | Open `aiosqlite` connection; requires applied schema from Phase 5 |
| 7 | Schema Idempotent Creation | 174 | Run `create_tables_async()` using `CREATE TABLE IF NOT EXISTS`; safe on re-entry |
| 8 | Feature Flag Audit Log | 178 | Record enabled flags to `feature_flag_log` table (requires Phase 7) |
| 9 | AuditLogger Initialization | 181–184 | Open sync `sqlite3` connection; create `AuditLogger`; required by repositories |
| 10 | Repositories Initialized | 186–194 | Create `AsyncSQLiteBatchRepository`, `SQLiteProxyRepository`, and media repositories (require Phase 6) |
| 11 | Application Services | 196–287 | Instantiate `ThumbnailService`, `WaveformService`, `ProxyService`, `RenderService`, `PreviewManager`, `QCService`, `DeliveryProfileService`; register job handlers at lines 273–287 |
| 12 | Background Job Worker | 289–291 | Start `asyncio.create_task(job_queue.process_jobs())`; all handlers must be registered first |
| 13 | Gate Cleared & Startup Event | 305–313 | Set `app.state._startup_ready = True`; emit `deployment.startup` log event; `/health` returns 200 |
| 14 | Optional Synthetic Monitoring | 320–337 | If `synthetic_monitoring` flag enabled, start `SyntheticMonitoringTask`; probes the initialized app via ASGITransport |

**Startup gate pattern:**
- `app.state._startup_ready` is `False` from Phase 3 until Phase 13.
- `GET /health` (`src/stoat_ferret/api/routers/health.py:63`) returns HTTP 503 (`{"ready": false, "status": "starting"}`) while the flag is `False`.
- Test-mode bypass (Phase 4, `app.state._deps_injected = True`) sets the gate to `True` immediately and returns without running Phases 5–14, allowing `/health` to pass in unit tests without a real database.

**Ordering constraints:**

| Phase | Must Follow | Reason |
|-------|-------------|--------|
| 2+ | 1 | All phases may log; logging must be configured first |
| 5 | 4 | Migrations run only in non-test mode; test bypass exits before Phase 5 |
| 6 | 5 | DB connection requires applied schema |
| 7 | 6 | Table creation requires an open connection |
| 8 | 7 | `feature_flag_log` table must exist before insert |
| 9 | 8 | AuditLogger opens the same DB; ordering preserves audit consistency |
| 10 | 9 | Repositories accept `audit_logger` parameter from Phase 9 |
| 11 | 10 | Services accept repositories from Phase 10 |
| 12 | 11 | Worker starts only after all job handlers are registered (lines 273–287) |
| 13 | 12 | Gate clears only after all subsystems are live |
| 14 | 13 | Synthetic task probes the app via ASGITransport; requires gate cleared |

**Rules for new services and background tasks:**
- **New services** must initialize after Phase 6 (database connection open, line 170) and before Phase 9 (AuditLogger, line 181). If the service requires a repository, initialize after Phase 10 (line 186).
- **New background tasks** must start after Phase 12 (background job worker started, line 289) and before Phase 13 (gate cleared, line 305). Do not start tasks that probe the application before Phase 13.
- Never insert DB-dependent code before Phase 5 (Alembic migrations, line 167) — schema state is undefined until migrations apply.
- See also: `AGENTS.md → Startup Ordering Rule` for the actionable constraint.

#### Fixture Lifecycle Invariants

The baseline SQLite schema used during development and UAT is stored as an immutable fixture at `tests/fixtures/stoat.seed.db` and tracked in git. Two invariants govern the fixture lifecycle:

**Invariant 1 — Fixture is never modified by tests.**
Tests that require a database use `tmp_path`-isolated copies or ephemeral databases. The fixture at `tests/fixtures/stoat.seed.db` is read-only during test runs. Violation: a test writing directly to `tests/fixtures/stoat.seed.db` corrupts all subsequent tests and UAT runs that bootstrap from the fixture.

**Invariant 2 — Fixture must match the current Alembic head.**
The fixture schema must match the latest migration in `alembic/versions/`. If the fixture lags behind the Alembic head, Phase 5 bootstrap copies a stale schema and subsequent migrations may produce unexpected state or fail.

#### Fixture Update Procedure

When a new Alembic migration is added, regenerate the fixture in the same PR:

```bash
uv run alembic -x sqlalchemy.url=sqlite:////tmp/new_fixture.db upgrade head
cp /tmp/new_fixture.db tests/fixtures/stoat.seed.db
uv run pytest tests/test_db_fixture_lifecycle.py -v
```

The fixture update **must be committed in the same PR as the migration** that changes the schema head. Committing the migration without updating the fixture violates Invariant 2 and causes `test_db_fixture_lifecycle.py` failures in CI.

Sourced from git history (commit 1ea54795).

### Database Migrations

Alembic + SQLAlchemy manage schema evolution exclusively. Runtime database operations use raw aiosqlite. These layers must remain separate — migrations must not import app-layer code or depend on runtime schema state.

**Upgrade pattern — `CREATE TABLE IF NOT EXISTS`:**
- All audit and operational tables must be created with `CREATE TABLE IF NOT EXISTS table_name (...)` (full schema inline).
- `IF NOT EXISTS` is mandatory, not optional. MigrationService may attempt to create a table that already exists if a prior deployment was partially applied and retried.
- Indexes follow the same rule: `CREATE INDEX IF NOT EXISTS idx_name ON table(col)`.

**Downgrade pattern — no-op for append-only tables:**
- Audit and operational tables are append-only. Downgrade must never drop these tables.
- A `DROP TABLE` in a downgrade erases the audit record of the downgrade itself — the audit trail would corrupt itself.
- Downgrade for append-only tables is a no-op (`pass`) with a docstring explaining the rationale. If the migration is critical, downgrade may raise an explicit error instead.

**MigrationService self-healing:**
- MigrationService checks whether each applied migration exists in the database and re-applies missing ones on retry.
- `CREATE TABLE IF NOT EXISTS` makes re-application safe — a table that already exists is silently skipped, not an error.
- Without `IF NOT EXISTS`, a retry of a partially-applied migration would fail with "table already exists".

**Alembic vs. aiosqlite separation:**
- Alembic + SQLAlchemy: schema management only (migration files, `run_startup_migrations()`).
- Raw aiosqlite: all runtime queries and writes after Phase 6.
- Migrations run at startup Phase 5, before the app connection opens at Phase 6. See `Startup Initialization Sequence` above.

**Code exemplars:**

`alembic/versions/d7a1b2c3e4f5_add_migration_history.py` — **canonical pattern** (lines 20–55): `CREATE TABLE IF NOT EXISTS` upgrade with index; no-op downgrade with rationale docstring explaining that the audit table must survive the operation it is auditing.

```python
# upgrade (lines 28–43) — idempotent creation
op.execute("""
    CREATE TABLE IF NOT EXISTS migration_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ...
        status TEXT NOT NULL DEFAULT 'applied'
    )
""")
op.execute(
    "CREATE INDEX IF NOT EXISTS idx_migration_history_applied_at "
    "ON migration_history(applied_at)"
)

# downgrade (lines 46–55) — no-op; audit must survive the rollback
def downgrade() -> None:
    """Intentionally preserve migration_history on downgrade.
    ...audit must survive the operation it is auditing..."""
    # no-op: see docstring
```

`alembic/versions/44c6bfb6188e_add_audit_log.py` — **older style, do not repeat** (lines 20–44): `CREATE TABLE audit_log (...)` without `IF NOT EXISTS` (vulnerable to "table already exists" on retry); `DROP TABLE IF EXISTS audit_log` in downgrade (destroys audit data on rollback).

**Process rule:** See `AGENTS.md → Migration Safeguard Rule` for the actionable constraint.

### Phase-7-Managed Tables: Encoder Cache Exception

The `encoder_cache` table is an exception to the standard Alembic-managed migration pattern. It is
created by `create_tables_async()` at startup **Phase 7** (`src/stoat_ferret/db/schema.py:304`), not
by any Alembic migration revision. Its full lifecycle — creation, clearing, and schema evolution — is
managed by application code (`src/stoat_ferret/render/encoder_cache.py`,
`src/stoat_ferret/db/schema.py`).

**Why this matters for migrations:**

Alembic migrations run at Phase 5, *before* `create_tables_async()` creates the `encoder_cache` table
at Phase 7. On a fresh install, the table does not yet exist when migrations execute. Any migration
that reads from or writes to `encoder_cache` without an existence guard will fail on fresh installs
with "no such table: encoder_cache".

**Required pattern — `sqlite_master` existence guard:**

Any migration that references `encoder_cache` MUST include a `sqlite_master` existence check before
operating on the table:

```python
bind = op.get_bind()
result = bind.execute(
    sa.text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='encoder_cache'"
    )
)
if result.fetchone() is not None:
    op.execute("DELETE FROM encoder_cache")  # or other DDL/DML
```

The existence check makes the migration safe on both fresh installs (table absent → skip) and
upgraded deployments (table present → apply operation).

**Canonical pattern exemplar:**

`alembic/versions/8cba156be54c_clear_encoder_cache.py` — The upgrade function uses the
`sqlite_master` guard (lines 33–40) before deleting poisoned rows; the downgrade is a no-op (rows
are ephemeral cache data). This is the canonical reference for conditional DDL against Phase-7-managed
tables.

**Do not manage `encoder_cache` schema via Alembic:**

Do not attempt to `CREATE TABLE encoder_cache` in any migration. The table schema is owned by
`create_tables_async()` in `src/stoat_ferret/db/schema.py`. Migrations may only read from or write
to `encoder_cache` after verifying its existence via the `sqlite_master` guard above.

### Structured Logging & Event Naming

All structured log calls follow the pattern `logger.info("event_name", key=value)` using structlog. The event name is the primary indexing dimension for log queries and dashboards — it must be deliberate, stable, and categorized by namespace.

**Event Namespace Taxonomy:**

| Namespace | Category | Purpose | Examples |
|-----------|----------|---------|----------|
| `deployment.*` | Infrastructure | Operational state changes: startup, migrations, feature flag recording | `deployment.startup`, `deployment.migration`, `deployment.feature_flag` |
| `synthetic.*` | Infrastructure | Synthetic monitoring probes: health checks, check results | `synthetic.task_started`, `synthetic.health_degraded`, `synthetic.check_failure` |
| `schema.*` | Infrastructure | Schema consistency checks | `schema.unknown_resource` |
| `preview.*` | Domain | Preview workflow WebSocket events | `preview.generating`, `preview.ready`, `preview.error` |
| `proxy.*` | Domain | Proxy workflow WebSocket events | `proxy.ready` |
| `render.*` | Domain | Render workflow events (endpoint-level) | `render.validation_failed` |
| `render_worker.*` | Domain | Render worker operational events (command building, segment handling, worker lifecycle) | `render_worker.multi_segment_truncated` |
| `testing.*` | Domain (gated) | Testing/debug operations behind feature flag | `testing.seed.created`, `testing.seed.forbidden` |
| `qc.*` | Domain | QC analysis pass lifecycle events | `qc.started`, `qc.check_completed`, `qc.completed` |
| (no namespace) | Domain background | High-volume background job lifecycle events | `batch_submitted`, `job_completed`, `scan_video_added`, `thumbnail_strip_generation_queued` |

**Namespace boundaries:**

- **Infrastructure namespaces** (`deployment.*`, `synthetic.*`, `schema.*`) are reserved for events that reflect system state, not user-initiated workflows. Use `deployment.*` for startup and migration events; `synthetic.*` for monitoring probes; `schema.*` for schema consistency validation.
- **Domain namespaces** (`preview.*`, `proxy.*`, `render.*`, `testing.*`) are used for user-visible workflows. Each domain namespace maps to a feature area, not a code module.
- **No-namespace events** are used for background job lifecycle events (batch, job, scan, thumbnail operations). These fire at high volume on every item or job cycle; omitting the namespace reduces prefix overhead and keeps log queries that filter by namespace free of background job churn. This is a deliberate convention, not an oversight.

**Naming stability:**

Event names are part of the observability contract. Once a name is published to production, renaming it breaks log queries, dashboards, and alerting rules. Choose namespace and event names for long-term stability — optimize for human-readable filtering, not code structure.

**Declaration-before-use rule:**

New namespaces must be declared in this section before the namespace is first used in code. The process is:

1. Propose the new namespace in the PR description, explaining what category of events it covers and why no existing namespace fits.
2. Add the namespace to the taxonomy table in this section and merge to main.
3. Use the namespace in code only after the FRAMEWORK_CONTEXT.md update is merged.

Ad-hoc event names without an approved namespace are not permitted. No new namespaces were introduced in v046; the taxonomy above describes all namespaces verified in production code as of 2026-04-29.

**Code exemplars:**

- `deployment.startup` — `src/stoat_ferret/api/app.py:308` (Phase 13 gate cleared)
- `synthetic.task_started` — `src/stoat_ferret/api/app.py:335` (synthetic monitoring start)
- `synthetic.health_degraded` — `src/stoat_ferret/api/services/synthetic_monitoring.py:207`
- `preview.generating`, `preview.ready`, `preview.error` — `src/stoat_ferret/api/websocket/events.py` (EventType enum)
- `schema.unknown_resource` — `src/stoat_ferret/api/routers/schema.py`
- `testing.seed.created` — `src/stoat_ferret/api/routers/testing.py`
- `batch_submitted` — `src/stoat_ferret/api/routers/batch.py:191` (no-namespace exemplar)

**Process rule:** See `AGENTS.md → Event Namespace Rule` for the actionable constraint.

---

## 4. Banned or Discouraged Patterns

| Anti-pattern | Instead use | Reason |
|-------------|-------------|--------|
| `builtins.TimeoutError` after `asyncio.wait_for()` | `asyncio.TimeoutError` | Distinct types in Python 3.10; not unified until 3.11 |
| `unwrap()` in Rust library code | `PyResult<T>` / `?` operator | Panics surface in Python as unrecoverable crashes |
| Regenerating `_core.pyi` from scratch | Restore from main, add new classes only | `stub_gen` strips method bodies |
| `maturin develop --manifest-path …` | `maturin develop` from project root | Creates conflicting package in site-packages |
| `nul` in Git Bash (Windows) | `/dev/null` | Creates a literal file named `nul` |
| Editing FRAMEWORK_CONTEXT.md from non-002 tasks | Raise a Maintenance Trigger | Content ownership reserved for task 002 (LRN-242) |
| `hatchling` build backend for Rust wheel | `maturin` build backend | hatchling cannot produce the compiled extension |

---

## 5. Active Migration Debt Summary

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| Build backend: hatchling → maturin | Deferred | Medium | Needed for distributable Rust wheel; `maturin develop` still works for local builds. |
| SQLAlchemy ORM (direct use) | Not planned | Low | Present only via alembic; raw aiosqlite used in app code. No ORM migration planned. |

---

## 6. Maintenance Trigger

Status: idle
Next Quarterly Review: 2026-08-04

---

## 7. Document Map

No split files required.

---

## 8. Review Metadata

| Field | Value |
|-------|-------|
| Last Updated | 2026-05-20 |
| Next Quarterly Review | 2026-08-04 |
| Updated By | v067 / feature-executor (encoder-cache-doc) |
| Source Version/Design Reference | comms/outbox/versions/design/v067/source-intent-ledger.json |
