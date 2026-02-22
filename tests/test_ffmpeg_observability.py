"""Tests for FFmpeg observability DI wiring.

Verifies that ObservableFFmpegExecutor is correctly wired into the
dependency injection chain and that metrics/logs are emitted.
"""

from __future__ import annotations

import structlog
from prometheus_client import REGISTRY

from stoat_ferret.ffmpeg.executor import ExecutionResult
from stoat_ferret.ffmpeg.observable import ObservableFFmpegExecutor


class MockExecutor:
    """Mock FFmpegExecutor for testing observability wiring."""

    def __init__(
        self,
        returncode: int = 0,
        duration_seconds: float = 0.5,
    ) -> None:
        """Initialize with configurable return values."""
        self.returncode = returncode
        self.duration_seconds = duration_seconds
        self.calls: list[list[str]] = []

    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        """Return mock result and record the call."""
        self.calls.append(args)
        return ExecutionResult(
            returncode=self.returncode,
            stdout=b"",
            stderr=b"",
            command=["ffmpeg", *args],
            duration_seconds=self.duration_seconds,
        )


class TestObservableExecutorWiring:
    """Tests for ObservableFFmpegExecutor DI wiring in create_app()."""

    def test_create_app_ffmpeg_executor_kwarg_stored_directly(self) -> None:
        """create_app(ffmpeg_executor=mock) stores mock without wrapping (FR-002)."""
        from stoat_ferret.api.app import create_app
        from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
        from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
        from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository

        mock = MockExecutor()
        app = create_app(
            video_repository=AsyncInMemoryVideoRepository(),
            project_repository=AsyncInMemoryProjectRepository(),
            clip_repository=AsyncInMemoryClipRepository(),
            ffmpeg_executor=mock,
        )

        assert app.state.ffmpeg_executor is mock
        assert not isinstance(app.state.ffmpeg_executor, ObservableFFmpegExecutor)

    def test_recording_executor_injectable_without_wrapping(self) -> None:
        """Recording test double remains injectable via create_app() (NFR-001)."""
        from stoat_ferret.api.app import create_app
        from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
        from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
        from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository

        mock = MockExecutor()
        app = create_app(
            video_repository=AsyncInMemoryVideoRepository(),
            project_repository=AsyncInMemoryProjectRepository(),
            clip_repository=AsyncInMemoryClipRepository(),
            ffmpeg_executor=mock,
        )

        # Verify it's stored directly, not wrapped
        assert app.state.ffmpeg_executor is mock


class TestObservableExecutorStructlog:
    """Tests for structured log emission through ObservableFFmpegExecutor (FR-003)."""

    def test_emits_structlog_with_correlation_id_and_duration(
        self,
    ) -> None:
        """FFmpeg execution emits structlog with correlation_id and duration."""
        captured: list[dict[str, object]] = []

        def capture_event(
            _logger: object, _method: str, event_dict: dict[str, object]
        ) -> dict[str, object]:
            captured.append(event_dict.copy())
            return event_dict

        structlog.configure(
            processors=[capture_event, structlog.dev.ConsoleRenderer()],
            wrapper_class=structlog.BoundLogger,
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=False,
        )

        mock = MockExecutor(returncode=0, duration_seconds=1.23)
        observable = ObservableFFmpegExecutor(mock)
        observable.run(["-i", "input.mp4", "output.mp4"], correlation_id="test-corr-42")

        # Find the completion log event
        completed_events = [e for e in captured if e.get("event") == "ffmpeg_execution_completed"]
        assert len(completed_events) == 1

        event = completed_events[0]
        assert event["correlation_id"] == "test-corr-42"
        assert event["duration_seconds"] == 1.23

        # Find the started log event
        started_events = [e for e in captured if e.get("event") == "ffmpeg_execution_started"]
        assert len(started_events) == 1
        assert started_events[0]["correlation_id"] == "test-corr-42"

    def test_emits_command_preview_in_logs(self) -> None:
        """FFmpeg execution logs include command args preview."""
        captured: list[dict[str, object]] = []

        def capture_event(
            _logger: object, _method: str, event_dict: dict[str, object]
        ) -> dict[str, object]:
            captured.append(event_dict.copy())
            return event_dict

        structlog.configure(
            processors=[capture_event, structlog.dev.ConsoleRenderer()],
            wrapper_class=structlog.BoundLogger,
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=False,
        )

        mock = MockExecutor()
        observable = ObservableFFmpegExecutor(mock)
        observable.run(["-i", "input.mp4", "-c:v", "libx264", "output.mp4"])

        started_events = [e for e in captured if e.get("event") == "ffmpeg_execution_started"]
        assert len(started_events) == 1
        assert "command_args" in started_events[0]


class TestObservableExecutorMetrics:
    """Tests for Prometheus metrics population through ObservableFFmpegExecutor (FR-004)."""

    def _get_metric_value(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get the current value of a metric."""
        value = REGISTRY.get_sample_value(name, labels or {})
        return value or 0.0

    def test_execution_counter_increments(self) -> None:
        """ffmpeg_executions_total counter increments after execution."""
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

    def test_duration_histogram_records(self) -> None:
        """ffmpeg_execution_duration_seconds histogram records after execution."""
        before_sum = self._get_metric_value("stoat_ferret_ffmpeg_execution_duration_seconds_sum")

        mock = MockExecutor(returncode=0, duration_seconds=3.14)
        observable = ObservableFFmpegExecutor(mock)
        observable.run(["-version"])

        after_sum = self._get_metric_value("stoat_ferret_ffmpeg_execution_duration_seconds_sum")
        assert after_sum >= before_sum + 3.14
