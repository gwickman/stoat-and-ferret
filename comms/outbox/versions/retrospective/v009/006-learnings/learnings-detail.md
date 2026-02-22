# Learnings Detail - v009 Retrospective

## LRN-047: WAL Mode Enables Safe Mixed Sync/Async SQLite Access

**Tags:** pattern, sqlite, async, database, concurrency
**Source:** v009/01-observability-pipeline/002-audit-logging completion-report, v009/01-observability-pipeline retrospective

### Content

#### Context

When wiring components that require synchronous database access (e.g., audit loggers) into an application that uses asynchronous database connections (aiosqlite), you need concurrent access to the same database from both sync and async code paths.

#### Learning

Open a separate synchronous `sqlite3.Connection` alongside the async `aiosqlite` connection to the same database file, with WAL (Write-Ahead Logging) mode enabled on both. WAL mode allows concurrent reads and writes from multiple connections without deadlocks.

#### Evidence

In v009, `AuditLogger` required synchronous `sqlite3` access while the app used `aiosqlite`. A separate sync connection with WAL mode was opened in the lifespan function. Concurrent tests confirmed no deadlocks occur. The sync connection is closed before the async connection during shutdown to maintain proper ordering.

#### Application

When adding components that need synchronous database access to an async application:
1. Open a separate sync connection with `sqlite3.connect()`
2. Enable WAL mode: `conn.execute("PRAGMA journal_mode=WAL")`
3. Close sync connection before async connection during shutdown
4. Use concurrent tests to verify no deadlocks under load

---

## LRN-048: Catch-All Routes Replace StaticFiles for SPA Fallback in FastAPI

**Tags:** pattern, fastapi, spa, routing, frontend
**Source:** v009/02-gui-runtime-fixes/001-spa-routing completion-report, v009/02-gui-runtime-fixes retrospective

### Content

#### Context

FastAPI's `StaticFiles` mount returns 404 for SPA sub-paths like `/gui/library` when users navigate directly or refresh the page. Single-page applications need all non-file paths to serve `index.html` for client-side routing to work.

#### Learning

Replace `StaticFiles` mounts with two catch-all FastAPI route handlers: one for the bare path (`/gui`) and one for all sub-paths (`/gui/{path:path}`). The sub-path handler checks if the requested path maps to an actual static file; if so, it serves it via `FileResponse`, otherwise it falls back to `index.html`.

#### Evidence

In v009, the SPA routing feature replaced `app.mount("/gui", StaticFiles(...))` with two `@app.get` handlers. This resolved direct navigation and page refresh on all GUI sub-paths while preserving static asset serving. The conditional `gui_dir.is_dir()` guard was maintained to keep the GUI optional.

#### Application

When serving a SPA from FastAPI:
1. Remove the `StaticFiles` mount
2. Add `@app.get("/prefix")` to serve `index.html` for the bare path
3. Add `@app.get("/prefix/{path:path}")` that checks `(prefix_dir / path).is_file()` before serving
4. Return `FileResponse(index_html_path)` as fallback for non-file paths
5. Keep the conditional directory guard to make the SPA optional
6. Consider adding cache-control headers for static assets

---

## LRN-049: Guard Optional Broadcast Calls to Avoid Runtime Crashes

**Tags:** pattern, websocket, dependency-injection, defensive-coding, testing
**Source:** v009/02-gui-runtime-fixes/003-websocket-broadcasts completion-report, v009/02-gui-runtime-fixes retrospective

### Content

#### Context

When adding event broadcasting (e.g., WebSocket notifications) to existing operations like record creation or background job completion, the broadcasting infrastructure may not always be available — particularly in tests, minimal deployments, or when the WebSocket manager hasn't been initialized.

#### Learning

Guard all broadcast calls with a simple `if manager:` check so they become a no-op when the broadcasting component is absent. This decouples event emission from core functionality and eliminates the need to mock or initialize broadcast infrastructure in unrelated tests.

#### Evidence

In v009, WebSocket broadcasts for `PROJECT_CREATED`, `SCAN_STARTED`, and `SCAN_COMPLETED` events were added with `if ws_manager:` guards. This allowed all existing tests to pass unchanged — only dedicated broadcast tests needed to set up the mock manager. No crashes occurred in contexts where `ws_manager` was not set.

#### Application

