# Risk Assessment — v009

## Risk: SPA fallback route ordering in FastAPI

- **Original severity**: medium
- **Category**: Investigate now
- **Investigation**: Queried DeepWiki (encode/starlette) for route vs mount priority semantics. Confirmed via Starlette routing internals that routes are processed sequentially — a `Route('/gui/{path:path}')` returns `Match.FULL` for ALL `/gui/*` paths, preventing a subsequent `Mount('/gui', StaticFiles(...))` from ever receiving requests.
- **Finding**: **Risk confirmed.** A naive catch-all route intercepts ALL `/gui/*` requests including static asset requests (`/gui/assets/main.js`, `/gui/assets/style.css`). StaticFiles never gets a chance to serve them. Reversing the order (Mount before Route) doesn't help either — Mount also returns `Match.FULL`, so StaticFiles would return 404 for SPA paths and the fallback route is never reached.
- **Resolution**: The catch-all route handler must serve dual duty: (1) check if `gui_dir / path` is an existing file — if yes, return `FileResponse` for that file; (2) if no, return `FileResponse` for `gui_dir / "index.html"`. This replaces the StaticFiles mount entirely for `/gui/*`. The route is registered after API routers. The `StaticFiles` mount at `/gui` should be **removed** and replaced with this route.
- **Affected themes/features**: Theme 2, Feature 001-spa-routing (BL-063)

## Risk: AuditLogger requires synchronous SQLite connection

- **Original severity**: medium
- **Category**: Investigate now
- **Investigation**: Read `src/stoat_ferret/db/audit.py` (full class), `src/stoat_ferret/db/async_repository.py` (lines 120-180), and `aiosqlite/core.py`. Verified AuditLogger constructor signature, async repository audit call pattern, and aiosqlite internals.
- **Finding**: **Risk confirmed with pragmatic resolution.** AuditLogger takes `sqlite3.Connection` (sync) and uses blocking `execute()` + `commit()`. Async repositories already have `if self._audit: self._audit.log_change(...)` as dead code (lines 168-170) — the call is synchronous from an async context. `aiosqlite.Connection` has no public API to access its underlying `sqlite3.Connection` (only private `_conn` property). Using the private property would also be unsafe — aiosqlite manages the connection via a worker thread.
- **Resolution**: Create a **separate** `sqlite3.Connection` for AuditLogger during lifespan, opened to the same database file. The brief event loop blocking (single INSERT + commit per mutation) is acceptable for v009 — audit writes are lightweight and occur after the main operation commits. The separate connection avoids thread-safety issues with aiosqlite's worker thread. Document async AuditLogger as a future improvement.
- **Affected themes/features**: Theme 1, Feature 002-audit-logging (BL-060)

## Risk: WebSocket broadcast touches multiple routers

- **Original severity**: medium
- **Category**: Investigate now
- **Investigation**: Read `websocket/events.py` (5 event types), `routers/videos.py` (6 endpoints), `routers/projects.py` (7 endpoints), and `websocket/manager.py`. Verified zero broadcast calls exist. Analyzed scan endpoint flow.
- **Finding**: **Risk partially confirmed — broadcast points differ from assumption.** The scan endpoint (`POST /api/v1/videos/scan`) does NOT execute the scan directly — it submits an async job to `job_queue` and returns 202 immediately. SCAN_STARTED and SCAN_COMPLETED broadcasts must fire from the **job handler/scan service**, not the videos router. PROJECT_CREATED can fire directly in the projects router's `create_project()` endpoint. Only 2 routers need modification (projects.py for PROJECT_CREATED), plus the scan service/job handler for SCAN events.
- **Resolution**: Adjust implementation plan: (1) PROJECT_CREATED broadcast in `routers/projects.py` create endpoint, (2) SCAN_STARTED and SCAN_COMPLETED broadcasts in the scan job handler (wherever the job queue processes scan jobs). This reduces router modifications from 2 to 1, lowering the cross-cutting risk. HEALTH_STATUS broadcasts are deferred (no clear trigger point identified).
- **Affected themes/features**: Theme 2, Feature 003-websocket-broadcasts (BL-065)

## Risk: Lifespan function complexity growth

- **Original severity**: low
- **Category**: Accept with mitigation
- **Investigation**: Reviewed current lifespan function (~30 lines of setup logic). v009 adds: FFmpeg executor wrapping (~3 lines), AuditLogger instantiation (~3 lines), separate sync connection for audit (~2 lines). Total addition: ~8 lines.
- **Finding**: Lifespan will grow to ~38 lines of setup logic, well under the 50-line threshold.
- **Resolution**: No design change needed for v009. Monitor after implementation. If it exceeds 50 lines, extract `setup_observability()` helper in a future version.
- **Affected themes/features**: Theme 1 (all features add to lifespan)

## Risk: Log backup count setting addition

- **Original severity**: low
- **Category**: Accept with mitigation
- **Investigation**: Reviewed Settings model pattern and LRN-044 (settings must be wired to consumer immediately).
- **Finding**: Adding `log_backup_count: int = 5` and `log_max_bytes: int = 10_485_760` to Settings is straightforward. Both are consumed immediately by `configure_logging()` when creating the `RotatingFileHandler`.
- **Resolution**: Add both settings fields with sensible defaults. Wire them in `configure_logging()`. Per LRN-044, the consumer exists in the same feature, so no dangling settings.
- **Affected themes/features**: Theme 1, Feature 003-file-logging (BL-057)

## Risk: Test double injection after ObservableFFmpegExecutor wiring

- **Original severity**: low
- **Category**: Investigate now
- **Investigation**: Read `create_app()` DI pattern in `app.py`. When kwargs are provided, `app.state._deps_injected = True` is set and the lifespan skips all DB/DI setup. Verified the conditional logic at lines 137-146.
- **Finding**: **Risk resolved — no issue.** When tests inject `ffmpeg_executor=mock_executor` via `create_app()`, the `_deps_injected` flag prevents lifespan from running. The mock executor is stored directly on `app.state` without being wrapped in `ObservableFFmpegExecutor`. The existing DI pattern handles test doubles correctly.
- **Resolution**: No design change needed. Test strategy remains as specified in Task 005.
- **Affected themes/features**: Theme 1, Feature 001-ffmpeg-observability (BL-059)

## Risk: Frontend pagination adjustment for BL-064

- **Original severity**: low
- **Category**: Investigate now
- **Investigation**: Read `gui/src/pages/ProjectsPage.tsx`, `gui/src/hooks/useProjects.ts`, `gui/src/stores/projectStore.ts`, and compared with `LibraryPage.tsx`, `useVideos.ts`, `libraryStore.ts`. Analyzed how `total` is consumed.
- **Finding**: **Scope increase discovered.** The Projects page has NO pagination UI. It fetches with `limit=100` hardcoded, no offset parameter. The `total` field is stored via the hook but never used for pagination. The Library page has full pagination (page state in Zustand store, offset calculation, Previous/Next buttons, page count display). BL-064 AC3 says "Frontend pagination displays correct page count when projects exceed the page limit" — this cannot be met without adding pagination UI to the Projects page.
- **Resolution**: Feature 002-pagination-fix must include frontend work: (1) add `page`/`pageSize` state to project store, (2) add offset parameter to `useProjects` hook, (3) add pagination UI to `ProjectsPage` (matching Library pattern). Complexity increases from Low to Medium. No backlog items are deferred — the scope increase stays within the feature.
- **Affected themes/features**: Theme 2, Feature 002-pagination-fix (BL-064)
