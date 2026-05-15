# FRAMEWORK_CONTEXT.md

## 1. Purpose and Scope

This document provides current framework guidance for stoat-and-ferret design and development. It covers:
- **Dependency versions** and ranges (Python, Rust, Node)
- **Preferred patterns** canonized in AGENTS.md
- **Banned patterns** with rationale and alternatives
- **Active migration debt** with priority
- **Maintenance triggers** for periodic review

This is the single source of truth for framework decisions across all design and execution phases. Design tasks reference this document; other tasks read it for constraints but do not edit it directly. If framework issues are discovered, raise a pending Maintenance Trigger rather than editing directly.

---

## 2. Current Framework Stack

| Layer | Framework/Tool | Version Range | Key Pattern | Constraints |
|-------|---|---|---|---|
| **Python Web** | FastAPI | 0.109+ | Routes in routers/; DI via app.state | OpenAPI schema sync required |
| **Python Web** | Uvicorn | 0.27+ | Standard extras for full ASGI | Production ASGI server |
| **Python DB** | SQLAlchemy + aiosqlite | Latest | Async ORM; Repository pattern | Must use async/await |
| **Python DB** | Alembic | 1.13+ | CREATE TABLE IF NOT EXISTS | Idempotency required |
| **Python Validation** | Pydantic | 2.0+ | Settings from STOAT_* env vars | Dual documentation required |
| **Python Validation** | pydantic-settings | 2.0+ | Environment variable parsing | Configuration audit tracked |
| **Python Logging** | structlog | 24.0+ | logger = structlog.get_logger(__name__) | Approved namespace only |
| **Python QA** | Ruff | 0.4+ | E, F, I, UP, B, SIM, ASYNC | 100-char line limit, py310 target |
| **Python QA** | MyPy | 1.10+ | strict=true, disallow_untyped_defs | Type hints on all public funcs |
| **Python QA** | Pytest | 8.0+ | asyncio_mode=auto; inject via state | 80% coverage minimum |
| **Python Build** | Hatchling | Latest | Package building | Standard Python wheel format |
| **Python Build** | Maturin | 1.0+ | PyO3 compilation | Must run from project root |
| **Rust Bindings** | PyO3 | 0.26 | abi3-py310; py_* prefix pattern | Stubs manually maintained |
| **Rust Bindings** | pyo3-stub-gen | 0.17 | Generate .pyi stubs | Regenerate after API changes |
| **Rust Core** | Regex | 1.x | FFmpeg filter syntax | Standard Rust patterns |
| **Rust Core** | Criterion | 0.5 | Benchmarking with HTML reports | Optional feature |
| **Frontend** | React | 19.2.0 | Component-based UI | Functional components + hooks |
| **Frontend** | TypeScript | 5.9.3 | Strict type checking | tsconfig orchestrates app/node |
| **Frontend** | Vite | 7.3.1 | Build tool; dev proxies to :8765 | Modern ES module bundler |
| **Frontend** | Tailwind CSS | 4.1.18 | Utility-first styling | @tailwindcss/vite plugin |
| **Frontend** | Vitest | 4.0.18 | Unit testing | ESM-first test runner |
| **Frontend** | ESLint | 9.39.1 | Code linting | typescript-eslint integration |

---

## 3. Preferred Patterns

### Python

- **Dependency Injection**: Services instantiated in lifespan(), stored on app.state
- **Structured Logging**: `logger.info("event_name", key=value)` with approved namespace prefix
- **Database Access**: Repository pattern; all async using aiosqlite + SQLAlchemy
- **Configuration**: Read from STOAT_* environment variables via pydantic-settings
- **Type Hints**: Required on all public functions; use `from __future__ import annotations` for forward references
- **Testing**: asyncio_mode="auto"; inject mocks via app.state before setting _deps_injected=True
- **Error Handling**: Return Result<T, E> from services; let FastAPI exception handlers convert to HTTP status

### Rust

