# Refined Logical Design — v009: Observability & GUI Runtime

## Version Overview

**Version:** v009
**Description:** Complete the observability pipeline (FFmpeg metrics, audit logging, file-based logs) and fix GUI runtime gaps (SPA routing, pagination, WebSocket broadcasts).

**Scope:** 2 themes, 6 features. All items are wiring gaps — no new functionality is being built.

**Changes from Task 005:** Three design refinements based on risk investigation (see `risk-assessment.md`):
1. SPA routing replaces StaticFiles mount with dual-purpose catch-all route
2. AuditLogger wiring uses a separate sync connection
3. Pagination fix includes frontend pagination UI for Projects page

---

## Theme 1: 01-observability-pipeline

**Goal:** Wire the three observability components that exist as dead code into the application's DI chain and startup sequence.

**Backlog Items:** BL-059, BL-060, BL-057

**Features:**

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-ffmpeg-observability | Wire ObservableFFmpegExecutor into DI so FFmpeg operations emit metrics and structured logs | BL-059 | None |
| 2 | 002-audit-logging | Wire AuditLogger into repository DI with a separate sync connection | BL-060 | None (sequenced after 001 to avoid app.py conflicts) |
| 3 | 003-file-logging | Add RotatingFileHandler to configure_logging() for persistent log output | BL-057 | None (sequenced after 002 to avoid app.py conflicts) |

### Design Refinement: Feature 002-audit-logging

**Change:** AuditLogger requires its own synchronous `sqlite3.Connection`, separate from the async `aiosqlite.Connection` used by repositories.

**Implementation:**
1. In lifespan, after creating the aiosqlite connection, open a separate `sqlite3.Connection` to the same database file
2. Pass this sync connection to `AuditLogger(conn=sync_conn)`
3. Store `audit_logger` on `app.state` and pass to repository constructors
4. Close the sync connection during lifespan cleanup (before closing aiosqlite)

**Rationale:** aiosqlite has no public API to access its underlying sync connection. Using the private `_conn` property would be unsafe (worker thread owns it). A separate connection is safe because: (a) the audit INSERT happens after the main operation commits, (b) SQLite WAL mode allows concurrent readers, and (c) the blocking is minimal (single lightweight INSERT + commit).

---

## Theme 2: 02-gui-runtime-fixes

**Goal:** Fix three runtime gaps in the GUI and API layer.

**Backlog Items:** BL-063, BL-064, BL-065

**Features:**

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-spa-routing | Replace StaticFiles mount with catch-all route that serves both static files and SPA fallback | BL-063 | None |
| 2 | 002-pagination-fix | Add count() to AsyncProjectRepository, fix total in API, and add frontend pagination UI | BL-064 | None |
| 3 | 003-websocket-broadcasts | Wire broadcast() into scan service and project router for real-time events | BL-065 | None (sequenced last due to cross-cutting complexity) |

### Design Refinement: Feature 001-spa-routing

**Change:** Replace the `StaticFiles` mount approach with a single catch-all route that handles both static file serving and SPA fallback.

**Implementation:**
1. Remove `app.mount("/gui", StaticFiles(directory=gui_dir, html=True), name="gui")`
2. Add `@app.get("/gui/{path:path}")` route after API routers
3. Route handler logic:
   - If `gui_dir / path` is an existing file → return `FileResponse(gui_dir / path)`
   - Otherwise → return `FileResponse(gui_dir / "index.html")`
4. Add `@app.get("/gui")` for the bare `/gui` path → return `FileResponse(gui_dir / "index.html")`
5. Both routes are conditional on `gui_dir.is_dir()` (LRN-020)

**Rationale:** Starlette routes are processed sequentially — a `Route('/gui/{path:path}')` returns `Match.FULL` for ALL `/gui/*` paths, preventing a subsequent `Mount` from receiving requests. A `Mount` first also fails — it catches everything and returns 404 for non-file paths without falling through. The dual-purpose route is the only pattern that works without custom middleware or StaticFiles subclassing.

### Design Refinement: Feature 002-pagination-fix

