# Observability

## Purpose

The Observability component provides centralized structured logging configuration for the entire Python backend. It configures the structlog library with a shared processor pipeline, selects between JSON output for production and human-readable console output for development, and attaches a rotating file handler so logs are persisted to disk with automatic size-based rotation.

## Responsibilities

- Configure structlog with a processor pipeline that adds log level, logger name, ISO 8601 timestamp, and stack traces to every log entry
- Support two output formats: JSON (production, suitable for log aggregation systems) and console (development, human-readable colored output)
- Attach a `RotatingFileHandler` to the root Python logger to persist logs in `logs/stoat-ferret.log` with configurable size and backup count (FR-001)
- Ensure idempotent configuration so `configure_logging()` can be called multiple times without creating duplicate handlers
- Bridge structlog's processor model to stdlib logging via `ProcessorFormatter` so all log output from all modules goes through the same pipeline

## Interfaces

### Provided Interfaces

**configure_logging (function)**
- `configure_logging(json_format: bool, level: int, log_dir: str | Path, max_bytes: int, backup_count: int) -> None`
  - `json_format=True` — JSON output; `False` for ConsoleRenderer
  - `level` — Minimum log level (default `logging.INFO`)
  - `log_dir` — Directory for rotating log file (default `"logs"`)
  - `max_bytes` — Maximum log file size before rotation (default 10MB)
  - `backup_count` — Number of backup files to retain (default 5)

### Required Interfaces

None — the component depends only on Python standard library `logging` and the `structlog` third-party library.

## Code Modules

| Module | Source | Purpose |
|--------|--------|---------|
| Logging Configuration | `src/stoat_ferret/logging.py` | `configure_logging()` function; shared processor pipeline; JSON/console renderer selection; rotating file handler; idempotent handler management |

## Key Behaviors

**Shared Processor Pipeline:** All log entries pass through `add_log_level`, `add_logger_name`, `TimeStamper(fmt="iso")`, and `StackInfoRenderer` before reaching the final renderer. This ensures every entry carries consistent metadata regardless of which module emits it.

**Idempotent Handler Management:** Before adding a `StreamHandler` or `RotatingFileHandler`, `configure_logging()` checks the root logger's existing handlers using exact type matching (`type(h) is RotatingFileHandler`). This prevents duplicate handlers when the function is called during testing or application restarts.

**ProcessorFormatter Bridge:** Both the stream handler and the file handler share the same `structlog.stdlib.ProcessorFormatter`, which applies the shared processor pipeline and the selected renderer. This means structlog's high-level API produces identical structured output whether writing to stdout or to the rotating file.

**Log Rotation (FR-001):** The `RotatingFileHandler` creates backup files named `stoat-ferret.log.1` through `stoat-ferret.log.{backup_count}`. When the current file reaches `max_bytes`, it is renamed and a new file is started. The oldest backup beyond `backup_count` is deleted automatically.

## Inter-Component Relationships

```
API Gateway (app.py lifespan)
    |-- calls --> Observability (configure_logging)

All components
    |-- emit structured logs via --> structlog.get_logger(__name__)
    |   (all logs route through the configured pipeline)

FFmpeg Integration, Preview subsystem
    |-- follow metric singleton module pattern (LRN-137)
    |   (all Prometheus metrics defined as module-level singletons in metrics.py)

Observability
    |-- writes logs to --> logs/stoat-ferret.log (rotating file)
    |-- writes logs to --> stdout (stream handler)
```

**Metric Singleton Module Pattern (LRN-137):** Subsystems define all Prometheus metrics in a dedicated `metrics.py` module as module-level singletons. Service files import specific metric objects rather than creating them inline. This provides a single inventory of all instrumentation points per subsystem, avoids import-time side effects, and enables consistent naming conventions. Applied in FFmpeg Integration (`ffmpeg/metrics.py`) and Preview subsystem (`preview/metrics.py`).

## Version History

| Version | Changes |
|---------|---------|
| v007 | Initial logging configuration with structlog, rotating file handler, and JSON/console formats |
| v027 | Documented metric singleton module pattern (LRN-137) as cross-cutting observability guidance |
