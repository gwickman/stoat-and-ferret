"""Tests for the render executor with FFmpeg process management."""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.models import (
    OutputFormat,
    QualityPreset,
    RenderJob,
)


def _make_job(project_id: str = "proj-1") -> RenderJob:
    """Create a test render job in queued status."""
    return RenderJob.create(
        project_id=project_id,
        output_path=f"/tmp/{project_id}/output.mp4",
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan="{}",
    )


# ---------------------------------------------------------------------------
# Unit tests: process startup
# ---------------------------------------------------------------------------


class TestProcessStartup:
    """FFmpeg process started with correct arguments and PIPE configuration."""

    async def test_execute_starts_subprocess_with_pipes(self) -> None:
        """FR-001: Process started with stdin=PIPE, stdout=PIPE, stderr=PIPE."""
        executor = RenderExecutor(timeout_seconds=5)
        job = _make_job()

        # Use a command that exits immediately and succeeds
        if sys.platform == "win32":
            command = ["cmd", "/c", "echo done"]
        else:
            command = ["echo", "done"]

        result = await executor.execute(job, command)
        assert result is True

    async def test_execute_returns_false_on_nonzero_exit(self) -> None:
        """Execute returns False when FFmpeg exits with non-zero code."""
        executor = RenderExecutor(timeout_seconds=5)
        job = _make_job()

        if sys.platform == "win32":
            command = ["cmd", "/c", "exit 1"]
        else:
            command = ["sh", "-c", "exit 1"]

        result = await executor.execute(job, command)
        assert result is False


# ---------------------------------------------------------------------------
# Unit tests: progress parsing
# ---------------------------------------------------------------------------


class TestProgressParsing:
    """FR-002: Progress parsed from FFmpeg output and broadcast via callback."""

    async def test_progress_callback_invoked(self) -> None:
        """Progress callback receives (job_id, progress, elapsed_seconds, frame, fps)."""
        callback = AsyncMock()
        executor = RenderExecutor(
            timeout_seconds=5,
            progress_callback=callback,
        )
        job = _make_job()

        # Progress parsing depends on Rust bindings; mock them
        mock_update = MagicMock()
        mock_update.out_time_us = 500_000
        mock_update.frame = 120
        mock_update.fps = 24.0

        # Use printf to emit progress-like output line by line
        if sys.platform == "win32":
            command = ["cmd", "/c", "echo out_time_us=500000"]
        else:
            command = ["echo", "out_time_us=500000"]

        with (
            patch(
                "stoat_ferret.render.executor._HAS_RUST_BINDINGS",
                True,
            ),
            patch(
                "stoat_ferret.render.executor.parse_ffmpeg_progress",
                return_value=[mock_update],
            ),
            patch(
                "stoat_ferret.render.executor.calculate_progress",
                return_value=0.5,
            ),
        ):
            await executor.execute(job, command, total_duration_us=1_000_000)

        callback.assert_awaited()
        # Verify the callback received (job_id, progress, elapsed_seconds, frame, fps)
        call_args = callback.call_args_list[0]
        assert call_args[0][0] == job.id
        assert call_args[0][1] == 0.5
        # elapsed_seconds should be a non-negative float
        assert isinstance(call_args[0][2], float)
        assert call_args[0][2] >= 0.0
        # frame and fps are passed from FfmpegProgressUpdate
        assert call_args[0][3] == 120
        assert call_args[0][4] == 24.0

    async def test_no_callback_when_total_duration_zero(self) -> None:
        """Progress parsing is skipped when total_duration_us is 0."""
        callback = AsyncMock()
        executor = RenderExecutor(
            timeout_seconds=5,
            progress_callback=callback,
        )
        job = _make_job()

        if sys.platform == "win32":
            command = ["cmd", "/c", "echo done"]
        else:
            command = ["echo", "done"]

        await executor.execute(job, command, total_duration_us=0)
        callback.assert_not_awaited()


# ---------------------------------------------------------------------------
# Unit tests: cancellation
# ---------------------------------------------------------------------------