- **PyO3 Bindings**: Use `py_` prefix for binding methods; expose clean names with `#[pyo3(name = "...")]`
- **Error Handling**: Use Result<T, E>; no unwrap() in library code
- **Documentation**: All public items must have doc comments
- **Testing**: Property-based tests (proptest) for complex logic; criterion for performance

### Frontend (React + TypeScript)

- **State Management**: Zustand for global state; props for component-local state
- **API Integration**: openapi-typescript for type generation; regenerate after API changes
- **Routing**: React Router DOM for client-side routing
- **Styling**: Tailwind CSS utilities; no custom CSS unless utility approach insufficient
- **Testing**: Vitest for unit tests; @playwright/test for E2E tests; axe-core for accessibility (see Accessibility Testing subsection below)
- **Progress Transport**: Batch uses HTTP polling via `useBatchJobs`; render/preview/proxy use WebSocket push (see Batch Progress Transport subsection below)

### Accessibility Testing — Baseline Scanning Strategy

This section formalizes when to run fresh axe-core baseline scans vs. fallback to prior version known violations, based on patterns observed in v052–v053 accessibility feature implementations. It provides a single decision tree and checklist for feature implementers.

#### Decision Tree

Use this tree before implementing any feature that creates or modifies UI components:

**Step 1: Is a running development server available?**
- **YES** → Run a fresh axe-core baseline scan before implementation begins. Document all violations in the completion report. This is the preferred approach — it eliminates ambiguity about whether violations are new or pre-existing. Proceed to implementation.
- **NO** → Proceed to Step 2.

**Step 2: Are v_N-1 known violations documented (in a prior completion report or accessibility audit)?**
- **YES** → Prior-version fallback is available. Proceed to Step 3 to confirm it applies to this feature.
- **NO** → **Risk: baseline unknown.** No documented prior violations means any violation found may be pre-existing or new. Document in quality-gaps.md as "accessibility: baseline unknown." Proceed to Step 3 with elevated risk.

**Step 3: Is this feature adding new routes or views?**
- **YES** → **Fresh axe-core scan is required** regardless of the outcome of Steps 1–2. Prior-version violations do not cover new routes. If a running server is currently unavailable, delay the baseline scan until one is available, and document the gap in quality-gaps.md. Do not proceed without either a fresh scan or a documented deferral.
- **NO** → Prior-version violations are sufficient as the baseline. Note the assumption in the completion report: *"Baseline inherited from v_N-1. No fresh scan run; feature adds no new routes."* Any violation found above this baseline is treated as a new regression.

#### Risk Notation

| Scenario | Risk Level | Rationale |
|----------|-----------|-----------|
| Fresh scan run before implementation | Low | Complete violation inventory; regressions are detectable |
| Prior-version violations used; no new routes | Medium | Other features in the same version may have introduced violations not yet catalogued |
| Prior-version violations used; new routes added | High | Prior violations do not cover new routes; new violations undetectable |
| No prior violations documented; no fresh scan | High | Baseline unknown; cannot distinguish new from pre-existing violations |

#### Violation Triage: Suppression vs. Remediation

When violations are found, classify each as follows:

- **Remediate immediately**: The violation is an accessibility bug with no design justification (e.g., missing `alt` text, broken focus order, contrast ratio below WCAG 2.1 AA minimum). Fix before completing the feature.
- **Suppress as documented design debt**: The violation is an accepted design constraint that cannot be remediated in the current sprint. Suppression requires:
  1. A comment in the relevant test file or axe configuration explaining the suppression reason.
  2. An entry in the feature's completion report noting the suppressed violation, its impact, and a backlog item for future remediation.
  3. **Do not suppress `critical` or `serious` axe-core violations without product sign-off.**
- **Pre-existing (out of scope)**: Violation is confirmed pre-existing and unchanged by this feature. Note in the completion report as "pre-existing; no change."

#### Feature Implementation Checklist

For each feature that creates or modifies UI components:

