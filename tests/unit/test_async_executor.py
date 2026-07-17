# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for async FFmpeg executor.

Verifies that RealAsyncFFmpegExecutor uses exclusive stderr reading via
_read_stderr() task without concurrent reads from process.communicate(),
which Python 3.13 asyncio.StreamReader disallows.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from stoat_ferret.ffmpeg.async_executor import (
    FakeAsyncFFmpegExecutor,
    ProgressInfo,
    RealAsyncFFmpegExecutor,
    parse_progress_line,
)


def _make_mock_process(
    *,
    returncode: int = 0,
    stdout_data: bytes = b"",
    stderr_lines: list[bytes] | None = None,
) -> MagicMock:
    """Create a mock asyncio subprocess with configurable stdout/stderr.

    Args:
        returncode: Exit code for the mock process.
        stdout_data: Bytes returned by process.stdout.read().
        stderr_lines: Lines yielded by process.stderr.readline(); b"" appended
            automatically to signal EOF.

    Returns:
        MagicMock configured to simulate an asyncio subprocess.
    """
    lines: list[bytes] = (stderr_lines or []) + [b""]
    readline_iter = iter(lines)

    process = MagicMock()
    process.returncode = returncode
    process.pid = 12345
    process.stdout = MagicMock()
    process.stdout.read = AsyncMock(return_value=stdout_data)
    process.stderr = MagicMock()
    process.stderr.readline = AsyncMock(side_effect=lambda: next(readline_iter, b""))
    process.wait = AsyncMock()
    # communicate() should NOT be called — include it so we can assert it isn't.
    process.communicate = AsyncMock(return_value=(stdout_data, b""))
    process.terminate = MagicMock()
    return process


# ---------- parse_progress_line ----------


class TestParseProgressLine:
    """Tests for parse_progress_line function."""

    def test_parses_out_time_us(self) -> None:
        info = ProgressInfo()
        result = parse_progress_line("out_time_us=1000000", info)
        assert result.out_time_us == 1_000_000

    def test_parses_speed_with_x_suffix(self) -> None:
        info = ProgressInfo()
        result = parse_progress_line("speed=2.5x", info)
        assert result.speed == 2.5

    def test_parses_fps(self) -> None:
        info = ProgressInfo()
        result = parse_progress_line("fps=30.0", info)
        assert result.fps == 30.0

    def test_ignores_unknown_keys(self) -> None:
        info = ProgressInfo()
        result = parse_progress_line("bitrate=1500k", info)
        assert result.out_time_us == 0
        assert result.speed == 0.0

    def test_handles_non_parseable_speed(self) -> None:
        info = ProgressInfo()
        result = parse_progress_line("speed=N/A", info)
        assert result.speed == 0.0

    def test_ignores_lines_without_equals(self) -> None:
        info = ProgressInfo()
        result = parse_progress_line("no equals here", info)
        assert result.out_time_us == 0

    def test_mutates_info_in_place(self) -> None:
        info = ProgressInfo()
        returned = parse_progress_line("out_time_us=42", info)
        assert returned is info
        assert info.out_time_us == 42


# ---------- RealAsyncFFmpegExecutor ----------