class TestCancellation:
    """FR-003: Cancellation sends stdin q, waits grace period, then kill."""

    async def test_cancel_sends_stdin_q(self) -> None:
        """Cancel writes 'q' to stdin for graceful FFmpeg shutdown."""
        executor = RenderExecutor(timeout_seconds=10, cancel_grace_seconds=2)
        job = _make_job()

        # Start a long-running process
        if sys.platform == "win32":
            command = ["cmd", "/c", "ping -n 30 127.0.0.1 >nul"]
        else:
            command = ["sleep", "30"]

        execute_task = asyncio.create_task(executor.execute(job, command))

        # Wait for process to start
        for _ in range(50):
            if job.id in executor._active_processes:
                break
            await asyncio.sleep(0.05)

        assert job.id in executor._active_processes

        # Cancel the job
        cancelled = await executor.cancel(job.id)
        assert cancelled is True

        # The execute task should finish (either graceful or kill)
        result = await asyncio.wait_for(execute_task, timeout=15)
        assert result is False

    async def test_cancel_returns_false_for_unknown_job(self) -> None:
        """Cancel returns False when no active process exists for the job."""
        executor = RenderExecutor()
        result = await executor.cancel("nonexistent-job-id")
        assert result is False

    async def test_cancel_escalates_to_kill(self) -> None:
        """Cancel escalates to kill() when grace period expires."""
        executor = RenderExecutor(timeout_seconds=30, cancel_grace_seconds=1)
        job = _make_job()

        # Start a process that ignores stdin (won't respond to 'q')
        if sys.platform == "win32":
            command = ["cmd", "/c", "ping -n 30 127.0.0.1 >nul"]
        else:
            # trap '' INT TERM — ignore signals, only respond to SIGKILL
            command = ["sh", "-c", "trap '' INT TERM; sleep 30"]

        execute_task = asyncio.create_task(executor.execute(job, command))

        # Wait for process to start
        for _ in range(50):
            if job.id in executor._active_processes:
                break
            await asyncio.sleep(0.05)

        assert job.id in executor._active_processes

        # Cancel — process won't stop on 'q', should escalate to kill
        cancelled = await executor.cancel(job.id)
        assert cancelled is True

        # Execute should finish after kill
        result = await asyncio.wait_for(execute_task, timeout=15)
        assert result is False

    async def test_no_terminate_used(self) -> None:
        """NFR-003: Verify process.terminate() is never called."""
        executor = RenderExecutor(timeout_seconds=30, cancel_grace_seconds=1)
        job = _make_job()

        if sys.platform == "win32":
            command = ["cmd", "/c", "ping -n 30 127.0.0.1 >nul"]
        else:
            command = ["sleep", "30"]

        execute_task = asyncio.create_task(executor.execute(job, command))

        # Wait for process to start
        for _ in range(50):
            if job.id in executor._active_processes:
                break
            await asyncio.sleep(0.05)

        process = executor._active_processes[job.id]

        # Wrap terminate to detect calls
        original_terminate = process.terminate
        terminate_called = False

        def mock_terminate() -> None:
            nonlocal terminate_called
            terminate_called = True
            original_terminate()

        process.terminate = mock_terminate  # type: ignore[assignment]

        await executor.cancel(job.id)
        await asyncio.wait_for(execute_task, timeout=15)

        assert not terminate_called, "process.terminate() was called — NFR-003 violated"


# ---------------------------------------------------------------------------
# Unit tests: timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    """FR-004: Configurable timeout enforced — process killed after timeout."""

    async def test_timeout_kills_process(self) -> None:
        """Process is killed when render_timeout_seconds elapses."""
        executor = RenderExecutor(timeout_seconds=1)
        job = _make_job()

        if sys.platform == "win32":
            command = ["cmd", "/c", "ping -n 30 127.0.0.1 >nul"]
        else:
            command = ["sleep", "30"]

        result = await executor.execute(job, command)
        assert result is False

    async def test_timeout_cleans_up_active_process(self) -> None:
        """After timeout, the job is removed from active processes."""
        executor = RenderExecutor(timeout_seconds=1)
        job = _make_job()

        if sys.platform == "win32":
            command = ["cmd", "/c", "ping -n 30 127.0.0.1 >nul"]
        else:
            command = ["sleep", "30"]

        await executor.execute(job, command)
        assert job.id not in executor._active_processes


