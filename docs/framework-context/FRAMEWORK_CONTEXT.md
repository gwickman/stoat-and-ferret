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
- **Testing**: Vitest for unit tests; @playwright/test for E2E tests

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

No split files. Main FRAMEWORK_CONTEXT.md contains all required content within size constraints (212 lines, 5.2 KB).

---

## 8. Review Metadata

| Field | Value |
|-------|-------|
| Last Updated | 2026-04-30 |
| Next Quarterly Review | 2026-07-30 |
| Updated By | v048-design-002 |
| Source Version/Design Reference | docs/auto-dev/versions/v048/002-framework-context-analysis |

