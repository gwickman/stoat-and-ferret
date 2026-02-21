# Log Destinations

## All Log Output Destinations

### 1. Uvicorn's Built-in Logging (active)
- **Destination**: stderr (uvicorn default)
- **Level**: INFO (hardcoded in `__main__.py`)
- **Content**: Server startup/shutdown messages, HTTP access logs
- **Source**: `uvicorn.run(app, ..., log_level="info")`

### 2. Application Structlog Loggers (partially broken)
- **Destination**: Depends on Python's logging fallback behaviour
- **Level**: Effectively WARNING+ via Python's `lastResort` handler
- **Content**: Job lifecycle, websocket events, effect registration, thumbnail generation, scan service events

10 modules create structlog loggers:
```
src/stoat_ferret/api/app.py              - job_worker_started, job_worker_stopped
src/stoat_ferret/api/routers/effects.py  - effect preview/render/apply events
src/stoat_ferret/api/routers/ws.py       - (logger created, no calls found)
src/stoat_ferret/api/services/scan.py    - (logger created, calls in handler)
src/stoat_ferret/api/services/thumbnail.py - thumbnail generation warnings
src/stoat_ferret/api/websocket/manager.py  - connect/disconnect/dead connection
src/stoat_ferret/effects/registry.py     - effect_registered
src/stoat_ferret/ffmpeg/observable.py     - (logger created)
src/stoat_ferret/jobs/queue.py           - job submit/start/complete/fail, worker lifecycle
```

Since `configure_logging()` is never called, structlog operates unconfigured. The `structlog.stdlib.LoggerFactory()` default creates standard library loggers, but no handlers are attached to the root logger. Python's `lastResort` handler (stderr, WARNING+) is the only safety net.

## File-Based Logging
**None.** No `FileHandler`, `RotatingFileHandler`, `TimedRotatingFileHandler`, or any file-based log sink exists anywhere in the codebase. The `configure_logging()` function (even if it were called) only creates a `StreamHandler(sys.stdout)`.

## Log Rotation
**None.** No log rotation is configured or implemented.

## Rust-Side Logging
**None.** The Rust extension (`stoat_ferret_core`) has minimal dependencies:
```toml
[dependencies]
pyo3 = { version = "0.26", features = ["abi3-py310"] }
pyo3-stub-gen = "0.17"
```
No `log`, `tracing`, `env_logger`, or `tracing-subscriber` crates. The Rust code does not emit any log output. The only `log`-related references in Rust source are:
- FFmpeg `-loglevel warning` flag for subprocess calls
- `FadeCurve::Log` (logarithmic audio fade curve)
- Algorithm complexity comments (`O(n log n)`)

## Uvicorn/ASGI Server Logging Behaviour
Uvicorn manages its own logging independently of the application:
- Uses Python's `logging` module with its own formatters
- Access log format: default uvicorn format to stderr
- Error log: stderr
- Level: controlled by `log_level="info"` parameter in `__main__.py`
- Not integrated with the application's structlog configuration

## Docker / CI
The `Dockerfile` runs `pytest -v` only (test container). No production deployment configuration exists that would add file logging or log aggregation.
