"""Deferred contract tests verifying compile_automation output is accepted by FFmpeg.

Gate: set STOAT_TEST_FFMPEG=1 (or equivalent) to run these tests.
These tests require FFmpeg installed and a real subprocess call to validate
that the compiled expression string is syntactically accepted by FFmpeg's
lavfi/sendcmd/volume filter system.

deferred_post_merge: these tests are skipped in normal CI and are discharged
as part of the FFmpeg-gated test suite (BL-418-AC-6).
"""

from __future__ import annotations

import subprocess

import pytest

from stoat_ferret_core import Automation, Keyframe, compile_automation
from tests.conftest import requires_ffmpeg

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_lavfi_volume_command(expr: str) -> list[str]:
    """Build an FFmpeg command that uses an expression in the volume filter.

    Creates a 0.5-second silent lavfi tone and applies a volume filter using
    the compiled automation expression. A non-zero exit code indicates FFmpeg
    rejected the expression as syntactically invalid.
    """
    return [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=0.5",
        "-af",
        f"volume='{expr}'",
        "-f",
        "null",
        "-",
    ]


def _run_ffmpeg_expression_check(expr: str) -> subprocess.CompletedProcess[bytes]:
    """Run FFmpeg to check whether an expression is accepted."""
    cmd = _build_lavfi_volume_command(expr)
    return subprocess.run(
        cmd,
        capture_output=True,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


@pytest.mark.contract
@requires_ffmpeg
class TestAutomationContractFFmpeg:
    """Verify that compile_automation output is accepted by FFmpeg volume filter."""

    def test_constant_automation_accepted(self) -> None:
        """FFmpeg accepts a constant (no-keyframe) automation expression."""
        automation = Automation(default=0.8, keyframes=[])
        expr = compile_automation(automation)
        result = _run_ffmpeg_expression_check(expr)
        assert result.returncode == 0, (
            f"FFmpeg rejected constant automation expression {expr!r}.\n"
            f"stderr: {result.stderr.decode(errors='replace')}"
        )

    def test_single_keyframe_automation_accepted(self) -> None:
        """FFmpeg accepts a single-keyframe (constant) automation expression."""
        automation = Automation(default=0.0, keyframes=[Keyframe(t=0.0, value=0.5, curve="Hold")])
        expr = compile_automation(automation)
        result = _run_ffmpeg_expression_check(expr)
        assert result.returncode == 0, (
            f"FFmpeg rejected single-keyframe expression {expr!r}.\n"
            f"stderr: {result.stderr.decode(errors='replace')}"
        )

    def test_linear_ramp_automation_accepted(self) -> None:
        """FFmpeg accepts a two-keyframe linear ramp expression."""
        automation = Automation(
            default=0.0,
            keyframes=[
                Keyframe(t=0.0, value=0.0, curve="Linear"),
                Keyframe(t=0.5, value=1.0, curve="Hold"),
            ],
        )
        expr = compile_automation(automation)
        result = _run_ffmpeg_expression_check(expr)
        assert result.returncode == 0, (
            f"FFmpeg rejected linear ramp expression {expr!r}.\n"
            f"stderr: {result.stderr.decode(errors='replace')}"
        )

    def test_exponential_curve_automation_accepted(self) -> None:
        """FFmpeg accepts an exponential curve automation expression."""
        automation = Automation(
            default=0.0,
            keyframes=[
                Keyframe(t=0.0, value=0.0, curve="Exponential"),
                Keyframe(t=0.5, value=1.0, curve="Hold"),
            ],
        )
        expr = compile_automation(automation)
        result = _run_ffmpeg_expression_check(expr)
        assert result.returncode == 0, (
            f"FFmpeg rejected exponential expression {expr!r}.\n"
            f"stderr: {result.stderr.decode(errors='replace')}"
        )

    def test_ease_in_out_automation_accepted(self) -> None:
        """FFmpeg accepts an ease-in-out automation expression."""
        automation = Automation(
            default=0.0,
            keyframes=[
                Keyframe(t=0.0, value=0.0, curve="EaseInOut"),
                Keyframe(t=0.5, value=1.0, curve="Hold"),
            ],
        )
        expr = compile_automation(automation)
        result = _run_ffmpeg_expression_check(expr)
        assert result.returncode == 0, (
            f"FFmpeg rejected ease-in-out expression {expr!r}.\n"
            f"stderr: {result.stderr.decode(errors='replace')}"
        )

    def test_multi_segment_automation_accepted(self) -> None:
        """FFmpeg accepts a multi-segment automation expression."""
        automation = Automation(
            default=0.0,
            keyframes=[
                Keyframe(t=0.0, value=0.0, curve="Linear"),
                Keyframe(t=0.1, value=0.8, curve="EaseInOut"),
                Keyframe(t=0.3, value=0.5, curve="Hold"),
                Keyframe(t=0.5, value=1.0, curve="Hold"),
            ],
        )
        expr = compile_automation(automation)
        result = _run_ffmpeg_expression_check(expr)
        assert result.returncode == 0, (
            f"FFmpeg rejected multi-segment expression {expr!r}.\n"
            f"stderr: {result.stderr.decode(errors='replace')}"
        )
