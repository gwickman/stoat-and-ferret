# Retrospective Insights — v009 for v010 Design

## Previous Version: v009 (Observability & GUI Runtime)

**Completed:** 2026-02-22 | **Themes:** 2/2 | **Features:** 6/6 | **AC:** 31/31

## What Worked Well (Continue)

1. **Established DI pattern scales cleanly.** The `create_app()` kwargs + `app.state` + `_deps_injected` flag pattern handled three new components in v009 without structural changes. v010 should extend this pattern for progress callbacks and cancellation mechanisms rather than introducing new wiring approaches.

2. **Incremental wiring over greenfield.** All six v009 features wired existing code or extended existing patterns rather than building from scratch. v010 Theme 1 (async-pipeline-fix) follows this pattern — ffprobe already exists, it just needs async conversion. Theme 2 (job-controls) extends the existing `AsyncioJobQueue`.

3. **Tightly scoped themes with 3 features each.** Both v009 themes had clear goals and completed cleanly with no scope changes. v010 follows the same pattern: Theme 1 has 3 features, Theme 2 has 2.

4. **Repository protocol extension pattern.** Adding methods to protocols (define on protocol, implement in SQLite/InMemory, wire via DI) worked reliably in v009. v010 may need this for job status extensions.

5. **Guard patterns for optional components.** The `if ws_manager:` pattern from v009 WebSocket broadcasts is directly relevant for v010 progress reporting — progress callbacks should be optional and guarded.

## What Didn't Work (Avoid)

1. **C4 documentation regeneration failed.** v009 noted this as tech debt. v010 should not attempt C4 regeneration as a side-effect; if needed, it should be a dedicated feature.

2. **No integration test for live WebSocket broadcast.** v009 tested broadcasts via mocked `ws_manager` only. v010's BL-078 (event-loop responsiveness test) is explicitly designed to avoid this problem by requiring real/simulated subprocess behavior, not mocks.

3. **Growing `create_app()` kwarg count.** v009 flagged this as low-severity debt. v010 may add more kwargs (progress callback, cancellation support). If the count exceeds 6-7, consider a DI container or config dataclass.

## Tech Debt Addressed vs Deferred

### Carried from v009 (still open):
- C4 documentation not updated for v009 changes (medium severity)
- `create_app()` kwarg count growing (low — watch threshold)
- No cache headers on static files (low)
- Pagination not on all list endpoints (low)
- No broadcast for project deletion (low)
- No integration test for live WebSocket broadcast (low — partially addressed by BL-078's approach)

### Not explicitly addressed in v010:
- v010 focuses on async correctness and job controls, not documentation or frontend polish
- The WebSocket integration testing gap is indirectly addressed by BL-078's pattern

## Architectural Decisions to Inform v010

1. **WAL mode for mixed sync/async SQLite.** v009 established that a separate sync connection with WAL mode works safely alongside aiosqlite. v010 should not need additional database connections, but should be aware of the pattern if audit logging touches job status.

2. **Idempotent startup functions.** v009/v008 established that lifespan functions must be idempotent. Any new startup wiring in v010 (e.g., registering cancellation handlers) should follow this pattern.

3. **Test-injection bypass pattern.** When `ffmpeg_executor` kwarg is provided, store directly without wrapping. v010's async ffprobe conversion should maintain this pattern — tests inject mock async executors, production wraps with the real implementation.

4. **`AsyncioJobQueue` is the foundation.** The existing queue (from v004/LRN-009/LRN-010) uses stdlib `asyncio.Queue` with handler registration pattern. v010 extends this with progress and cancellation rather than replacing it.
