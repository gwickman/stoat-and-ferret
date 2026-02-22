# Implementation Plan: file-logging

## Overview

Add a `RotatingFileHandler` to `configure_logging()` for persistent log output to rotating files. Add `log_backup_count` and `log_max_bytes` settings to the Settings model. Ensure `logs/` directory is auto-created and added to `.gitignore`.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/logging.py` | Modify | Add RotatingFileHandler with idempotent guard, logs/ directory creation |
| `src/stoat_ferret/api/settings.py` | Modify | Add `log_backup_count` and `log_max_bytes` fields |
| `.gitignore` | Modify | Add `logs/` entry |
| `tests/test_logging_startup.py` | Modify | Add file handler tests alongside existing stream handler tests |

## Test Files

`tests/test_logging_startup.py`

## Implementation Stages

### Stage 1: Add settings fields

1. Add `log_backup_count: int = 5` to Settings model
2. Add `log_max_bytes: int = 10_485_760` to Settings model

**Verification:**
```bash
uv run mypy src/
```

### Stage 2: Add RotatingFileHandler to configure_logging()

1. Import `RotatingFileHandler` from `logging.handlers`
2. In `configure_logging()`, after the StreamHandler setup:
   - Create `logs/` directory if it doesn't exist (`Path("logs").mkdir(exist_ok=True)`)
   - Add idempotent guard: `has_file_handler = any(type(h) is RotatingFileHandler for h in root.handlers)`
   - If no file handler: create `RotatingFileHandler(filename="logs/stoat-ferret.log", maxBytes=settings.log_max_bytes, backupCount=settings.log_backup_count, encoding="utf-8")`
   - Set same formatter and log level as the StreamHandler
   - Add to root logger

**Verification:**
```bash
uv run mypy src/
uv run pytest tests/test_logging_startup.py -x
```

### Stage 3: Update .gitignore and add tests

1. Add `logs/` to `.gitignore`
2. Add tests:
   - Verify RotatingFileHandler is added after `configure_logging()`
   - Verify idempotent guard (calling twice produces exactly 1 file handler)
   - Verify `logs/` directory is created if absent
   - Verify file handler uses same formatter and level as stdout
   - Verify stdout continues working alongside file logging

**Verification:**
```bash
uv run pytest tests/test_logging_startup.py -x
uv run ruff check src/ tests/
```

## Test Infrastructure Updates

- Tests should use `tmp_path` for log directory to avoid polluting the project root
- May need to parametrize `configure_logging()` to accept a custom log directory for testing

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- Settings fields must be immediately consumed (LRN-044) — both are consumed by `configure_logging()` in the same feature.
- Log file path is relative to CWD — tests must use tmp_path to avoid side effects.

## Commit Message

```
feat(observability): add file-based logging with rotation

BL-057: Add RotatingFileHandler to configure_logging() writing to logs/
directory with 10MB rotation and configurable backup count. Add
log_backup_count and log_max_bytes settings. Add logs/ to .gitignore.
```