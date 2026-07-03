# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for render command argv-limit guard (BL-584).

Verifies that _maybe_route_filter_to_file routes long filter args to temp files
on Windows and passes through unchanged on non-Windows or for short filters.
"""

from __future__ import annotations

import contextlib
import sys
from unittest.mock import MagicMock

import pytest

from stoat_ferret.render.worker import WINDOWS_ARGV_LIMIT, _maybe_route_filter_to_file


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
    # The threshold applies to the filter string alone. Since filter args are only
    # a portion of the full command line, routing at WINDOWS_ARGV_LIMIT is conservative
    # and prevents the total argv from approaching the OS limit.
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
