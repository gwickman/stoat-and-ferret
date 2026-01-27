"""Observable FFmpeg executor with logging and metrics.

Provides a wrapper executor that adds structured logging and Prometheus
metrics to any FFmpegExecutor implementation.
"""

from __future__ import annotations

import uuid

import structlog

from stoat_ferret.ffmpeg.executor import ExecutionResult, FFmpegExecutor
from stoat_ferret.ffmpeg.metrics import (
    ffmpeg_active_processes,
    ffmpeg_execution_duration_seconds,
    ffmpeg_executions_total,
)

logger = structlog.get_logger(__name__)


class ObservableFFmpegExecutor:
    """Wraps any FFmpegExecutor with logging and metrics.

    This executor wraps another FFmpegExecutor implementation and adds:
    - Structured logging for each execution (start, completion, failure)
    - Prometheus metrics (counters, histogram, gauge)
    - Correlation ID support for tracing
    """

    def __init__(self, wrapped: FFmpegExecutor) -> None:
        """Initialize with a wrapped executor.

        Args:
            wrapped: The FFmpegExecutor implementation to wrap.
        """
        self._wrapped = wrapped

    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
        correlation_id: str | None = None,
    ) -> ExecutionResult:
        """Execute FFmpeg with logging and metrics.

        Args:
            args: Arguments to pass to ffmpeg (not including the ffmpeg command).
            stdin: Optional bytes to pass to stdin.
            timeout: Optional timeout in seconds.
            correlation_id: Optional correlation ID for tracing. Generated if not provided.

        Returns:
            ExecutionResult with the outcome of the execution.
        """
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
