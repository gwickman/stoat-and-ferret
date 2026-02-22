---
status: complete
acceptance_passed: 7
acceptance_total: 7
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 002-logging-startup

## Summary

Wired `configure_logging()` into application startup and connected `settings.log_level` to control log verbosity. Made `configure_logging()` idempotent and updated uvicorn to use the settings-based log level.

## Changes Made

### `src/stoat_ferret/logging.py`
- Made `configure_logging()` idempotent by guarding `root.addHandler()` with an exact-type check for existing `StreamHandler` on the root logger. Multiple calls no longer accumulate duplicate handlers.

### `src/stoat_ferret/api/app.py`
- Added `configure_logging(level=getattr(logging, settings.log_level))` call at the start of the `lifespan()` function, before the `_deps_injected` guard. This ensures logging is configured for both production and test modes.

### `src/stoat_ferret/api/__main__.py`
- Changed uvicorn's hardcoded `log_level="info"` to `log_level=settings.log_level.lower()`.

### `tests/test_logging.py`
- Added `autouse` fixture to clean up root logger `StreamHandler` instances between tests.
- Fixed import to use `collections.abc.Generator` per ruff UP035 rule.

### `tests/test_logging_startup.py` (new)
- 15 tests covering idempotency, log level conversion, lifespan integration, uvicorn wiring, and output visibility.

## Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| FR-001 | configure_logging() called during startup lifespan | PASS |
| FR-002 | settings.log_level controls root logger level | PASS |
| FR-003 | STOAT_LOG_LEVEL=DEBUG produces visible debug output | PASS |
| FR-004 | Existing structlog modules produce visible output at INFO | PASS |
| FR-005 | uvicorn log_level uses settings.log_level.lower() | PASS |
| FR-006 | configure_logging() is idempotent | PASS |
| FR-007 | Existing tests continue to pass | PASS |

## Quality Gates

- ruff check: pass (0 errors)
- ruff format: pass (113 files formatted)
- mypy: pass (49 source files, no issues)
- pytest: pass (883 passed, 20 skipped, 92.71% coverage)
