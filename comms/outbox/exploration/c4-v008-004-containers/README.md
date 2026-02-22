# C4 Container Synthesis — Task 004 (v008)

The v008 container architecture remains the same 5-container structure as v007 (3 runtime, 1 embedded database, 1 filesystem storage), with delta updates applied to reflect the effect workshop completion, WCAG AA accessibility, configurable WebSocket heartbeat, and structured logging wired into lifespan startup. The OpenAPI specification was bumped to v0.8.0 with updated description. No new containers were introduced; all changes are refinements within existing container boundaries.

## Containers Identified: 5

1. **API Server** (runtime) -- FastAPI/uvicorn process hosting REST API, WebSocket (configurable heartbeat from `ws_heartbeat_interval` setting), background job worker, effects engine, structured logging wired into lifespan, and static GUI serving
2. **Web GUI** (build artifact) -- React SPA built with Vite; in v008 the effect workshop lifecycle (apply/edit/remove) is fully implemented, WCAG AA compliance verified via axe-core, expanded to 22 components, 8 hooks, 7 stores, 15 Playwright E2E tests
3. **Rust Core Library** (in-process library) -- PyO3 native extension compiled with maturin; no changes in v008
4. **SQLite Database** (embedded) -- File-based database at `data/stoat.db`, 5 Alembic migration versions; no changes in v008
5. **File Storage** (filesystem) -- Local directories for source videos and thumbnails; no changes in v008

## Infrastructure Files Found

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build: Stage 1 compiles Rust extension with maturin, Stage 2 creates slim Python 3.12 runtime with uv for testing |
| `docker-compose.yml` | Single `test` service with read-only source mounts for fast iteration |
| `.github/workflows/ci.yml` | CI with 5 jobs: path-filtered changes detection, 9-matrix test (3 OS x 3 Python), Rust coverage, frontend build+test, Playwright E2E with 5 WCAG AA + 7 effect lifecycle tests |
| `pyproject.toml` | Python project config with maturin build settings, entry point `python -m stoat_ferret.api` |
| `gui/package.json` | Frontend dependencies and build scripts (`npm run build` to `gui/dist/`) |
| `gui/vite.config.ts` | Vite config with API proxy for development (`/api`, `/health`, `/metrics`, `/ws` to port 8000) |
| `alembic.ini` + `alembic/versions/` | 5 database migration scripts for schema management |

## API Specifications Generated

| File | Description |
|------|-------------|
| `docs/C4-Documentation/apis/api-server-api.yaml` | OpenAPI 3.1 spec v0.8.0 -- 24 REST endpoints across 6 tag groups (Health, Videos, Projects, Clips, Effects, Transitions, Jobs); description updated to reflect configurable WebSocket heartbeat and structured logging startup |

## Delta Changes from v007

| Container | v007 | v008 Change |
|-----------|------|-------------|
| API Server | REST + WebSocket, effects CRUD, job worker | Added: `ws_heartbeat_interval` and `debug` settings wired via lifespan; `configure_logging()` called on startup for structured JSON/console output; no new endpoints |
| Web GUI | Effect workshop (basic); basic accessibility | Effect workshop: full apply/edit/remove lifecycle; WCAG AA compliance via axe-core; expanded to 22 components, 8 hooks, 7 stores; E2E suite grew to 15 tests (5 WCAG AA + 7 effect lifecycle + 3 navigation/scan) |
| Rust Core Library | Unchanged | No v008 changes |
| SQLite Database | Unchanged | No v008 changes |
| File Storage | Unchanged | No v008 changes |
| OpenAPI spec | v0.7.0, 24 endpoints | v0.8.0, same 24 endpoints; description updated |

## Key Architectural Observations (Unchanged from v007)

- **Single-process monolith**: The API Server is the only runtime process. The Rust core library, SQLite database, and job queue all run in-process.
- **Docker is test-only**: The Dockerfile and docker-compose.yml are configured exclusively for running the test suite, not for production deployment.
- **No production deployment config**: No Kubernetes manifests, Terraform, or cloud deployment configs. The system runs as a local development application.
- **Embedded scaling constraints**: SQLite single-writer and in-process asyncio job queue prevent horizontal scaling, appropriate for the current single-user local application use case.
