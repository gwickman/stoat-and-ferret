# Theme 01: Observability Pipeline — Retrospective

## Summary

Wired three pre-existing observability components into the application's DI chain and startup sequence. After this theme, FFmpeg operations emit Prometheus metrics and structured logs, database mutations produce audit entries, and all logs are persisted to rotating files. All three features were delivered successfully with all acceptance criteria passing and all quality gates green.

## Feature Results

| # | Feature | Acceptance | Quality Gates | Status |
|---|---------|------------|---------------|--------|
| 001 | ffmpeg-observability | 5/5 pass | ruff, mypy, pytest pass | Complete |
| 002 | audit-logging | 4/4 pass | ruff, mypy, pytest pass | Complete |
| 003 | file-logging | 7/7 pass | ruff, mypy, pytest pass | Complete |

**Total:** 16/16 acceptance criteria passed across 3 features.

## Deliverables

| Deliverable | Description |
|-------------|-------------|
| `ObservableFFmpegExecutor` DI wiring | FFmpeg executor wrapped with metrics/logging layer in lifespan, injectable via `create_app()` |
| `AuditLogger` DI wiring | Separate sync `sqlite3.Connection` opened alongside aiosqlite, `AuditLogger` passed to repository |
| `RotatingFileHandler` integration | File-based logging with 10MB rotation, 5 backups, auto-created `logs/` directory |

## Key Decisions

### Separate sync connection for AuditLogger
**Context:** `AuditLogger` uses synchronous `sqlite3` while the app uses `aiosqlite`. Sharing a connection would require refactoring the audit logger.
**Choice:** Open a second synchronous `sqlite3.Connection` to the same database with WAL mode for concurrent access.
**Outcome:** Clean separation of concerns; no deadlocks confirmed by concurrent tests.

### Test-injection bypass for ObservableFFmpegExecutor
**Context:** Tests need to inject mock executors without the observable wrapper adding noise.
**Choice:** When `ffmpeg_executor` kwarg is provided to `create_app()`, store it directly without wrapping.
**Outcome:** Test doubles work cleanly; production path always wraps with observability.

### Idempotent handler registration for file logging
**Context:** `configure_logging()` could be called multiple times, risking duplicate file handlers.
**Choice:** Guard against duplicate `RotatingFileHandler` registration with an idempotent check.
**Outcome:** Safe to call repeatedly; no duplicate log entries.

## Metrics

| Metric | Start (pre-theme) | End (post-theme) |
|--------|-------------------|-------------------|
| Tests passing | ~890 | 910 |
| Test coverage | ~92.7% | 92.89% |
| New test files | — | 3 (`test_ffmpeg_observability.py`, `test_audit_logging.py`, `test_logging_startup.py` updates) |

## Learnings

### What Went Well
- All three features followed the same pattern: existing dead code wired into the DI chain via `create_app()` kwargs and lifespan initialization. This consistency made each successive feature faster.
- The existing DI pattern (`create_app()` kwargs + `app.state` + `_deps_injected` flag) scaled cleanly to three new components without any structural changes.
- Quality gates remained green throughout — zero regressions introduced.

### Patterns Discovered
- **DI wiring pattern:** Add kwarg to `create_app()` → instantiate in lifespan → store on `app.state` → pass to dependent services. This pattern is now well-established for future components.
- **WAL mode for mixed sync/async SQLite:** Enables concurrent read/write from both `sqlite3` and `aiosqlite` connections without deadlocks.

## Technical Debt

| Item | Source | Severity | Notes |
|------|--------|----------|-------|
| `create_app()` kwarg count growing | All 3 features | Low | Function now has many optional kwargs for DI; could benefit from a config/container object if more components are added |
| Hardcoded log rotation defaults | 003-file-logging | Low | `max_bytes=10MB`, `backup_count=5` are configurable via settings but defaults are hardcoded in `configure_logging()` signature |
| No log format distinction | 003-file-logging | Low | File handler uses same formatter as stdout; structured JSON logs to file could aid log aggregation tools |

## Recommendations

1. **For future DI additions:** Continue the `create_app()` kwarg pattern but consider introducing a DI container or dataclass if the kwarg count exceeds 6-7 parameters.
2. **For future observability work:** The metrics and logging infrastructure is now live — future features can emit custom metrics and structured logs without additional wiring.
3. **For audit logging expansion:** The `AuditLogger` is currently wired only to `AsyncSQLiteVideoRepository.add()`. Consider extending to update/delete operations as the application grows.