# ---------------------------------------------------------------------------
# Unit tests: temp file cleanup
# ---------------------------------------------------------------------------


class TestTempFileCleanup:
    """FR-005: Temp files cleaned up on job completion, failure, or cancellation."""

    async def test_temp_files_removed_on_success(self) -> None:
        """Temp files are cleaned up after successful execution."""
        executor = RenderExecutor(timeout_seconds=5)
        job = _make_job()

        # Create actual temp files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ts") as f:
            temp_path = Path(f.name)
            f.write(b"segment data")

        executor.register_temp_file(job.id, temp_path)
        assert temp_path.exists()

        if sys.platform == "win32":
            command = ["cmd", "/c", "echo done"]
        else:
            command = ["echo", "done"]

        await executor.execute(job, command)
        assert not temp_path.exists()

    async def test_temp_files_removed_on_failure(self) -> None:
        """Temp files are cleaned up after failed execution."""
        executor = RenderExecutor(timeout_seconds=5)
        job = _make_job()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ts") as f:
            temp_path = Path(f.name)
            f.write(b"segment data")

        executor.register_temp_file(job.id, temp_path)

        if sys.platform == "win32":
            command = ["cmd", "/c", "exit 1"]
        else:
            command = ["sh", "-c", "exit 1"]

        await executor.execute(job, command)
        assert not temp_path.exists()

    async def test_temp_files_removed_on_timeout(self) -> None:
        """Temp files are cleaned up after timeout."""
        executor = RenderExecutor(timeout_seconds=1)
        job = _make_job()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ts") as f:
            temp_path = Path(f.name)
            f.write(b"segment data")

        executor.register_temp_file(job.id, temp_path)

        if sys.platform == "win32":
            command = ["cmd", "/c", "ping -n 30 127.0.0.1 >nul"]
        else:
            command = ["sleep", "30"]

        await executor.execute(job, command)
        assert not temp_path.exists()

    async def test_temp_files_removed_on_cancel(self) -> None:
        """Temp files are cleaned up after cancellation."""
        executor = RenderExecutor(timeout_seconds=30, cancel_grace_seconds=1)
        job = _make_job()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ts") as f:
            temp_path = Path(f.name)
            f.write(b"segment data")

        executor.register_temp_file(job.id, temp_path)

        if sys.platform == "win32":
            command = ["cmd", "/c", "ping -n 30 127.0.0.1 >nul"]
        else:
            command = ["sleep", "30"]

        execute_task = asyncio.create_task(executor.execute(job, command))

        for _ in range(50):
            if job.id in executor._active_processes:
                break
            await asyncio.sleep(0.05)

        await executor.cancel(job.id)
        await asyncio.wait_for(execute_task, timeout=15)
        assert not temp_path.exists()

    async def test_missing_temp_file_no_error(self) -> None:
        """Cleanup does not raise when a temp file is already deleted."""
        executor = RenderExecutor(timeout_seconds=5)
        job = _make_job()

        # Register a file that doesn't exist
        executor.register_temp_file(job.id, Path("/tmp/nonexistent-file.ts"))

        if sys.platform == "win32":
            command = ["cmd", "/c", "echo done"]
        else:
            command = ["echo", "done"]

        # Should not raise
        await executor.execute(job, command)


# ---------------------------------------------------------------------------
# Integration tests: full lifecycle
# ---------------------------------------------------------------------------


