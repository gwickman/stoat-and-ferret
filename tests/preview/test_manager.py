# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for preview manager helpers."""

from __future__ import annotations

from stoat_ferret.preview.manager import PREVIEW_STDERR_MAX_LINES, _truncate_stderr


def test_truncate_stderr_above_cap() -> None:
    """200-line input produces truncated output with the expected marker."""
    lines = [f"line {i:03d}" for i in range(200)]
    result = _truncate_stderr(lines)

    assert "[... 150 lines truncated ...]" in result
    assert len(result.splitlines()) < 60


def test_truncate_stderr_below_cap() -> None:
    """30-line input (below default 50) is returned verbatim."""
    lines = [f"line {i:03d}" for i in range(30)]
    result = _truncate_stderr(lines)

    assert result == "\n".join(lines)
    assert "[... " not in result


def test_truncate_stderr_exactly_cap() -> None:
    """Input at exactly PREVIEW_STDERR_MAX_LINES is returned verbatim."""
    lines = [f"line {i:03d}" for i in range(PREVIEW_STDERR_MAX_LINES)]
    result = _truncate_stderr(lines)

    assert result == "\n".join(lines)
    assert "[... " not in result


def test_truncate_stderr_tail_preserved() -> None:
    """The last line of a long input appears in the truncated output."""
    banner = [f"ffmpeg version banner line {i}" for i in range(100)]
    error_lines = ["Error: something went wrong", "Exit code: 1"]
    lines = banner + error_lines
    result = _truncate_stderr(lines)

    assert "Error: something went wrong" in result
    assert "Exit code: 1" in result
    assert "[... " in result
