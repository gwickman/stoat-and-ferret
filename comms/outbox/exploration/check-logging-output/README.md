# Exploration: check-logging-output

**No, the MVP does not log debug output to files anywhere.** The only log destination is stdout, via uvicorn's default logging. The custom structlog-based `configure_logging()` function exists but is never called at application startup, meaning all structlog loggers throughout the codebase operate with structlog's default (unconfigured) behaviour. There is no file-based logging, no log rotation, and no persistent debug logging of any kind.

## Summary

### Logging Configuration
- `src/stoat_ferret/logging.py` defines `configure_logging()` with structlog processors and a `StreamHandler(sys.stdout)` - but this function is **never imported or called** anywhere in the codebase.
- 10 modules use `structlog.get_logger(__name__)` to create loggers, emitting `logger.info()`, `logger.warning()`, and `logger.error()` calls. With structlog unconfigured, these fall through to Python's standard logging with default formatting.
- `src/stoat_ferret/api/settings.py` defines a `log_level` setting (configurable via `STOAT_LOG_LEVEL` env var, default `INFO`), but this setting is **never read or applied** to any logging configuration.

### Where Output Goes
- The only logging configuration that takes effect is uvicorn's `log_level="info"` hardcoded in `__main__.py`. Uvicorn logs (access logs, server startup) go to stderr by default.
- Application-level structlog calls (job lifecycle, websocket events, effect registration, thumbnails) use structlog's default unconfigured behaviour, which proxies to Python's root logger with no handlers explicitly attached - output depends on Python's `logging.lastResort` handler (stderr, WARNING+).
- The Rust extension (`stoat_ferret_core`) has no logging dependencies (only `pyo3` and `pyo3-stub-gen`). It does not emit any log output.

### Gaps
1. `configure_logging()` is dead code - never called at startup
2. `settings.log_level` is defined but never consumed
3. No file-based log output anywhere
4. No log rotation
5. No way to enable debug logging without code changes
6. Structlog loggers emit calls that may be silently dropped (INFO level calls hit Python's lastResort handler which only shows WARNING+)
