# Logging Configuration

**Source:** `src/stoat_ferret/logging.py`
**Component:** Observability

## Purpose

Provides centralized logging configuration using structlog with support for JSON output (production) and console output (development). Includes rotating file-based logging with configurable file rotation via RotatingFileHandler for persistent log output.

## Public Interface

### Functions

- `configure_logging(json_format: bool = True, level: int = logging.INFO, log_dir: str | Path = "logs", max_bytes: int = 10_485_760, backup_count: int = 5) -> None`: Configure structlog for the application
  - Args:
    - `json_format`: If True, output JSON logs. If False, use console format. (default: True)
    - `level`: Logging level (default: logging.INFO)
    - `log_dir`: Directory for log files (default: "logs")
    - `max_bytes`: Maximum log file size in bytes before rotation (default: 10MB = 10,485,760)
    - `backup_count`: Number of rotated backup files to keep (default: 5)

## Dependencies

### Internal Dependencies

None

### External Dependencies

- `logging`: Standard Python logging module
  - `logging.getLogger()`: Root logger access
  - `logging.StreamHandler`: Console output handler
  - `logging.INFO`: Default log level constant
- `logging.handlers.RotatingFileHandler`: File rotation handler
  - Uses maxBytes and backupCount for rotation management
- `pathlib.Path`: Directory operations for log_dir
- `sys`: Standard output stream (sys.stdout)
- `structlog`: Structured logging framework
  - `structlog.stdlib.add_log_level`: Processor for log level
  - `structlog.stdlib.add_logger_name`: Processor for logger name
  - `structlog.processors.TimeStamper`: ISO format timestamps
  - `structlog.processors.StackInfoRenderer`: Stack traces
  - `structlog.processors.JSONRenderer`: JSON output format
  - `structlog.dev.ConsoleRenderer`: Development console format
  - `structlog.stdlib.ProcessorFormatter`: Adapter for stdlib logging
  - `structlog.stdlib.BoundLogger`: Context binding
  - `structlog.stdlib.LoggerFactory`: Factory for creating loggers
  - `structlog.configure()`: Global configuration

## Key Implementation Details

### Configuration Pattern

`configure_logging()` sets up a three-layer logging system:

1. **structlog configuration**: Top-level async logging API
2. **stdlib logging handlers**: Console and file output
3. **ProcessorFormatter**: Bridges structlog to stdlib logging

This layered approach enables:
- High-level structured logging API via structlog
- Underlying stdlib logging for handler management
- Support for multiple output formats simultaneously

### Shared Processors

Both JSON and console formats use shared processing pipeline:

```python
shared_processors = [
    structlog.stdlib.add_log_level,      # Add log level field
    structlog.stdlib.add_logger_name,    # Add logger module name
    structlog.processors.TimeStamper(fmt="iso"),  # ISO 8601 timestamps
    structlog.processors.StackInfoRenderer(),     # Stack traces for exceptions
]
```

These processors:
- Standardize metadata across output formats
- Add ISO 8601 timestamps for time-based filtering
- Enable stack trace rendering for debugging
- Ensure consistency between JSON and console output

### Output Format Selection

Format determined by `json_format` parameter:

**JSON Format (Production):**
- `structlog.processors.JSONRenderer()`: Renders all fields as JSON
- Enables structured querying in log aggregation systems
- Suitable for Elasticsearch, Splunk, etc.

**Console Format (Development):**
- `structlog.dev.ConsoleRenderer()`: Human-readable colored output
- Enables quick debugging in development
- Readable multi-line output for exceptions

### Rotating File Handler (FR-001 Requirement)

File rotation is implemented via `RotatingFileHandler`:

**File Rotation Configuration:**
- `filename`: Log file path: `log_dir / "stoat-ferret.log"`
- `maxBytes`: Maximum file size before rotation (default 10MB)
  - Standard parameter: 10,485,760 bytes = 10 * 1024 * 1024
  - Configurable per environment (larger for high-volume logging)
- `backupCount`: Number of backup files to keep (default 5)
  - Creates stoat-ferret.log.1, .log.2, .log.3, .log.4, .log.5
  - Oldest file (.log.5) is deleted when new rotation needed
- `encoding`: UTF-8 for international character support

**Rotation Behavior:**
- When current log reaches maxBytes, file is renamed
- Current file → .log.1, .log.1 → .log.2, etc.
- Oldest backup (backupCount + 1) is deleted
- New stoat-ferret.log created for new entries
- Rollover is automatic and transparent

**Log Directory Handling:**
- `Path(log_dir).mkdir(parents=True, exist_ok=True)` creates directory
- Creates parent directories if needed
- Idempotent (safe to call multiple times)

### Handler Idempotency

Configuration is idempotent (safe to call multiple times):

**Stream Handler Idempotency:**
```python
has_stream_handler = any(type(h) is logging.StreamHandler for h in root.handlers)
if not has_stream_handler:
    # Add handler only if not present
```
- Uses exact type match (`is logging.StreamHandler`)
- Avoids matching subclasses (e.g., pytest's LogCaptureHandler)
- Prevents duplicate handlers when called multiple times

**File Handler Idempotency:**
```python
has_file_handler = any(type(h) is RotatingFileHandler for h in root.handlers)
if not has_file_handler:
    # Add handler only if not present
```
- Same exact type matching pattern
- Allows safe reconfiguration without duplication

### Formatter Configuration

Both handlers use the same ProcessorFormatter:

```python
formatter = structlog.stdlib.ProcessorFormatter(
    processor=renderer,              # JSON or Console renderer
    foreign_pre_chain=shared_processors,  # Shared processors
)
```

The ProcessorFormatter:
- Bridges structlog and stdlib logging
- Applies shared processors to all log records
- Applies selected renderer (JSON or Console)
- Enables format-agnostic logging API

### Root Logger Configuration

Configuration affects the root logger:

```python
root = logging.getLogger()  # Gets root logger
root.addHandler(handler)    # Add handler
root.setLevel(level)        # Set minimum level
```

This ensures:
- All loggers inherit configuration
- Centralized control of logging behavior
- Consistent formatting across modules

## Relationships

- **Used by:** Application initialization code to configure logging before any log statements
- **Uses:** structlog for structured logging, stdlib logging for handler management, RotatingFileHandler for file rotation