- [ ] **Review prior-version violations**: Check the previous version's completion report or accessibility audit. Note the inherited baseline violations (if any).
- [ ] **Apply the decision tree**: Determine whether a fresh axe-core baseline scan is required (see Decision Tree above).
- [ ] **Run fresh scan (if required or server available)**: Start the dev server and run the axe-core accessibility scan (e.g., `npx playwright test --grep axe` or via `npm run uat`). Document all violations found.
- [ ] **Inherit prior-version baseline (if applicable)**: Note in the completion report: *"Baseline inherited from v_N-1. No fresh scan run; feature adds no new routes."*
- [ ] **Triage violations**: For each violation, classify as: remediate immediately / suppress as documented design debt / pre-existing (out of scope).
- [ ] **Document in completion report**: Include (1) violations found, (2) classification, and (3) remediation action taken or backlog item created.

---

### Batch Progress Transport

This section identifies which progress channels use WebSocket push versus HTTP polling. The distinction matters for test authors and feature implementers: incorrect transport assumptions produce unverifiable test requirements (see v053 NFR-001 for a concrete example).

#### Transport Channel Summary

| Channel | Transport | Namespace / Hook | Notes |
|---------|-----------|-----------------|-------|
| Render progress | WebSocket push | `render.*` | Server-pushed; client subscribes via WebSocket connection |
| Preview progress | WebSocket push | `preview.*` | Server-pushed; client subscribes via WebSocket connection |
| Proxy progress | WebSocket push | `proxy.*` | Server-pushed; client subscribes via WebSocket connection |
| Batch progress | HTTP polling | `useBatchJobs` hook | Client-initiated; **no WebSocket events emitted** |

#### Batch Progress via HTTP Polling

Batch job progress uses HTTP polling, not WebSocket push. The `useBatchJobs` hook (`gui/src/hooks/useBatchJobs.ts`) implements:

- **Normal polling cadence**: 1 second (`NORMAL_INTERVAL_MS = 1000`, line 10)
- **Exponential backoff on error**: 1 s → 2 s → 4 s, capped at 10 seconds (`MAX_BACKOFF_MS = 10_000`, line 14)
- **Polling endpoint**: `GET /api/v1/render/batch/{batchId}` (line 135)
- **Automatic termination**: Polling stops when all jobs reach a terminal status (`completed`, `failed`, `cancelled`)
- **No WebSocket events**: Batch progress does not emit WebSocket events and does not participate in the ConnectionManager WebSocket replay buffer (`replay_buffer_size`, `replay_ttl_seconds`)

#### WebSocket Replay Buffer Exclusion

The ConnectionManager replay buffer (`replay_buffer_size`, `replay_ttl_seconds`) stores and re-delivers `render.*` and `preview.*` events for clients that reconnect mid-stream. Batch progress does not use WebSocket transport and is excluded from the replay buffer. "Rejoin mid-stream" test scenarios apply to render/preview channels only, not batch.

#### Test Authoring Guidance

**Batch progress tests must assert on HTTP polling behavior, not WebSocket events.**

- Mock or intercept `GET /api/v1/render/batch/{batchId}` to control test state
- Do not assert on WebSocket event streams for batch progress (no such events exist)
- Polling timing can be tested by controlling `NORMAL_INTERVAL_MS` and advancing fake timers

Cross-reference: `useBatchJobs` hook is documented in the GUI hooks C4 reference (`docs/design/c4/c4-code-gui-hooks.md`).

---

### render_jobs API Ordering Constraint

The `render_jobs` API must be queried in creation order for reproducible queue semantics. The endpoint returns jobs in `created_at, id ASC` order, which reflects the intended execution sequence.

**Constraint**: Any batch processing loop that reads render jobs must preserve the creation-order sequence returned by the API. Reordering or sorting by a different field (e.g., priority, status) breaks reproducibility — the same input set produces different execution sequences across runs, making debugging and retry workflows unpredictable.

**Discovery**: This constraint was identified in the v058 retrospective after observing non-deterministic batch execution behavior when job lists were consumed out of creation order.

