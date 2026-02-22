# Learning Extraction - v009 Retrospective

6 new learnings saved, 3 existing learnings reinforced. Sources: 6 completion reports, 2 theme retrospectives, 1 version retrospective, session health findings (Task 004b), and session analytics.

## New Learnings

| ID | Title | Tags | Source |
|----|-------|------|--------|
| LRN-047 | WAL Mode Enables Safe Mixed Sync/Async SQLite Access | sqlite, async, database, concurrency | v009/01-observability-pipeline/002-audit-logging |
| LRN-048 | Catch-All Routes Replace StaticFiles for SPA Fallback in FastAPI | fastapi, spa, routing, frontend | v009/02-gui-runtime-fixes/001-spa-routing |
| LRN-049 | Guard Optional Broadcast Calls to Avoid Runtime Crashes | websocket, dependency-injection, defensive-coding | v009/02-gui-runtime-fixes/003-websocket-broadcasts |
| LRN-050 | Incremental DI Wiring Is Fast and Low-Risk When Patterns Are Established | dependency-injection, process, planning, efficiency | v009/01-observability-pipeline retrospective |
| LRN-051 | Add count() to Repository Protocols for Accurate Pagination | repository, pagination, api-design, database | v009/02-gui-runtime-fixes/002-pagination-fix |
| LRN-052 | Run Formatter Before Linter to Avoid Double Fix Cycles | process, tooling, ruff, code-quality | session analytics (v009 period) |

## Reinforced Learnings

| ID | Title | New Evidence |
|----|-------|-------------|
| LRN-005 | Constructor DI over dependency_overrides for FastAPI Testing | v009 added 3 more DI components via `create_app()` kwargs — the pattern continues to scale cleanly without structural changes |
| LRN-039 | Excessive Context Compaction Signals Need for Task Decomposition | v009 session health found 27 sessions with 3+ compaction events (54% of sessions), up from 48% in v007; the issue remains systemic |
| LRN-040 | Idempotent Startup Functions for Lifespan Wiring | v009/003-file-logging used idempotent handler registration guards to prevent duplicate `RotatingFileHandler` registration, confirming this pattern extends beyond database initialization |

## Filtered Out

**Total candidates identified:** 15
**Saved as new:** 6
**Reinforced existing:** 3
**Filtered out:** 6

| Category | Count | Examples |
|----------|-------|---------|
| Duplicates of existing learnings | 2 | DI wiring pattern (LRN-005), idempotent startup (LRN-040) |
| Too implementation-specific | 2 | Specific file paths for logging config, test file names |
| Already captured by v009 session health (Task 004b) | 1 | Tool authorization retry waste finding |
| Version-specific references | 1 | C4 documentation regeneration failure (v009-only issue) |
