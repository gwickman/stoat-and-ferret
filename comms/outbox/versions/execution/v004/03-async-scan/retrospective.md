# Theme Retrospective — 03: Async Scan Infrastructure

## Theme Summary

Theme 03 replaced the synchronous blocking `POST /videos/scan` endpoint with an async job queue pattern, enabling non-blocking API behavior and progress tracking. Three features were delivered sequentially, each building on the previous:

1. **Job queue infrastructure** — `AsyncioJobQueue` implementation using `asyncio.Queue` producer-consumer pattern with background worker, configurable per-job timeout (default 5 minutes), and FastAPI lifespan integration
2. **Async scan endpoint** — Refactored `POST /videos/scan` to return `202 Accepted` with a `job_id`, added `GET /api/v1/jobs/{job_id}` for status polling, and migrated all scan tests to the async submit-and-poll pattern
3. **Scan doc updates** — Updated four design documents (`02-architecture.md`, `03-prototype-design.md`, `04-technical-stack.md`, `05-api-specification.md`) to reflect async scan behavior and job queue architecture

All three features passed quality gates (ruff, mypy, pytest) and met their acceptance criteria. The theme added 19 new tests, growing the suite from 507 to 529 passing tests (with existing scan tests migrated to the async pattern) while maintaining 93% coverage.

## Feature Results

| # | Feature | Acceptance | Quality Gates | Tests Added | Status |
|---|---------|------------|---------------|-------------|--------|
| 1 | job-queue-infrastructure | 6/6 PASS | All PASS | 14 | Complete |
| 2 | async-scan-endpoint | 5/5 PASS | All PASS | 5 | Complete |
| 3 | scan-doc-updates | 4/4 PASS | All PASS | 0 (docs only) | Complete |

**Totals:** 15/15 acceptance criteria passed. 19 new tests. 0 regressions.

## Key Learnings

### What Went Well

- **Sequential feature chain worked cleanly.** Features had strict sequential dependencies (queue -> endpoint -> docs) and the handoff documents between features provided clear context. The `handoff-to-next.md` from Feature 1 explicitly documented the API surface, handler registration pattern, and testing approach for Feature 2.
- **`asyncio.Queue` over external dependencies was the right call.** Using the stdlib `asyncio.Queue` instead of Redis/arq eliminated an external dependency entirely. The single-worker producer-consumer pattern is sufficient for current scale and keeps the deployment footprint minimal.
- **InMemoryJobQueue enabled deterministic test execution.** Feature 2 registered real scan handlers on `InMemoryJobQueue` (which executes jobs synchronously at submit time), allowing tests to verify the full async flow without actual background workers or timing issues.
- **Theme 01 DI pattern extended naturally.** The `create_app(job_queue=...)` injection pattern established in earlier themes absorbed the job queue dependency without friction. Both `conftest.py` files (API and blackbox) gained queue injection with minimal boilerplate.

### Patterns Discovered

- **Handler registration over configuration.** The `register_handler()` method pattern allows job types to be wired to async functions at startup. This avoids a handler registry module and keeps job routing explicit. Jobs submitted without a registered handler fail immediately with a clear error.
- **`make_scan_handler()` factory for dependency injection.** Rather than the scan handler reaching into `app.state` for repositories, a factory function captures dependencies at registration time. This keeps the handler testable in isolation.
- **No separate worker module needed.** The `process_jobs()` coroutine lives as a method on `AsyncioJobQueue` since it needs direct access to the internal queue and job dict. Splitting it out would require exposing internals unnecessarily.

### What Could Improve

- **No quality-gaps documents were generated.** The retrospective prompt referenced `quality-gaps.md` files per feature, but none were produced during execution. The completion reports served as the primary quality record instead (same gap noted in Theme 02).
- **Test count growth was modest.** 19 new tests is lower than Theme 02's 58 because much of Feature 2's work was migrating existing scan tests rather than writing new ones. The existing tests still exercise the async pattern, but the migration work isn't reflected in net-new test count.

## Technical Debt

| Item | Source | Priority | Notes |
|------|--------|----------|-------|
| Single worker limits concurrency | Feature 1 | Low | One job at a time is sufficient for current scale; add worker pool if scan volume grows |
| No job expiration or cleanup | Feature 1 | Low | Completed/failed jobs remain in memory indefinitely; add TTL-based cleanup if memory becomes a concern |
| No job cancellation API | Feature 2 | Low | `DELETE /jobs/{id}` not implemented; add if users need to cancel long-running scans |
| Timeout value (5 min) is a guess | Feature 1 | Low | Default based on risk assessment (U1); tune based on real-world scan durations |

## Recommendations

1. **For future job types:** The `AsyncioJobQueue` and handler registration pattern are generic. New job types (e.g., batch import, transcode) can be added by implementing a handler and calling `register_handler()` at startup — no queue changes needed.
2. **For scaling:** If concurrent job execution is needed, the single `process_jobs()` worker can be replaced with a worker pool spawning multiple `asyncio.create_task()` consumers. The queue protocol and status tracking would remain unchanged.
3. **For production readiness:** Consider adding job persistence (write pending/running jobs to SQLite) so jobs survive app restarts. Currently all state is in-memory and lost on shutdown.
4. **Quality-gaps generation:** Consider making `quality-gaps.md` a required output of feature execution. This is the second consecutive theme where it was missing.

## Metrics

- **Lines changed:** +1,151 / -188 across 19 source/test/doc files
- **Source files changed:** 7 (4 modified, 3 created)
- **Test files changed:** 7 (3 modified, 4 created)
- **Doc files changed:** 4 (all modified)
- **Final test count:** 529 passed, 14 skipped
- **Coverage:** 93%
- **Commits:** 3 (one per feature, via PR)