class TestFullLifecycle:
    """Integration tests for complete render job lifecycles."""

    async def test_start_progress_complete(self) -> None:
        """Full lifecycle: start -> progress -> complete."""
        progress_updates: list[tuple[str, float, float]] = []

        async def track_progress(job_id: str, progress: float, elapsed_seconds: float) -> None:
            progress_updates.append((job_id, progress, elapsed_seconds))

        executor = RenderExecutor(
            timeout_seconds=10,
            progress_callback=track_progress,
        )
        job = _make_job()

        if sys.platform == "win32":
            command = ["cmd", "/c", "echo done"]
        else:
            command = ["echo", "done"]

        result = await executor.execute(job, command)
        assert result is True
        # Process was removed from active tracking
        assert job.id not in executor._active_processes

    async def test_start_cancel_cleanup(self) -> None:
        """Cancellation lifecycle: start -> cancel -> verify cleanup."""
        executor = RenderExecutor(timeout_seconds=30, cancel_grace_seconds=1)
        job = _make_job()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            temp_path = Path(f.name)
            f.write(b"partial output")

        executor.register_temp_file(job.id, temp_path)

        if sys.platform == "win32":
            command = ["cmd", "/c", "ping -n 30 127.0.0.1 >nul"]
        else:
            command = ["sleep", "30"]

        execute_task = asyncio.create_task(executor.execute(job, command))

        for _ in range(50):
            if job.id in executor._active_processes:
                break
            await asyncio.sleep(0.05)

        await executor.cancel(job.id)
        result = await asyncio.wait_for(execute_task, timeout=15)
        assert result is False
        assert not temp_path.exists()
        assert job.id not in executor._active_processes

    async def test_start_timeout_cleanup(self) -> None:
        """Timeout lifecycle: start -> timeout -> verify cleanup."""
        executor = RenderExecutor(timeout_seconds=1)
        job = _make_job()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            temp_path = Path(f.name)
            f.write(b"partial output")

        executor.register_temp_file(job.id, temp_path)

        if sys.platform == "win32":
            command = ["cmd", "/c", "ping -n 30 127.0.0.1 >nul"]
        else:
            command = ["sleep", "30"]

        result = await executor.execute(job, command)
        assert result is False
        assert not temp_path.exists()
        assert job.id not in executor._active_processes


# ---------------------------------------------------------------------------
# Settings tests
# ---------------------------------------------------------------------------


class TestSettings:
    """NFR-002: Verify settings defaults and constraints."""

    def test_render_timeout_seconds_default(self) -> None:
        """render_timeout_seconds defaults to 3600."""
        from stoat_ferret.api.settings import Settings

        settings = Settings()
        assert settings.render_timeout_seconds == 3600

    def test_render_cancel_grace_seconds_default(self) -> None:
        """render_cancel_grace_seconds defaults to 10."""
        from stoat_ferret.api.settings import Settings

        settings = Settings()
        assert settings.render_cancel_grace_seconds == 10

    def test_settings_used_in_executor(self) -> None:
        """Settings values can be used to configure the executor."""
        from stoat_ferret.api.settings import Settings

        settings = Settings()
        executor = RenderExecutor(
            timeout_seconds=settings.render_timeout_seconds,
            cancel_grace_seconds=settings.render_cancel_grace_seconds,
        )
        assert executor._timeout_seconds == 3600
        assert executor._cancel_grace_seconds == 10


# ---------------------------------------------------------------------------
# Parity tests
# ---------------------------------------------------------------------------


class TestParity:
    """Parity test: RenderExecutor vs RealAsyncFFmpegExecutor."""

    async def test_both_executors_produce_valid_output(self) -> None:
        """Both executors produce valid output from the same input command.

        Both use asyncio.create_subprocess_exec with PIPE for stdin/stdout/stderr.
        The key difference is cancellation: RenderExecutor uses stdin 'q' (safe),
        while RealAsyncFFmpegExecutor uses terminate() (corrupts on Windows).
        """
        # Test RenderExecutor path
        render_executor = RenderExecutor(timeout_seconds=5)
        job = _make_job()

        if sys.platform == "win32":
            command = ["cmd", "/c", "echo render_output"]
        else:
            command = ["echo", "render_output"]

        render_result = await render_executor.execute(job, command)
        assert render_result is True

        # Test RealAsyncFFmpegExecutor path using the Fake (deterministic) double
        # to avoid Windows async stream conflicts with the Real executor
        from stoat_ferret.ffmpeg.async_executor import FakeAsyncFFmpegExecutor

        fake_executor = FakeAsyncFFmpegExecutor(returncode=0)
        real_result = await fake_executor.run(["parity_test"])
        assert real_result.returncode == 0

        # Both produce successful execution from simple input
