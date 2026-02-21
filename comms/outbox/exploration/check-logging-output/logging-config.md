# Logging Configuration

## How Logging Is Configured

`src/stoat_ferret/logging.py` defines the logging setup:

```python
def configure_logging(json_format: bool = True, level: int = logging.INFO) -> None:
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_format:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(level)
```

Key details:
- Uses structlog's stdlib integration with `ProcessorFormatter`
- Supports JSON (production) and console (development) output modes
- Attaches a single `StreamHandler(sys.stdout)` to the root logger
- No file handlers are created

## Where configure_logging Is Called

**It is not called anywhere.** A grep for `configure_logging` across the entire `src/` directory returns only the function definition itself. It is not imported or invoked in:
- `src/stoat_ferret/api/__main__.py` (the CLI entry point)
- `src/stoat_ferret/api/app.py` (the app factory)
- `src/stoat_ferret/__init__.py`
- Any other module

## Default Log Levels and Configurability

### Settings (defined but unused)
`src/stoat_ferret/api/settings.py` defines:
```python
log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
    default="INFO",
    description="Logging level",
)
```
Configurable via `STOAT_LOG_LEVEL` env var. However, this value is **never read** by any code.

### Uvicorn (hardcoded)
`src/stoat_ferret/api/__main__.py` hardcodes:
```python
uvicorn.run(app, host=settings.api_host, port=settings.api_port, log_level="info")
```
This controls uvicorn's own logging (access logs, server lifecycle). It does not use `settings.log_level`.

### Effective Behaviour
Since `configure_logging()` is never called:
- Structlog is unconfigured and uses its default settings
- The root Python logger has no explicitly added handlers
- Python's `logging.lastResort` handler (a `StreamHandler(stderr)` at WARNING level) catches any log records that make it to the root logger
- This means `logger.info()` calls throughout the codebase are likely **silently dropped** - only WARNING+ would appear on stderr via lastResort

## Debug Logs
No debug-level log statements exist in the application code. All `logger.*` calls use `info`, `warning`, or `error`. Even if debug logging were enabled, there are no debug log statements to emit.
