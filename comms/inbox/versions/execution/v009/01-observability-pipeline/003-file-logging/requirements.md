# Requirements: file-logging

## Goal

Add RotatingFileHandler to configure_logging() for persistent log output to rotating files.

## Background

Backlog Item: BL-057

After BL-056 (completed in v008), structured logging is wired but outputs to stdout only. When the process stops, all log history is lost. This feature adds file-based logging with rotation for persistent log output.

## Functional Requirements

**FR-001: RotatingFileHandler in configure_logging()**
- Add a `RotatingFileHandler` writing to `logs/stoat-ferret.log` at the project root
- Use idempotent guard: `type(h) is RotatingFileHandler` to prevent duplicate handlers
- Acceptance: After `configure_logging()`, a RotatingFileHandler is present in root logger handlers

**FR-002: Log rotation configuration**
- Log files rotate at 10MB (`maxBytes=10_485_760`)
- Backup count is configurable via Settings (`log_backup_count` default 5, `log_max_bytes` default 10_485_760)
- Acceptance: When log file exceeds 10MB, rotation produces `stoat-ferret.log.1`, etc.

**FR-003: Automatic directory creation**
- `logs/` directory is created automatically on startup if it does not exist
- Acceptance: Starting the application with no `logs/` directory creates it before logging begins

**FR-004: .gitignore update**
- `logs/` is added to `.gitignore`
- Acceptance: `git status` does not show log files as untracked

**FR-005: Consistent formatting**
- File handler uses the same structlog formatter and log level as the stdout handler
- Acceptance: Log entries in file and stdout are identically formatted

**FR-006: Parallel stdout output**
- Stdout logging continues to work alongside file logging
- Acceptance: Both stdout and file contain the same log entries after operations

## Non-Functional Requirements

**NFR-001: Idempotent handler registration**
- Calling `configure_logging()` multiple times does not produce duplicate file handlers
- Metric: After 3 calls, exactly 1 RotatingFileHandler and 1 StreamHandler exist

## Out of Scope

- Log aggregation or external log shipping
- Log format customization beyond matching stdout
- Log viewer or search functionality
- JSON log format (uses existing structlog formatter)

## Test Requirements

- Unit: Verify `configure_logging()` adds a RotatingFileHandler (AC1)
- Unit: Verify idempotent guard prevents duplicate file handlers
- Unit: Verify `logs/` directory is created if absent (AC3)
- Unit: Verify file handler uses same formatter and log level as stdout (AC5)
- Unit: Verify stdout logging continues alongside file logging (AC6)
- Integration: Verify log files rotate at configured size (AC2)
- Existing: `tests/test_logging_startup.py` — add file handler tests alongside stream handler tests
- Verify: `.gitignore` includes `logs/` entry (AC4)

See `comms/outbox/versions/design/v009/005-logical-design/test-strategy.md` for full test strategy.

## Reference

See `comms/outbox/versions/design/v009/004-research/` for supporting evidence.