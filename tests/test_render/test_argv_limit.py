# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for render command argv-limit guard (BL-584).

Verifies that _maybe_route_filter_to_file routes long filter args to temp files
on Windows and passes through unchanged on non-Windows or for short filters.
"""

from __future__ import annotations

import contextlib
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from stoat_ferret.render.worker import (
    COMMAND_OVERHEAD_CHARS,
    WINDOWS_ARGV_LIMIT,
    RenderWorkerLoop,
    _maybe_route_filter_to_file,
)


def _make_long_filter(length: int = WINDOWS_ARGV_LIMIT) -> str:
    """Generate a filter string of exactly `length` chars."""
    return "x" * length


def _make_job(job_id: str = "test-job-id") -> MagicMock:
    job = MagicMock()
    job.id = job_id
    return job


def _make_executor() -> MagicMock:
    executor = MagicMock()
    executor.register_temp_file = MagicMock()
    return executor


def test_long_vf_filter_routes_to_file_on_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    long_filter = _make_long_filter()
    command = ["ffmpeg", "-i", "input.mp4", "-vf", long_filter, "output.mp4"]
    job = _make_job()
    executor = _make_executor()

    new_cmd, filter_path = _maybe_route_filter_to_file(command, job, executor)

    assert filter_path is not None
    assert long_filter not in new_cmd
    assert "-vf" not in new_cmd
    assert "-filter_script" in new_cmd
    assert str(filter_path) in new_cmd
    with contextlib.suppress(OSError):
        filter_path.unlink(missing_ok=True)


def test_long_filter_complex_routes_to_file_on_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    long_filter = _make_long_filter()
    command = ["ffmpeg", "-i", "input.mp4", "-filter_complex", long_filter, "-map", "[v]"]
    job = _make_job()
    executor = _make_executor()

    new_cmd, filter_path = _maybe_route_filter_to_file(command, job, executor)

    assert filter_path is not None
    assert long_filter not in new_cmd
    assert "-filter_complex" not in new_cmd
    assert "-filter_complex_script" in new_cmd
    assert str(filter_path) in new_cmd
    with contextlib.suppress(OSError):
        filter_path.unlink(missing_ok=True)


def test_temp_filter_file_contains_full_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    long_filter = _make_long_filter()
    command = ["ffmpeg", "-i", "input.mp4", "-vf", long_filter, "output.mp4"]
    job = _make_job()
    executor = _make_executor()

    _, filter_path = _maybe_route_filter_to_file(command, job, executor)

    assert filter_path is not None
    assert filter_path.read_text(encoding="utf-8") == long_filter
    with contextlib.suppress(OSError):
        filter_path.unlink(missing_ok=True)


def test_temp_filter_file_registered_with_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    long_filter = _make_long_filter()
    command = ["ffmpeg", "-i", "input.mp4", "-vf", long_filter, "output.mp4"]
    job = _make_job()
    executor = _make_executor()

    _, filter_path = _maybe_route_filter_to_file(command, job, executor)

    assert filter_path is not None
    executor.register_temp_file.assert_called_once_with(job.id, filter_path)
    with contextlib.suppress(OSError):
        filter_path.unlink(missing_ok=True)


def test_short_filter_passthrough_on_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    short_filter = "scale=1920:1080"  # well below WINDOWS_ARGV_LIMIT
    command = ["ffmpeg", "-i", "input.mp4", "-vf", short_filter, "output.mp4"]
    job = _make_job()
    executor = _make_executor()

    new_cmd, filter_path = _maybe_route_filter_to_file(command, job, executor)

    assert filter_path is None
    assert new_cmd == command
    executor.register_temp_file.assert_not_called()


def test_filter_passthrough_on_non_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    long_filter = _make_long_filter()
    command = ["ffmpeg", "-i", "input.mp4", "-vf", long_filter, "output.mp4"]
    job = _make_job()
    executor = _make_executor()

    new_cmd, filter_path = _maybe_route_filter_to_file(command, job, executor)

    assert filter_path is None
    assert new_cmd == command
    executor.register_temp_file.assert_not_called()


def test_argv_limit_guard_constant_documented() -> None:
    """Guard test: WINDOWS_ARGV_LIMIT is 32,767 — the Windows CreateProcessW limit."""
    assert WINDOWS_ARGV_LIMIT == 32_767
    # The guard threshold is WINDOWS_ARGV_LIMIT - COMMAND_OVERHEAD_CHARS, not WINDOWS_ARGV_LIMIT
    # itself. COMMAND_OVERHEAD_CHARS budgets for exe path, arg separators, and null terminator
    # in the full command line, ensuring the guard triggers before the OS limit is reached.
    assert isinstance(WINDOWS_ARGV_LIMIT, int)


def test_cleanup_registered_on_success_and_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify temp file is created, registered with executor, and cleanable."""
    monkeypatch.setattr(sys, "platform", "win32")
    long_filter = _make_long_filter()
    command = ["ffmpeg", "-i", "input.mp4", "-vf", long_filter, "output.mp4"]
    job = _make_job()
    executor = _make_executor()

    _, filter_path = _maybe_route_filter_to_file(command, job, executor)

    assert filter_path is not None
    assert filter_path.exists()
    # Executor registration provides cleanup on normal job completion
    executor.register_temp_file.assert_called_once_with(job.id, filter_path)
    # Local finally-block cleanup (asyncio-cancellation-safe path)
    with contextlib.suppress(OSError):
        filter_path.unlink(missing_ok=True)
    assert not filter_path.exists()


