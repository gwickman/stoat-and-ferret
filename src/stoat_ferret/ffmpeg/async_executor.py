"""Async FFmpeg executor for long-running transcoding operations.

Provides a protocol-based async abstraction for FFmpeg execution with:
- RealAsyncFFmpegExecutor: Actual async subprocess execution with progress parsing
- FakeAsyncFFmpegExecutor: Deterministic test double
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Protocol

import structlog

from stoat_ferret.ffmpeg.executor import ExecutionResult

logger = structlog.get_logger(__name__)


@dataclass
class ProgressInfo:
    """Parsed progress information from FFmpeg -progress output.

    Attributes:
        out_time_us: Output time in microseconds.
        speed: Encoding speed multiplier (e.g., 2.5x).
        fps: Current frames per second.
    """

    out_time_us: int = 0
    speed: float = 0.0
    fps: float = 0.0


# Type alias for progress callbacks
ProgressCallback = Callable[[ProgressInfo], Awaitable[None]]


class AsyncFFmpegExecutor(Protocol):
    """Protocol for async FFmpeg command execution."""

    async def run(
        self,
        args: list[str],
        *,
        progress_callback: ProgressCallback | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> ExecutionResult:
        """Execute FFmpeg asynchronously with the given arguments.

        Args:
            args: Arguments to pass to ffmpeg (not including the ffmpeg command).
            progress_callback: Optional callback invoked with parsed progress info.
            cancel_event: Optional event; when set, the process is terminated.

        Returns:
            ExecutionResult with the outcome of the execution.
        """
        ...


def parse_progress_line(line: str, info: ProgressInfo) -> ProgressInfo:
    """Parse a single line from FFmpeg -progress pipe:2 output.

    FFmpeg emits key=value pairs, one per line, with blocks separated
    by 'progress=continue' or 'progress=end'.

    Args:
        line: A single line from FFmpeg stderr progress output.
        info: The ProgressInfo to update in place.

    Returns:
        The updated ProgressInfo.
    """
    line = line.strip()
    if "=" not in line:
        return info

    key, _, value = line.partition("=")
    key = key.strip()
    value = value.strip()

    if key == "out_time_us":
        with contextlib.suppress(ValueError):
            info.out_time_us = int(value)
    elif key == "speed":
        # speed is like "2.5x" or "N/A"
        value = value.rstrip("x")
        with contextlib.suppress(ValueError):
            info.speed = float(value)
    elif key == "fps":
        with contextlib.suppress(ValueError):
            info.fps = float(value)

    return info


class RealAsyncFFmpegExecutor:
    """Async executor that runs FFmpeg via asyncio.create_subprocess_exec.

    Parses progress from stderr when -progress pipe:2 is used.
    Supports cooperative cancellation via an asyncio.Event.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        """Initialize with the path to ffmpeg executable.

        Args:
            ffmpeg_path: Path to the ffmpeg executable.
        """
        self.ffmpeg_path = ffmpeg_path

    async def run(
        self,
        args: list[str],
        *,
        progress_callback: ProgressCallback | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> ExecutionResult:
        """Execute FFmpeg asynchronously.

        Args:
            args: Arguments to pass to ffmpeg.
            progress_callback: Optional async callback invoked with ProgressInfo.
            cancel_event: Optional event; when set, the process is terminated.

        Returns:
            ExecutionResult with the outcome of the execution.
        """
        command = [self.ffmpeg_path, *args]
        start = time.monotonic()

        logger.info("async_ffmpeg_started", command=command)

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stderr_chunks: list[bytes] = []
        info = ProgressInfo()

        async def _read_stderr() -> None:
            assert process.stderr is not None
            while True:
                line_bytes = await process.stderr.readline()
                if not line_bytes:
                    break
                stderr_chunks.append(line_bytes)
                line = line_bytes.decode("utf-8", errors="replace")
                parse_progress_line(line, info)
                if progress_callback is not None:
                    await progress_callback(info)

        async def _monitor_cancel() -> None:
            if cancel_event is None:
                return
            await cancel_event.wait()
            if process.returncode is None:
                logger.info("async_ffmpeg_cancelling", pid=process.pid)
                process.terminate()

        # Run stderr reading and cancel monitoring concurrently
        reader_task = asyncio.create_task(_read_stderr())
        cancel_task = asyncio.create_task(_monitor_cancel())

        try:
            stdout, _ = await process.communicate()
        finally:
            cancel_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await cancel_task
            await reader_task

        duration = time.monotonic() - start
        stderr = b"".join(stderr_chunks)

        logger.info(
            "async_ffmpeg_completed",
            returncode=process.returncode,
            duration_seconds=round(duration, 2),
        )

        return ExecutionResult(
            returncode=process.returncode or 0,
            stdout=stdout or b"",
            stderr=stderr,
            command=command,
            duration_seconds=duration,
        )


@dataclass
class FakeAsyncFFmpegExecutor:
    """Fake async executor for deterministic testing.

    Allows configuring return codes, progress emissions, and
    simulated durations without running actual FFmpeg.
    """

    returncode: int = 0
    stderr_lines: list[str] = field(default_factory=list)
    stdout: bytes = b""
    calls: list[list[str]] = field(default_factory=list)

    async def run(
        self,
        args: list[str],
        *,
        progress_callback: ProgressCallback | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> ExecutionResult:
        """Simulate FFmpeg execution.

        Records args and optionally feeds stderr_lines to the progress callback.

        Args:
            args: Arguments (recorded for assertion).
            progress_callback: Optional callback to invoke with progress.
            cancel_event: Optional cancel event (checked but not awaited).

        Returns:
            Pre-configured ExecutionResult.
        """
        self.calls.append(args)

        info = ProgressInfo()
        for line in self.stderr_lines:
            parse_progress_line(line, info)
            if progress_callback is not None:
                await progress_callback(info)

        stderr = "\n".join(self.stderr_lines).encode("utf-8")
        return ExecutionResult(
            returncode=self.returncode,
            stdout=self.stdout,
            stderr=stderr,
            command=["ffmpeg", *args],
            duration_seconds=0.0,
        )
