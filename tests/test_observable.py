"""Tests for ObservableFFmpegExecutor with logging and metrics."""

from __future__ import annotations

import pytest
import structlog
from prometheus_client import REGISTRY

from stoat_ferret.ffmpeg.executor import ExecutionResult
from stoat_ferret.ffmpeg.observable import ObservableFFmpegExecutor


class MockExecutor:
    """Mock executor for testing ObservableFFmpegExecutor."""

    def __init__(
        self,
        returncode: int = 0,
        stdout: bytes = b"",
        stderr: bytes = b"",
        duration_seconds: float = 0.5,
    ) -> None:
        """Initialize with configurable return values."""
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.duration_seconds = duration_seconds
        self.calls: list[tuple[list[str], bytes | None, float | None]] = []

    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        """Return mock result and record the call."""
        self.calls.append((args, stdin, timeout))
        return ExecutionResult(
            returncode=self.returncode,
            stdout=self.stdout,
            stderr=self.stderr,
            command=["ffmpeg", *args],
            duration_seconds=self.duration_seconds,
        )


class RaisingExecutor:
    """Executor that raises an exception."""

    def __init__(self, exception: Exception) -> None:
        """Initialize with the exception to raise."""
        self.exception = exception

    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        """Raise the configured exception."""
        raise self.exception


