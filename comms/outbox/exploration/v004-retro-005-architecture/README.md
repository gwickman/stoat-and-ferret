# Architecture Alignment Check — v004

No additional architecture drift detected. The primary architecture document (`docs/design/02-architecture.md`) was updated during v004 Theme 03 Feature 3 (scan-doc-updates) to reflect the async scan endpoint, job queue infrastructure, and updated data flows. Formal C4 documentation does not exist and is tracked by existing backlog item BL-018, which has been updated with v004 component details.

## Existing Open Items

- **BL-018**: "Create C4 architecture documentation" (P2, open, tags: documentation/architecture/c4). Description: No C4 architecture documentation currently exists. Notes updated with v004 component inventory.

## Changes in v004

v004 delivered 5 themes and 15 features focused on testing infrastructure and quality verification. The architecturally significant changes were:

- **Async job queue** (Theme 03): Replaced synchronous `POST /videos/scan` with async pattern returning `202 Accepted` + job ID. New `AsyncioJobQueue` using `asyncio.Queue` with background worker coroutine, handler registration (`register_handler()`), per-job timeout via `asyncio.wait_for()`, and FastAPI lifespan integration.
- **Job status endpoint** (Theme 03): Added `GET /api/v1/jobs/{job_id}` for polling job status (pending/running/complete/failed/timeout).
- **Security configuration** (Theme 04): Added `ALLOWED_SCAN_ROOTS` environment variable with `validate_scan_path()` enforcement in the Python scan service. Rust handles low-level input sanitization; Python handles business policy.
- **DI pattern** (Theme 01): Formalized `create_app()` constructor-based dependency injection replacing `dependency_overrides`. Dependencies resolved via `app.state` with production fallbacks.
- **InMemory test doubles** (Theme 01): `InMemoryVideoRepository`, `InMemoryJobQueue` with deepcopy isolation and synchronous seed helpers.
- **Docker infrastructure** (Theme 05): Multi-stage Dockerfile (Rust builder + Python runtime) and docker-compose for local development.
- **CI additions** (Theme 05): Rust code coverage via `cargo-llvm-cov` at 75% threshold (target: 90%).
- **Design docs added** (Theme 04): `09-security-audit.md`, `10-performance-benchmarks.md`.
- **Design docs updated** (Theme 03): `02-architecture.md`, `03-prototype-design.md`, `04-technical-stack.md`, `05-api-specification.md` updated to reflect async scan behavior.

## Documentation Status

| Document | Exists | Currency |
|----------|--------|----------|
| `docs/design/02-architecture.md` | Yes | Updated during v004 (Theme 03 Feature 3) — reflects async scan, job queue, updated data flows |
| `docs/design/03-prototype-design.md` | Yes | Updated during v004 |
| `docs/design/04-technical-stack.md` | Yes | Updated during v004 |
| `docs/design/05-api-specification.md` | Yes | Updated during v004 |
| `docs/design/09-security-audit.md` | Yes | Created during v004 |
| `docs/design/10-performance-benchmarks.md` | Yes | Created during v004 |
| `docs/C4-Documentation/` | No | Never created |
| `docs/ARCHITECTURE.md` | No | Does not exist (architecture is in `docs/design/02-architecture.md`) |

## Drift Assessment

No additional architecture drift detected between v004 changes and the documented architecture.

The primary architecture document (`02-architecture.md`) was proactively updated during v004 Theme 03 Feature 3 to capture:
- Job queue section with `asyncio.Queue` implementation details
- `/jobs` endpoint group in the API layer
- Async video import flow diagram (202 Accepted pattern)
- `InMemoryJobQueue` testing strategy
- Python layer responsibilities updated to include "Job queue orchestration (asyncio.Queue)"

The only documentation gap is the absence of formal C4 documentation (Context, Container, Component, Code level), which predates v004 and is already tracked by BL-018.

## Action Taken

Updated existing backlog item **BL-018** with notes documenting the v004 components that should be captured when C4 documentation is created: AsyncioJobQueue, job status endpoint, ALLOWED_SCAN_ROOTS, DI pattern, InMemory test doubles, Docker infrastructure, and Rust coverage CI. No new backlog item was created since BL-018 already covers this gap.