**Cross-reference**: Render job batch endpoints are documented in `docs/design/05-api-specification.md`. The underlying repository query uses `ORDER BY created_at, id ASC` to enforce this constraint at the database layer. `created_at` is the primary ordering dimension; `id ASC` serves as a deterministic tie-break for same-millisecond inserts (SQLite millisecond resolution means concurrent writes can share a timestamp).

---

### Structured Logging — render_worker.* Events

This section declares the `render_worker.*` event namespace introduced in v055 (PRs #373–#375, 2026-05-03) and documents all events emitted by the background render worker loop (`src/stoat_ferret/render/worker.py`). The namespace was used in production before formal declaration was completed; v057 completes the governance process.

Cross-reference: See AGENTS.md — Structured Event Naming for the full approved namespace taxonomy and the declaration-before-use process.

#### Namespace Declaration

| Namespace | Category | Purpose |
|-----------|----------|---------|
| `render_worker.*` | Domain | Render worker lifecycle events and execution errors |

#### Event Reference

| Event | Severity | When Fired |
|-------|----------|------------|
| `render_worker.started` | `info` | Worker loop enters main `run()` coroutine |
| `render_worker.stopped` | `info` | `asyncio.CancelledError` caught; graceful shutdown |
| `render_worker.multi_segment_truncated` | `warning` | `render_plan` contains >1 segment; only the first segment is executed |
| `render_worker.job_failed` | `error` | Job execution raised an exception (command build or `run_job` failure) |
| `render_worker.error` | `error` | Failure handler raised an exception, or repository `update_status` failed (2 call sites in `_handle_job_error`) |

All 5 events are emitted by `RenderWorkerLoop` in `src/stoat_ferret/render/worker.py`. `render_worker.error` fires at two distinct call sites within `_handle_job_error()`: once when `_handle_failure()` raises (line 228), and once when `_repo.update_status()` raises (line 241).

---

## 4. Banned or Discouraged Patterns

| Pattern | Why | Instead Use |
|---------|-----|-------------|
| `asyncio.TimeoutError` catch without qualification | Python 3.10: two types (asyncio vs builtins). Caught separately. | Import asyncio.TimeoutError explicitly for Python 3.10 compat |
| unwrap() in Rust library code | Panics crash the process; opaque error context | Result<T, E>; custom error types with context |
| Modifying FRAMEWORK_CONTEXT.md outside Task 002 | Governance: single task responsible for consistency | Raise pending Maintenance Trigger; Task 002 applies the update |
| CREATE TABLE / DROP TABLE in migrations without IF NOT EXISTS | Non-idempotent on retry; corrupts audit trail | CREATE TABLE IF NOT EXISTS; idempotent upgrades |
| Inline Maintenance Trigger updates | State collision; trigger parsing errors | Use MCP tools (save_learning, add_backlog_item) to record issues |
| Hand-coded type stubs for Rust API | Stale stubs cause TypeErrors; stub-gen prevents gaps | Regenerate stubs via cargo run --bin stub_gen after API changes |
| Ad-hoc event naming (no namespace) | Breaks log queries and dashboards if renamed | Use approved namespace (deployment.*, synthetic.*, etc.) or no prefix for background jobs |
| Direct database writes before Phase 5 (Alembic) | Schema state undefined; migration failures | Initialize services after Phase 5; check AGENTS.md §Startup Ordering |
| Ignoring OpenAPI schema sync | CI failure; API contract drift | Run `uv run python -m scripts.export_openapi` before push |

---

## 5. Active Migration Debt Summary

**Status: None identified.**

The framework stack is current and patterns are well-established. No legacy compatibility shims or tech debt items require prioritization.

---

## 6. Maintenance Trigger

Status: idle
Next Quarterly Review: 2026-07-30

---

## 7. Document Map

No split files. Main FRAMEWORK_CONTEXT.md contains all required content within size constraints (~240 lines).

---

## 8. Review Metadata

| Field | Value |
|-------|-------|
| Last Updated | 2026-05-04 |
| Next Quarterly Review | 2026-07-30 |
| Updated By | v057-feature-005 |
| Source Version/Design Reference | docs/auto-dev/versions/v057/02-framework-context-additions/003-render-worker-namespace |

