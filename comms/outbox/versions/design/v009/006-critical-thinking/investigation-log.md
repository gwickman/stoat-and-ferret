# Investigation Log — v009 Critical Thinking

## Investigation 1: AuditLogger Sync/Async Compatibility

**Goal:** Determine if AuditLogger can work with async repositories without modification.

**Queries performed:**
1. Read `src/stoat_ferret/db/audit.py` — full AuditLogger class
2. Read `src/stoat_ferret/db/async_repository.py` lines 120-180 — async repo audit usage
3. Read `aiosqlite/core.py` — internal connection structure
4. Read `src/stoat_ferret/db/repository.py` — sync repo audit usage for comparison

**Evidence:**
- `AuditLogger.__init__` takes `sqlite3.Connection` (sync only)
- `AuditLogger.log_change()` calls `self._conn.execute()` and `self._conn.commit()` — blocking
- `AsyncSQLiteVideoRepository.add()` at line 168-170: `if self._audit: self._audit.log_change("INSERT", "video", video.id)` — blocking call from async context
- `aiosqlite.Connection._conn` is private property; no public access to underlying sync connection
- aiosqlite uses a worker thread + SimpleQueue for async operations — sharing the connection would be thread-unsafe

**Conclusion:** AuditLogger needs its own sync `sqlite3.Connection`. The blocking audit call is acceptable (single lightweight INSERT per mutation). Creating a separate connection in lifespan is the simplest safe approach.

---

## Investigation 2: WebSocket Broadcast Insertion Points

**Goal:** Identify exactly where broadcast calls should be added and whether all 4 event types need wiring.

**Queries performed:**
1. Read `src/stoat_ferret/api/websocket/events.py` — all event types
2. Read `src/stoat_ferret/api/routers/videos.py` — scan endpoint flow
3. Read `src/stoat_ferret/api/routers/projects.py` — CRUD endpoints
4. Searched for existing `broadcast` calls in codebase — zero found
5. Read `src/stoat_ferret/api/websocket/manager.py` — broadcast method

**Evidence:**
- 5 event types defined: HEALTH_STATUS, SCAN_STARTED, SCAN_COMPLETED, PROJECT_CREATED, HEARTBEAT
- HEARTBEAT already sent by `routers/ws.py` heartbeat loop — no change needed
- `POST /api/v1/videos/scan` submits to `job_queue` and returns 202 — scan runs async
- `POST /api/v1/projects` creates project synchronously — broadcast can fire inline
- `ConnectionManager.broadcast()` exists but is never called from any router
- No other routers (effects, health, jobs) have operations requiring broadcasts

**Conclusion:** Scan broadcasts must fire from the job handler/scan service, not the videos router. Only projects router needs direct modification for PROJECT_CREATED. HEALTH_STATUS has no clear trigger point — defer to implementation-time decision.

---

## Investigation 3: SPA Route vs StaticFiles Mount Priority

**Goal:** Determine if a catch-all route and StaticFiles mount can coexist at `/gui/`.

**Queries performed:**
1. Read `src/stoat_ferret/api/app.py` — full route registration and mount order
2. DeepWiki query on `encode/starlette` — route vs mount priority semantics
3. Read Task 004 external-research.md — SPA fallback approach

**Evidence:**
- Current app.py: routers included at lines 154-159, StaticFiles mounted at line 177
- Starlette routing: routes processed sequentially, first `Match.FULL` wins
- `Route('/gui/{path:path}')` returns `Match.FULL` for ALL `/gui/*` paths
- `Mount('/gui', StaticFiles(...))` also returns `Match.FULL` for ALL `/gui/*` paths
- Whichever is defined first captures everything — no fallthrough after FULL match
- Task 004 research said "add catch-all route" but didn't address the static asset conflict

**Conclusion:** The catch-all route must replace StaticFiles for `/gui/*` by handling both static file serving and SPA fallback. The handler checks if the path maps to a real file in gui_dir — serve the file if yes, serve index.html if no. The StaticFiles mount at `/gui` is removed.

---

## Investigation 4: Frontend Projects Pagination

**Goal:** Verify if changing `total` in the projects API response will break the frontend.

**Queries performed:**
1. Read `gui/src/pages/ProjectsPage.tsx` — Projects page component
2. Read `gui/src/hooks/useProjects.ts` — projects fetch hook
3. Read `gui/src/stores/projectStore.ts` — project state store
4. Read `gui/src/pages/LibraryPage.tsx` — Library page for comparison
5. Read `gui/src/hooks/useVideos.ts` — videos hook for comparison
6. Read `gui/src/stores/libraryStore.ts` — library state for comparison

**Evidence:**
- Projects page: fetches with `limit=100`, no offset, no pagination UI
- `useProjects` stores `total` but page never reads it for pagination
- `projectStore` has no page/pageSize state
- Library page: full pagination with page state, offset calc, Previous/Next UI
- `useVideos` sends limit + offset, uses total for `totalPages = Math.ceil(total/pageSize)`
- `libraryStore` has page (0-indexed), pageSize (20), reset-on-search logic

**Conclusion:** Changing `total` won't break the Projects page (it's unused). But BL-064 AC3 requires "Frontend pagination displays correct page count" — this means pagination UI must be added to the Projects page, following the Library page pattern. Scope increase from Low to Medium.

---

## Investigation 5: Test Double Injection Pattern

**Goal:** Confirm test doubles aren't wrapped by ObservableFFmpegExecutor after wiring.

**Queries performed:**
1. Read `src/stoat_ferret/api/app.py` — create_app() DI pattern and lifespan

**Evidence:**
- `create_app()` accepts optional kwargs (lines 99-108)
- Lines 137-146: if any repo/queue is injected, sets `_deps_injected = True`
- Lifespan at line 65-67: `if getattr(app.state, "_deps_injected", False): yield; return` — skips all setup
- When tests inject `ffmpeg_executor=mock`, lifespan doesn't run, mock is stored directly

**Conclusion:** Risk fully resolved. The `_deps_injected` flag bypasses lifespan entirely, so test doubles are never wrapped.
