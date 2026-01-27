# Implementation Plan: FFmpeg Observability

## Step 1: Add Dependencies
Edit pyproject.toml:
```toml
[project]
dependencies = [
    "alembic>=1.13",
    "structlog>=24.0",
    "prometheus-client>=0.20",
]
```

Run `uv sync`.

## Step 2: Create Metrics Module
Create `src/stoat_ferret/ffmpeg/metrics.py`:

```python
from prometheus_client import Counter, Histogram, Gauge

ffmpeg_executions_total = Counter(
    "stoat_ferret_ffmpeg_executions_total",
    "Total FFmpeg command executions",
    ["status"],  # success, failure
)

ffmpeg_execution_duration_seconds = Histogram(
    "stoat_ferret_ffmpeg_execution_duration_seconds",
    "FFmpeg command execution duration in seconds",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

ffmpeg_active_processes = Gauge(
    "stoat_ferret_ffmpeg_active_processes",
    "Number of currently running FFmpeg processes",
)
```

## Step 3: Create Observable Executor
Create `src/stoat_ferret/ffmpeg/observable.py`:

```python
import structlog
import uuid
from .executor import FFmpegExecutor, ExecutionResult
from .metrics import (
    ffmpeg_executions_total,
    ffmpeg_execution_duration_seconds,
    ffmpeg_active_processes,
)

logger = structlog.get_logger(__name__)


class ObservableFFmpegExecutor:
    """Wraps any FFmpegExecutor with logging and metrics."""
    
    def __init__(self, wrapped: FFmpegExecutor):
        self._wrapped = wrapped
    
    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
        correlation_id: str | None = None,
    ) -> ExecutionResult:
        correlation_id = correlation_id or str(uuid.uuid4())
        
        # Truncate args for logging (avoid logging sensitive paths)
        log_args = args[:10] if len(args) > 10 else args
        
        log = logger.bind(
            correlation_id=correlation_id,
            command_args=log_args,
            arg_count=len(args),
        )
        
        log.info("ffmpeg_execution_started")
        ffmpeg_active_processes.inc()
        
        try:
            result = self._wrapped.run(args, stdin=stdin, timeout=timeout)
            
            status = "success" if result.returncode == 0 else "failure"
            ffmpeg_executions_total.labels(status=status).inc()
            ffmpeg_execution_duration_seconds.observe(result.duration_seconds)
            
            log.info(
                "ffmpeg_execution_completed",
                returncode=result.returncode,
                duration_seconds=round(result.duration_seconds, 3),
                status=status,
            )
            
            return result
            
        except Exception as e:
            ffmpeg_executions_total.labels(status="failure").inc()
            log.error(
                "ffmpeg_execution_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
            
        finally:
            ffmpeg_active_processes.dec()
```

## Step 4: Configure Structlog
Create `src/stoat_ferret/logging.py`:

```python
import structlog
import logging
import sys

def configure_logging(json_format: bool = True, level: int = logging.INFO):
    """Configure structlog for the application.
    
    Args:
        json_format: If True, output JSON logs. If False, use console format.
        level: Logging level.
    """
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
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
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

## Step 5: Add Tests
```python
import pytest
from unittest.mock import Mock
from stoat_ferret.ffmpeg.observable import ObservableFFmpegExecutor
from stoat_ferret.ffmpeg.executor import ExecutionResult

class MockExecutor:
    def __init__(self, returncode=0):
        self.returncode = returncode
    
    def run(self, args, *, stdin=None, timeout=None):
        return ExecutionResult(
            returncode=self.returncode,
            stdout=b"",
            stderr=b"",
            command=["ffmpeg"] + args,
            duration_seconds=0.5,
        )

def test_observable_executor_success(caplog):
    import structlog
    structlog.configure(
        processors=[structlog.processors.KeyValueRenderer()],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    
    observable = ObservableFFmpegExecutor(MockExecutor(returncode=0))
    result = observable.run(["-version"], correlation_id="test-123")
    
    assert result.returncode == 0
    # Logs would contain correlation_id="test-123"

def test_observable_executor_metrics():
    from prometheus_client import REGISTRY
    
    # Get baseline
    before = REGISTRY.get_sample_value(
        "stoat_ferret_ffmpeg_executions_total", 
        {"status": "success"}
    ) or 0
    
    observable = ObservableFFmpegExecutor(MockExecutor(returncode=0))
    observable.run(["-version"])
    
    after = REGISTRY.get_sample_value(
        "stoat_ferret_ffmpeg_executions_total", 
        {"status": "success"}
    )
    assert after == before + 1

def test_observable_executor_failure_metrics():
    from prometheus_client import REGISTRY
    
    before = REGISTRY.get_sample_value(
        "stoat_ferret_ffmpeg_executions_total", 
        {"status": "failure"}
    ) or 0
    
    observable = ObservableFFmpegExecutor(MockExecutor(returncode=1))
    observable.run(["-invalid"])
    
    after = REGISTRY.get_sample_value(
        "stoat_ferret_ffmpeg_executions_total", 
        {"status": "failure"}
    )
    assert after == before + 1
```

## Verification
- Logs emitted in JSON format with correlation ID
- Prometheus metrics increment on execution
- Active process gauge increments/decrements correctly