**Change:** Feature scope increased from Low to Medium complexity. In addition to backend count() wiring, the feature must add pagination UI to the Projects page.

**Implementation:**
1. **Backend:** Add `count()` to `AsyncProjectRepository` protocol, SQLite, and InMemory implementations
2. **Backend:** Wire `count()` into projects router for correct `total` in response
3. **Frontend:** Add `page`/`pageSize` state to `projectStore.ts` (matching `libraryStore.ts` pattern)
4. **Frontend:** Update `useProjects` hook to accept `page`/`pageSize` and send `limit`/`offset` params
5. **Frontend:** Add Previous/Next pagination UI to `ProjectsPage.tsx` (matching `LibraryPage.tsx` pattern)

**Rationale:** BL-064 AC3 requires "Frontend pagination displays correct page count when projects exceed the page limit." The Projects page currently has no pagination — it fetches with hardcoded `limit=100`. Without adding pagination UI, AC3 cannot be met. The Library page provides a proven pattern to follow.

### Design Refinement: Feature 003-websocket-broadcasts

**Change:** SCAN_STARTED and SCAN_COMPLETED broadcasts fire from the scan job handler, not the videos router.

**Implementation:**
1. **PROJECT_CREATED:** Add `broadcast(build_event(EventType.PROJECT_CREATED, {...}))` in `routers/projects.py` `create_project()` after successful creation
2. **SCAN_STARTED:** Add broadcast at the beginning of the scan job handler (wherever job_queue processes scan jobs)
3. **SCAN_COMPLETED:** Add broadcast at the end of scan job handler after scan finishes
4. **HEALTH_STATUS:** Defer trigger identification to implementation — no clear trigger point exists
5. Access `ws_manager` via `request.app.state.ws_manager` in routers and via dependency injection in the scan service

**Rationale:** The scan endpoint (`POST /api/v1/videos/scan`) submits an async job and returns 202 immediately. The actual scan runs later in the job handler. Broadcasting at the endpoint would only announce "job submitted," not "scan started/completed."

---

## Execution Order

No changes from Task 005. Theme and feature ordering remain the same.

### Theme Order
**Theme 1 before Theme 2.** Rationale unchanged — avoids concurrent `app.py` modifications.

### Feature Order Within Theme 1
1. 001-ffmpeg-observability → 2. 002-audit-logging → 3. 003-file-logging

### Feature Order Within Theme 2
1. 001-spa-routing → 2. 002-pagination-fix → 3. 003-websocket-broadcasts

---

## Updated Test Strategy

### Feature 001-spa-routing (updated)
- **New test:** Verify static asset requests (e.g., `/gui/assets/main.js`) return the correct file content (not index.html)
- **New test:** Verify `/gui` (bare path) returns index.html
- **Removed assumption:** No need to test route-vs-mount ordering — StaticFiles mount is removed

### Feature 002-audit-logging (updated)
- **New test:** Verify separate sync `sqlite3.Connection` is created and closed during lifespan
- **New test:** Verify audit entries are written while async operations continue (no deadlock)

### Feature 002-pagination-fix (updated)
- **New test:** Frontend: Verify Projects page shows pagination when projects exceed page limit
- **New test:** Frontend: Verify Previous/Next navigation works for projects
- **New test:** Frontend: Verify page resets when project is created/deleted

### Feature 003-websocket-broadcasts (updated)
- **Clarification:** SCAN_STARTED/COMPLETED tests should trigger a scan job and wait for completion, not just test the endpoint response
- **Clarification:** HEALTH_STATUS broadcast may not be wired in v009 if no clear trigger exists

---

## Research Sources Adopted

All sources from Task 005 remain valid, plus:

### Starlette Route vs Mount Priority
- **Finding:** Routes process sequentially; first `Match.FULL` wins. Routes and Mounts at the same path cannot coexist with fallthrough.
- **Source:** DeepWiki — `encode/starlette` (Routing internals, `Router` iteration)
- **Impact:** SPA fallback must replace StaticFiles mount, not coexist with it.