When adding optional notification/broadcast capabilities to existing operations:
1. Accept the broadcast dependency as an optional parameter
2. Guard every broadcast call with `if dependency:` before calling methods on it
3. This pattern avoids forcing all consumers to provide the dependency
4. Dedicated tests can inject a mock to verify broadcast behavior
5. Non-broadcast tests need no changes to their setup

---

## LRN-050: Incremental DI Wiring Is Fast and Low-Risk When Patterns Are Established

**Tags:** pattern, dependency-injection, process, planning, efficiency
**Source:** v009/01-observability-pipeline retrospective, v009 version retrospective

### Content

#### Context

Many applications accumulate dead code — components that are implemented but never wired into the runtime dependency injection chain. Wiring these components into the live application can be done as a dedicated activity once the DI pattern is well-established.

#### Learning

Features that wire existing, tested code into the DI chain follow a predictable pattern and complete quickly with minimal risk of regressions. When the DI pattern is established (add kwarg -> instantiate in lifespan -> store on app.state -> pass to dependents), each successive wiring feature is faster than the last. Consider batching similar DI wiring tasks into dedicated versions.

#### Evidence

In v009, all six features either wired existing components (Theme 01: FFmpeg observability, audit logging, file logging) or extended existing patterns (Theme 02: SPA routing, pagination, broadcasts). All 31 acceptance criteria passed with zero quality gate failures. Each feature in Theme 01 followed the identical DI wiring pattern, making the third feature noticeably faster than the first. Coverage stayed stable at ~92.9% throughout.

#### Application

When planning versions:
1. Identify dead code or unwired components in the codebase
2. Batch wiring tasks into a dedicated theme for compounding efficiency
3. Expect high first-iteration success rates for wiring features
4. Monitor kwarg count on factory functions — consider a DI container if it exceeds 6-7 parameters

---

## LRN-051: Add count() to Repository Protocols for Accurate Pagination

**Tags:** pattern, repository, pagination, api-design, database
**Source:** v009/02-gui-runtime-fixes/002-pagination-fix completion-report, v009/02-gui-runtime-fixes retrospective

### Content

#### Context

List endpoints that paginate results need an accurate total count to calculate page numbers. Using `len(page_results)` as the total returns the page size rather than the true database count, breaking pagination UI.

#### Learning

Add a `count()` method to repository protocols alongside `list()` for any entity type that supports pagination. Implement as `SELECT COUNT(*)` for SQLite and `len(self._store)` for InMemory. Call `count()` separately from `list()` in the endpoint to populate the total field accurately.

#### Evidence

In v009, the projects endpoint returned `total=len(projects)` which equaled the page size rather than the true count. Adding `count()` to `AsyncProjectRepository` protocol (mirroring the existing `AsyncVideoRepository.count()` pattern), implementing in both SQLite and InMemory backends, and wiring into the router fixed the pagination total.

#### Application

When adding a new repository protocol or noticing a list endpoint with pagination:
1. Add `count()` to the protocol definition
2. Implement `SELECT COUNT(*) FROM table` for SQLite
3. Implement `len(self._store)` for InMemory
4. Call `await repo.count()` in the endpoint, not `len(results)`
5. Add contract tests verifying count accuracy across implementations

---

## LRN-052: Run Formatter Before Linter to Avoid Double Fix Cycles

**Tags:** process, tooling, ruff, code-quality, efficiency
**Source:** session analytics (v009 period)

### Content

#### Context

When implementing features, code is written and then quality gates are run. Session analytics show that nearly every v009 implementation session encountered ruff format failures on the first quality gate run, followed by ruff check import-ordering failures — requiring multiple fix-and-rerun cycles.

#### Learning

Run `ruff format` before `ruff check` during local development. Format failures cause sibling tool call errors in parallel quality gate runs, and import-ordering violations (I001) are often side effects of unformatted code. Running the formatter first eliminates a class of linter errors and reduces fix cycles.

#### Evidence

Session analytics for v009 show recurring error patterns: `ruff format --check` failures for newly-written test files and `ruff check` I001 import-ordering violations. These appeared in nearly every feature implementation session as the first quality gate run, requiring at least one fix-and-rerun cycle each time.

#### Application

In implementation workflows:
1. Run `ruff format` first after writing/modifying code
2. Then run `ruff check` — many I001 violations will already be resolved
3. When running quality gates in parallel, expect sibling errors if format fails
4. Consider running format as part of the edit workflow rather than as a post-implementation check