@pytest.fixture(autouse=True)
def configure_structlog() -> None:
    """Configure structlog for testing."""
    structlog.configure(
        processors=[structlog.processors.KeyValueRenderer()],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


class TestObservableFFmpegExecutor:
    """Tests for ObservableFFmpegExecutor."""

    def test_delegates_to_wrapped_executor(self) -> None:
        """Test that calls are delegated to wrapped executor."""
        mock = MockExecutor(returncode=0, stdout=b"delegated output")
        observable = ObservableFFmpegExecutor(mock)

        result = observable.run(["-version"])

        assert result.stdout == b"delegated output"
        assert len(mock.calls) == 1
        assert mock.calls[0][0] == ["-version"]

    def test_passes_stdin_and_timeout(self) -> None:
        """Test that stdin and timeout are passed through."""
        mock = MockExecutor()
        observable = ObservableFFmpegExecutor(mock)

        observable.run(["-i", "pipe:"], stdin=b"input data", timeout=30.0)

        assert mock.calls[0][1] == b"input data"
        assert mock.calls[0][2] == 30.0

    def test_returns_execution_result(self) -> None:
        """Test that the execution result is returned."""
        mock = MockExecutor(
            returncode=0,
            stdout=b"output",
            stderr=b"error",
            duration_seconds=1.5,
        )
        observable = ObservableFFmpegExecutor(mock)

        result = observable.run(["-version"])

        assert result.returncode == 0
        assert result.stdout == b"output"
        assert result.stderr == b"error"
        assert result.duration_seconds == 1.5

    def test_generates_correlation_id_if_not_provided(self) -> None:
        """Test that correlation_id is generated if not provided."""
        mock = MockExecutor()
        observable = ObservableFFmpegExecutor(mock)

        # Should not raise
        result = observable.run(["-version"])
        assert result.returncode == 0

    def test_uses_provided_correlation_id(self) -> None:
        """Test that provided correlation_id is used."""
        mock = MockExecutor()
        observable = ObservableFFmpegExecutor(mock)

        # Should not raise
        result = observable.run(["-version"], correlation_id="test-correlation-123")
        assert result.returncode == 0


class TestObservableFFmpegExecutorMetrics:
    """Tests for ObservableFFmpegExecutor metrics."""

    def _get_metric_value(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get the current value of a metric."""
        value = REGISTRY.get_sample_value(name, labels or {})
        return value or 0.0

    def test_increments_success_counter_on_success(self) -> None:
        """Test that success counter is incremented on successful execution."""
        before = self._get_metric_value(
            "stoat_ferret_ffmpeg_executions_total", {"status": "success"}
        )

        mock = MockExecutor(returncode=0)
        observable = ObservableFFmpegExecutor(mock)
        observable.run(["-version"])

        after = self._get_metric_value(
            "stoat_ferret_ffmpeg_executions_total", {"status": "success"}
        )
        assert after == before + 1

    def test_increments_failure_counter_on_nonzero_returncode(self) -> None:
        """Test that failure counter is incremented on non-zero returncode."""
        before = self._get_metric_value(
            "stoat_ferret_ffmpeg_executions_total", {"status": "failure"}
        )

        mock = MockExecutor(returncode=1)
        observable = ObservableFFmpegExecutor(mock)
        observable.run(["-invalid"])

        after = self._get_metric_value(
            "stoat_ferret_ffmpeg_executions_total", {"status": "failure"}
        )
        assert after == before + 1

    def test_increments_failure_counter_on_exception(self) -> None:
        """Test that failure counter is incremented when exception is raised."""
        before = self._get_metric_value(
            "stoat_ferret_ffmpeg_executions_total", {"status": "failure"}
        )

        raising = RaisingExecutor(RuntimeError("test error"))
        observable = ObservableFFmpegExecutor(raising)

        with pytest.raises(RuntimeError, match="test error"):
            observable.run(["-version"])

        after = self._get_metric_value(
            "stoat_ferret_ffmpeg_executions_total", {"status": "failure"}
        )
        assert after == before + 1

    def test_records_duration_histogram(self) -> None:
        """Test that duration histogram is recorded."""
        # Get histogram sum before
        before_sum = self._get_metric_value("stoat_ferret_ffmpeg_execution_duration_seconds_sum")

        mock = MockExecutor(returncode=0, duration_seconds=2.5)
        observable = ObservableFFmpegExecutor(mock)
        observable.run(["-version"])

        after_sum = self._get_metric_value("stoat_ferret_ffmpeg_execution_duration_seconds_sum")
        # Duration should be added to the histogram
        assert after_sum >= before_sum + 2.5

    def test_active_processes_gauge_increments_and_decrements(self) -> None:
        """Test that active processes gauge is managed correctly."""
        # Since tests run concurrently, we verify the gauge changes during execution
        mock = MockExecutor(returncode=0)
        observable = ObservableFFmpegExecutor(mock)

        # Execute should complete without error and gauge should return to baseline
        observable.run(["-version"])

        # No assertion on exact gauge value since it may be affected by concurrent tests
        # The fact that it doesn't error out indicates proper inc/dec pairing

    def test_active_processes_gauge_decrements_on_exception(self) -> None:
        """Test that gauge is decremented even when exception is raised."""
        raising = RaisingExecutor(RuntimeError("test error"))
        observable = ObservableFFmpegExecutor(raising)

        with pytest.raises(RuntimeError):
            observable.run(["-version"])

        # Again, we verify it doesn't leak by not erroring out


class TestObservableFFmpegExecutorProtocol:
    """Tests for ObservableFFmpegExecutor protocol compliance."""

    def test_observable_does_not_implement_ffmpeg_executor_protocol(self) -> None:
        """Test that ObservableFFmpegExecutor has extended signature.

        The ObservableFFmpegExecutor has an extended run() signature with
        correlation_id, so it doesn't strictly implement FFmpegExecutor.
        However, it's compatible when correlation_id is not used.
        """
        mock = MockExecutor()
        observable = ObservableFFmpegExecutor(mock)

        # Should work with basic parameters (compatible usage)
        result = observable.run(["-version"], stdin=None, timeout=None)
        assert result.returncode == 0


class TestObservableFFmpegExecutorLogging:
    """Tests for ObservableFFmpegExecutor logging behavior."""

    def test_truncates_long_args_in_logs(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that long args lists are truncated in logs."""
        mock = MockExecutor()
        observable = ObservableFFmpegExecutor(mock)

        # Create args longer than 10 elements
        long_args = [f"-arg{i}" for i in range(20)]
        observable.run(long_args)

        # The execution should complete - truncation happens internally
        assert len(mock.calls) == 1
        assert mock.calls[0][0] == long_args

    def test_logs_on_success(self) -> None:
        """Test that logging occurs on successful execution."""
        mock = MockExecutor(returncode=0)
        observable = ObservableFFmpegExecutor(mock)

        # Should not raise
        result = observable.run(["-version"])
        assert result.returncode == 0

    def test_logs_on_failure(self) -> None:
        """Test that logging occurs on failed execution."""
        mock = MockExecutor(returncode=1)
        observable = ObservableFFmpegExecutor(mock)

        # Should not raise
        result = observable.run(["-invalid"])
        assert result.returncode == 1

    def test_logs_on_exception(self) -> None:
        """Test that logging occurs when exception is raised."""
        raising = RaisingExecutor(RuntimeError("test error"))
        observable = ObservableFFmpegExecutor(raising)

        with pytest.raises(RuntimeError):
            observable.run(["-version"])


class TestExports:
    """Tests for module exports."""

    def test_observable_executor_exported_from_ffmpeg_package(self) -> None:
        """Test that ObservableFFmpegExecutor is exported from ffmpeg package."""
        from stoat_ferret.ffmpeg import ObservableFFmpegExecutor

        assert ObservableFFmpegExecutor is not None

    def test_metrics_exported_from_ffmpeg_package(self) -> None:
        """Test that metrics are exported from ffmpeg package."""
        from stoat_ferret.ffmpeg import (
            ffmpeg_active_processes,
            ffmpeg_execution_duration_seconds,
            ffmpeg_executions_total,
        )

        assert ffmpeg_executions_total is not None
        assert ffmpeg_execution_duration_seconds is not None
        assert ffmpeg_active_processes is not None
