"""Tests for the async FFmpeg executor module."""

from __future__ import annotations

import asyncio

from stoat_ferret.ffmpeg.async_executor import (
    FakeAsyncFFmpegExecutor,
    ProgressInfo,
    parse_progress_line,
)


class TestParseProgressLine:
    """Tests for FFmpeg progress line parsing."""

    def test_parse_out_time_us(self) -> None:
        """Parse out_time_us from progress output."""
        info = ProgressInfo()
        parse_progress_line("out_time_us=5000000", info)
        assert info.out_time_us == 5_000_000

    def test_parse_speed(self) -> None:
        """Parse speed from progress output."""
        info = ProgressInfo()
        parse_progress_line("speed=2.5x", info)
        assert info.speed == 2.5

    def test_parse_fps(self) -> None:
        """Parse fps from progress output."""
        info = ProgressInfo()
        parse_progress_line("fps=30.0", info)
        assert info.fps == 30.0

    def test_parse_invalid_value(self) -> None:
        """Invalid values are silently ignored."""
        info = ProgressInfo()
        parse_progress_line("out_time_us=not_a_number", info)
        assert info.out_time_us == 0

    def test_parse_speed_na(self) -> None:
        """N/A speed is silently ignored."""
        info = ProgressInfo()
        parse_progress_line("speed=N/A", info)
        assert info.speed == 0.0

    def test_parse_empty_line(self) -> None:
        """Empty lines are ignored."""
        info = ProgressInfo()
        parse_progress_line("", info)
        assert info.out_time_us == 0

    def test_parse_no_equals(self) -> None:
        """Lines without = are ignored."""
        info = ProgressInfo()
        parse_progress_line("progress continue", info)
        assert info.out_time_us == 0

    def test_parse_unknown_key(self) -> None:
        """Unknown keys are ignored."""
        info = ProgressInfo()
        parse_progress_line("bitrate=1234.5kbits/s", info)
        assert info.out_time_us == 0

    def test_parse_multiple_lines_updates_in_place(self) -> None:
        """Multiple lines update the same ProgressInfo."""
        info = ProgressInfo()
        parse_progress_line("out_time_us=1000000", info)
        parse_progress_line("speed=1.5x", info)
        parse_progress_line("fps=24.0", info)
        assert info.out_time_us == 1_000_000
        assert info.speed == 1.5
        assert info.fps == 24.0


class TestFakeAsyncFFmpegExecutor:
    """Tests for the fake async executor."""

    async def test_records_calls(self) -> None:
        """Executor records the args passed to each call."""
        executor = FakeAsyncFFmpegExecutor()
        await executor.run(["-i", "test.mp4", "-o", "out.mp4"])
        assert len(executor.calls) == 1
        assert executor.calls[0] == ["-i", "test.mp4", "-o", "out.mp4"]

    async def test_returns_configured_returncode(self) -> None:
        """Executor returns the configured return code."""
        executor = FakeAsyncFFmpegExecutor(returncode=1)
        result = await executor.run(["-i", "test.mp4"])
        assert result.returncode == 1

    async def test_returns_zero_by_default(self) -> None:
        """Executor returns zero by default."""
        executor = FakeAsyncFFmpegExecutor()
        result = await executor.run(["-i", "test.mp4"])
        assert result.returncode == 0

    async def test_invokes_progress_callback(self) -> None:
        """Executor invokes progress callback with stderr lines."""
        events: list[ProgressInfo] = []

        async def on_progress(info: ProgressInfo) -> None:
            events.append(
                ProgressInfo(
                    out_time_us=info.out_time_us,
                    speed=info.speed,
                    fps=info.fps,
                )
            )

        executor = FakeAsyncFFmpegExecutor(
            stderr_lines=[
                "out_time_us=1000000",
                "speed=2.0x",
            ]
        )
        await executor.run(["-i", "test.mp4"], progress_callback=on_progress)
        assert len(events) == 2
        assert events[0].out_time_us == 1_000_000
        assert events[1].speed == 2.0

    async def test_command_includes_ffmpeg(self) -> None:
        """Result command starts with ffmpeg."""
        executor = FakeAsyncFFmpegExecutor()
        result = await executor.run(["-i", "test.mp4"])
        assert result.command[0] == "ffmpeg"
        assert result.command[1:] == ["-i", "test.mp4"]

    async def test_does_not_block_event_loop(self) -> None:
        """Verify async executor doesn't block (NFR-001)."""
        executor = FakeAsyncFFmpegExecutor()
        # Run concurrently with a trivial coroutine
        flag = False

        async def set_flag() -> None:
            nonlocal flag
            flag = True

        await asyncio.gather(
            executor.run(["-i", "test.mp4"]),
            set_flag(),
        )
        assert flag is True