class TestRealAsyncFFmpegExecutor:
    """Tests for RealAsyncFFmpegExecutor.

    Focus: verifies the exclusive-stderr-reader pattern (no concurrent reads
    via communicate()) and progress callback behaviour.
    """

    async def test_uses_wait_not_communicate(self) -> None:
        """Executor calls process.wait(), never process.communicate()."""
        mock_process = _make_mock_process()
        executor = RealAsyncFFmpegExecutor()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await executor.run(["-version"])

        mock_process.communicate.assert_not_called()
        mock_process.wait.assert_called_once()

    async def test_stdout_read_directly(self) -> None:
        """Executor reads stdout via process.stdout.read(), not communicate()."""
        mock_process = _make_mock_process(stdout_data=b"stdout bytes")
        executor = RealAsyncFFmpegExecutor()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await executor.run(["-version"])

        mock_process.stdout.read.assert_called_once()
        assert result.stdout == b"stdout bytes"

    async def test_stderr_captured_via_reader_task(self) -> None:
        """Stderr output is collected by _read_stderr() and returned in result."""
        stderr_lines = [b"FFmpeg version 6.0\n", b"libavcodec 60.0\n"]
        mock_process = _make_mock_process(stderr_lines=stderr_lines)
        executor = RealAsyncFFmpegExecutor()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await executor.run(["-version"])

        assert b"FFmpeg version 6.0" in result.stderr
        assert b"libavcodec 60.0" in result.stderr

    async def test_progress_callback_fires_during_execution(self) -> None:
        """Progress callback receives ProgressInfo for each parsed stderr line."""
        received: list[int] = []

        async def on_progress(info: ProgressInfo) -> None:
            received.append(info.out_time_us)

        stderr_lines = [
            b"out_time_us=500000\n",
            b"out_time_us=1000000\n",
        ]
        mock_process = _make_mock_process(stderr_lines=stderr_lines)
        executor = RealAsyncFFmpegExecutor()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await executor.run(["-version"], progress_callback=on_progress)

        assert 500_000 in received
        assert 1_000_000 in received

    async def test_progress_callback_failure_does_not_crash_executor(self) -> None:
        """Executor completes normally even if progress callback raises."""

        async def failing_callback(info: ProgressInfo) -> None:
            raise RuntimeError("callback exploded")

        stderr_lines = [b"out_time_us=500000\n"]
        mock_process = _make_mock_process(stderr_lines=stderr_lines, returncode=0)
        executor = RealAsyncFFmpegExecutor()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await executor.run(["-version"], progress_callback=failing_callback)

        assert result.returncode == 0

    async def test_returncode_propagated(self) -> None:
        """ExecutionResult.returncode matches the mock process returncode."""
        mock_process = _make_mock_process(returncode=1)
        executor = RealAsyncFFmpegExecutor()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await executor.run(["-version"])

        assert result.returncode == 1

    async def test_command_includes_ffmpeg_path(self) -> None:
        """ExecutionResult.command begins with the configured ffmpeg path."""
        mock_process = _make_mock_process()
        executor = RealAsyncFFmpegExecutor(ffmpeg_path="/usr/local/bin/ffmpeg")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await executor.run(["-i", "in.mp4"])

        assert result.command[0] == "/usr/local/bin/ffmpeg"
        assert result.command[1:] == ["-i", "in.mp4"]

    async def test_cancel_event_terminates_process(self) -> None:
        """Setting cancel event before process.returncode is set calls terminate()."""
        cancel_event = asyncio.Event()

        # Simulate a process that hasn't exited yet when cancelled.
        mock_process = _make_mock_process()
        mock_process.returncode = None  # process still running

        async def set_cancel_then_complete() -> None:
            # Let _monitor_cancel task start waiting
            await asyncio.sleep(0)
            cancel_event.set()
            # After terminate() is called, simulate process exit
            await asyncio.sleep(0)
            mock_process.returncode = -15

        async def slow_read() -> bytes:
            # Block stdout.read() long enough for cancel to fire
            await asyncio.sleep(0.05)
            return b""

        mock_process.stdout.read = slow_read

        executor = RealAsyncFFmpegExecutor()
        task = asyncio.create_task(set_cancel_then_complete())

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await executor.run(["-version"], cancel_event=cancel_event)

        await task
        mock_process.terminate.assert_called_once()


# ---------- FakeAsyncFFmpegExecutor ----------


class TestFakeAsyncFFmpegExecutor:
    """Tests for FakeAsyncFFmpegExecutor test double."""

    async def test_records_all_calls(self) -> None:
        executor = FakeAsyncFFmpegExecutor()
        await executor.run(["-i", "input.mp4"])
        await executor.run(["-version"])
        assert executor.calls == [["-i", "input.mp4"], ["-version"]]

    async def test_configurable_returncode(self) -> None:
        executor = FakeAsyncFFmpegExecutor(returncode=2)
        result = await executor.run([])
        assert result.returncode == 2

    async def test_fires_progress_callback_per_stderr_line(self) -> None:
        """FakeAsyncFFmpegExecutor invokes progress callback for each stderr line."""
        received: list[int] = []

        async def on_progress(info: ProgressInfo) -> None:
            received.append(info.out_time_us)

        executor = FakeAsyncFFmpegExecutor(stderr_lines=["out_time_us=1000000"])
        await executor.run([], progress_callback=on_progress)

        assert received == [1_000_000]

    async def test_stderr_in_result(self) -> None:
        executor = FakeAsyncFFmpegExecutor(stderr_lines=["line one", "line two"])
        result = await executor.run([])
        assert b"line one" in result.stderr
        assert b"line two" in result.stderr

    async def test_no_call_when_no_progress_callback(self) -> None:
        """FakeAsyncFFmpegExecutor runs without a progress callback."""
        executor = FakeAsyncFFmpegExecutor(stderr_lines=["out_time_us=1000000"])
        result = await executor.run([])
        assert result.returncode == 0