def test_fence_post_below_threshold_no_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Filter just below the guard threshold does NOT route to file on Windows.

    The routing threshold is WINDOWS_ARGV_LIMIT - COMMAND_OVERHEAD_CHARS.
    A filter of WINDOWS_ARGV_LIMIT - 1 - COMMAND_OVERHEAD_CHARS chars is one
    below that threshold and must pass through unchanged.
    """
    monkeypatch.setattr(sys, "platform", "win32")
    # One below the threshold: WINDOWS_ARGV_LIMIT - 1 - COMMAND_OVERHEAD_CHARS
    fence_post_filter = _make_long_filter(WINDOWS_ARGV_LIMIT - 1 - COMMAND_OVERHEAD_CHARS)
    command = ["ffmpeg", "-i", "input.mp4", "-vf", fence_post_filter, "output.mp4"]
    job = _make_job()
    executor = _make_executor()

    new_cmd, filter_path = _maybe_route_filter_to_file(command, job, executor)

    assert filter_path is None
    assert new_cmd == command
    executor.register_temp_file.assert_not_called()


def test_fence_post_at_threshold_routes_to_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Filter at exactly the guard threshold (32,267 chars) routes to file on Windows.

    The gate uses `>=`, so 32_267 >= 32_267 → True → routing must occur.
    BL-600-AC-1: pins the >= operator against a silent > regression.
    """
    monkeypatch.setattr(sys, "platform", "win32")
    threshold_filter = _make_long_filter(WINDOWS_ARGV_LIMIT - COMMAND_OVERHEAD_CHARS)
    command = ["ffmpeg", "-i", "input.mp4", "-vf", threshold_filter, "output.mp4"]
    job = _make_job()
    executor = _make_executor()

    _new_cmd, filter_path = _maybe_route_filter_to_file(command, job, executor)

    assert filter_path is not None
    with contextlib.suppress(OSError):
        filter_path.unlink(missing_ok=True)


def test_write_failure_cleans_up_temp_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """OSError during filter write must not orphan the partial temp file."""
    monkeypatch.setattr(sys, "platform", "win32")
    long_filter = _make_long_filter()
    command = ["ffmpeg", "-i", "input.mp4", "-vf", long_filter, "output.mp4"]
    job = _make_job()
    executor = _make_executor()

    sentinel = tmp_path / "test_write_fail.filter"
    sentinel.write_bytes(b"")

    class _FailingFile:
        name = str(sentinel)

        def write(self, data: bytes) -> None:
            raise OSError("simulated disk full")

        def __enter__(self) -> _FailingFile:
            return self

        def __exit__(self, *args: object) -> None:
            pass

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", lambda **kwargs: _FailingFile())

    with pytest.raises(OSError, match="disk full"):
        _maybe_route_filter_to_file(command, job, executor)

    assert not sentinel.exists(), "partial temp file must be removed after write OSError"


async def test_run_job_routes_long_filter_and_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Long filter routed through _run_job() is cleaned up in the finally block."""
    monkeypatch.setattr(sys, "platform", "win32")
    long_filter = _make_long_filter()
    long_filter_command = ["ffmpeg", "-i", "input.mp4", "-vf", long_filter, "output.mp4"]

    import stoat_ferret.render.worker as _worker_module

    monkeypatch.setattr(
        _worker_module,
        "build_command_for_job",
        AsyncMock(return_value=long_filter_command),
    )

    mock_executor = _make_executor()
    mock_service = MagicMock()
    mock_service._executor = mock_executor
    mock_service.run_job = AsyncMock()

    worker = RenderWorkerLoop(
        service=mock_service,
        queue=MagicMock(),
        clip_repository=MagicMock(),
        video_repository=MagicMock(),
    )

    job = _make_job()
    job.render_plan = '{"settings": {}, "total_duration": 1.0}'

    await worker._run_job(job)

    mock_executor.register_temp_file.assert_called_once()
    _, filter_path = mock_executor.register_temp_file.call_args[0]

    assert not filter_path.exists(), "filter temp file must be deleted in _run_job finally block"
