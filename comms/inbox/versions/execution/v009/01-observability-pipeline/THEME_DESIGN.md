# Theme: observability-pipeline

## Goal

Wire the three observability components that exist as dead code into the application's DI chain and startup sequence. After this theme, FFmpeg operations emit metrics and structured logs, database mutations produce audit entries, and all logs are persisted to rotating files.

## Design Artifacts

See `comms/outbox/versions/design/v009/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | ffmpeg-observability | BL-059 | Wire ObservableFFmpegExecutor into DI so FFmpeg operations emit metrics and structured logs |
| 002 | audit-logging | BL-060 | Wire AuditLogger into repository DI with a separate sync connection for audit entries |
| 003 | file-logging | BL-057 | Add RotatingFileHandler to configure_logging() for persistent log output |

## Dependencies

- BL-057 depends on BL-056 (structured logging wired in v008) — already completed
- Features are sequenced (001 → 002 → 003) to avoid concurrent app.py modifications, not due to functional dependencies

## Technical Approach

- **001-ffmpeg-observability:** Wrap `RealFFmpegExecutor()` with `ObservableFFmpegExecutor()` in lifespan. Add `ffmpeg_executor` kwarg to `create_app()` for test injection. See `004-research/codebase-patterns.md` Section 1 and 6 for DI pattern and executor structure.
- **002-audit-logging:** Open a separate `sqlite3.Connection` in lifespan for AuditLogger. Pass to repository constructors that accept the parameter. Add `audit_logger` kwarg to `create_app()`. See `006-critical-thinking/risk-assessment.md` for sync connection rationale.
- **003-file-logging:** Add `RotatingFileHandler` with idempotent guard (`type(h) is RotatingFileHandler`) matching the existing StreamHandler pattern. Add `log_backup_count` and `log_max_bytes` settings. See `004-research/codebase-patterns.md` Section 2 and `004-research/evidence-log.md` for values.

## Risks

| Risk | Mitigation |
|------|------------|
| AuditLogger requires sync connection | Use separate sqlite3.Connection — see 006-critical-thinking/risk-assessment.md |
| Lifespan function complexity growth | Additions are ~8 lines total, under 50-line threshold — see 006-critical-thinking/risk-assessment.md |
| Test double injection after wrapping | create_app() _deps_injected flag bypasses lifespan — see 006-critical-thinking/risk-assessment.md |