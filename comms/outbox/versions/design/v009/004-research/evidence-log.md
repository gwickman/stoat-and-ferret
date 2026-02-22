# Evidence Log — v009

## Log Rotation Size

- **Value**: 10MB (`maxBytes=10_485_760`)
- **Source**: BL-057 acceptance criteria and backlog notes
- **Data**: AC2 specifies "Log files rotate at 10MB". Backlog notes: "Use RotatingFileHandler with maxBytes=10MB."
- **Rationale**: Explicit requirement from backlog item

## Log Backup Count

- **Value**: 5 (default), configurable via settings
- **Source**: BL-057 AC2 specifies "configurable backup count"
- **Data**: No existing setting for this. Python stdlib default is 0 (no rotation). Common values: 3-10.
- **Rationale**: 5 is a reasonable default for development. Configurable per AC.

## Log File Path

- **Value**: `logs/stoat-ferret.log` at project root
- **Source**: BL-057 AC1 specifies "logs/ directory at project root"
- **Data**: No existing log directory. `.gitignore` has `*.log` (line 59) but no `logs/` entry.
- **Rationale**: Matches AC requirement. Relative to CWD (project root).

## Idempotent Handler Guard Pattern

- **Value**: `type(h) is RotatingFileHandler` exact-type check
- **Source**: Existing pattern in `src/stoat_ferret/logging.py:52-58` (LRN-040)
- **Data**: Current code uses `type(h) is logging.StreamHandler` to prevent duplicate stdout handlers. Test at `tests/test_logging_startup.py:39-51` verifies this.
- **Rationale**: Consistent with established pattern; prevents duplicate file handlers in tests

## SPA Fallback Behavior

- **Value**: `StaticFiles(html=True)` returns 404 for non-existent sub-paths
- **Source**: DeepWiki query on `encode/starlette` repository
- **Data**: Starlette test `test_staticfiles_html_normal` confirms `/missing` serves `404.html`, not `index.html`. The `html=True` flag only serves `index.html` for directory requests.
- **Rationale**: BL-063 requires a separate catch-all route

## Projects count() Gap

- **Value**: `AsyncProjectRepository` has no `count()` method
- **Source**: Codebase investigation — `src/stoat_ferret/db/project_repository.py:18-86`
- **Data**: `AsyncVideoRepository` has `count()` at line 100 (protocol), 210 (SQLite), 365 (InMemory). Projects endpoint uses `total=len(projects)` at `routers/projects.py:113`.
- **Rationale**: Asymmetry introduced in v005 when count() was added to videos but not projects

## WebSocket Broadcast Gap

- **Value**: Zero `broadcast()` calls in any API router
- **Source**: Grep for `broadcast` in `src/stoat_ferret/api/routers/` — only ws.py references ConnectionManager
- **Data**: Event types defined (SCAN_STARTED, SCAN_COMPLETED, PROJECT_CREATED). Manager available at `app.state.ws_manager`. Frontend ActivityLog parses events correctly.
- **Rationale**: Infrastructure built in v005 but broadcast calls never added

## Historical Session Durations

- **Value**: v008 feature sessions: 87-343 seconds (1.5-5.7 minutes)
- **Source**: query_cli_sessions — session_list for project, last 60 days
- **Data**: v008 retro sessions: 116-343s. C4 doc sessions: 124-295s. Feature sessions completed with 0 errors in most cases.
- **Rationale**: v009 wiring tasks are similar complexity — expect 2-5 min per feature. Source: query_cli_sessions

## Tool Reliability

- **Value**: WebFetch 34.9% error rate, Edit 10%, Bash 15.4%
- **Source**: query_cli_sessions — tool_usage analytics, last 60 days
- **Data**: 83 WebFetch calls with 29 errors. 2342 Edit calls with 235 errors. MCP tools: 0% error rate across all auto-dev-mcp tools.
- **Rationale**: Avoid relying on WebFetch for implementation. Edit errors are expected (non-unique strings). Source: query_cli_sessions

## Learning Verification Table

| Learning | Status | Evidence |
|----------|--------|----------|
| LRN-040 | VERIFIED | Exact-type handler guard at `logging.py:52-58`, tested at `test_logging_startup.py:39-51` |
| LRN-041 | VERIFIED | mypy in quality gates (`AGENTS.md`), caught `debug=` kwarg in v008 |
| LRN-005 | VERIFIED | `create_app()` kwargs pattern at `app.py:99-179`, test injection at `test_api/conftest.py:67-91` |
| LRN-020 | VERIFIED | Conditional mount at `app.py:169-177` checks `gui_dir.is_dir()` |
| LRN-023 | VERIFIED | SPA fallback not implemented — BL-063 will fix root cause |
| LRN-042 | VERIFIED | v009 themes grouped by modification point (DI/startup vs API/GUI) |
| LRN-043 | VERIFIED | Process learning — applicable to any new E2E tests in BL-063/065 |
| LRN-046 | VERIFIED | v008 achieved 4/4 first-iteration, 0 quality gate failures |
| LRN-031 | VERIFIED | All 6 items have current-state/gap/impact + testable ACs |
| LRN-016 | VERIFIED | All referenced classes confirmed to exist with expected interfaces |
| LRN-009 | VERIFIED | Handler registration pattern exists — tangentially relevant |
| LRN-037 | VERIFIED | ActivityLog uses independent Zustand store (`activityStore.ts`) |
| LRN-044 | VERIFIED | BL-057 may add `log_backup_count` setting — must wire consumer |
