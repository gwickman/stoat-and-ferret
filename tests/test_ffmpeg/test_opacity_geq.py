# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""FFmpeg integration tests for OpacityBuilder geq animated opacity (BL-502).

Validates that:
  AC-1: geq with uppercase T parses and runs on FFmpeg 8.0.1
  AC-2: alpha channel changes over time (animated opacity)
  AC-3: composition survival — animated alpha in geq doesn't break overlay ordering

All tests are gated on STOAT_TEST_FFMPEG=1.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from stoat_ferret_core import Automation, Keyframe, OpacityBuilder

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="FFmpeg integration test; set STOAT_TEST_FFMPEG=1 to enable",
)


def _run_ffmpeg(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ffmpeg", *args],
        capture_output=True,
        text=True,
    )


def _build_animated_opacity_filter() -> str:
    """Build geq filter string for 0→1 opacity fade over 2 s."""
    auto = Automation(
        default=0.0,
        keyframes=[
            Keyframe(t=0.0, value=0.0, curve="Linear"),
            Keyframe(t=2.0, value=1.0, curve="Linear"),
        ],
    )
    return str(OpacityBuilder(opacity=0.0).with_automation(auto).build())


@_FFMPEG_SKIP
def test_geq_parses_on_ffmpeg(tmp_path: Path) -> None:
    """geq with uppercase T is accepted by FFmpeg (BL-502-AC-1)."""
    filter_str = _build_animated_opacity_filter()
    output = tmp_path / "out.mp4"
    result = _run_ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=black:size=64x64:duration=3:rate=24",
        "-vf",
        filter_str,
        "-frames:v",
        "24",
        "-y",
        str(output),
    )
    assert result.returncode == 0, (
        f"FFmpeg rejected geq opacity filter:\nfilter={filter_str!r}\n{result.stderr}"
    )
    assert output.exists() and output.stat().st_size > 0


@_FFMPEG_SKIP
def test_geq_alpha_changes_over_time(tmp_path: Path) -> None:
    """Alpha channel is non-constant for animated opacity (BL-502-AC-2).

    Encodes a 3-second fade-in, extracts alpha at t=0.5 s and t=1.5 s,
    and asserts they differ (proving time-varying opacity).
    """
    filter_str = _build_animated_opacity_filter()
    output = tmp_path / "out.mp4"
    result = _run_ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=red:size=64x64:duration=3:rate=24",
        "-vf",
        filter_str,
        "-y",
        str(output),
    )
    assert result.returncode == 0, f"FFmpeg failed during alpha-change test:\n{result.stderr}"

    # Use extractplanes=a to extract actual alpha pixel values from RGBA output.
    # Opacity ramp: 0→1 over 2 s at 24 fps.
    # frame 5 (≈0.21 s): opacity ≈ 0.10 → mean alpha ≈ 26
    # frame 43 (≈1.79 s): opacity ≈ 0.90 → mean alpha ≈ 229
    def _mean_alpha(frame_n: int) -> float:
        """Render one RGBA frame via lavfi+geq; return mean alpha [0..255] via extractplanes=a."""
        res = subprocess.run(
            [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                "color=red:size=64x64:rate=24:duration=3:pix_fmt=rgba",
                "-vf",
                f"{filter_str},select=eq(n\\,{frame_n}),setpts=PTS-STARTPTS,extractplanes=a",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "gray",
                "-frames:v",
                "1",
                "pipe:1",
            ],
            capture_output=True,
        )
        px = res.stdout
        if len(px) != 64 * 64:
            return -1.0
        return sum(px) / (64 * 64)

    early_alpha = _mean_alpha(5)  # frame 5 @ 24 fps ≈ t=0.21 s, expected opacity ≈ 0.10
    late_alpha = _mean_alpha(43)  # frame 43 @ 24 fps ≈ t=1.79 s, expected opacity ≈ 0.90

    assert early_alpha >= 0, "Failed to extract early alpha frame via extractplanes=a"
    assert late_alpha >= 0, "Failed to extract late alpha frame via extractplanes=a"
    assert early_alpha < late_alpha, (
        f"Alpha not increasing over time: early={early_alpha:.1f}, late={late_alpha:.1f}; "
        "opacity animation does not appear to be changing"
    )


@_FFMPEG_SKIP
def test_geq_composition_survival(tmp_path: Path) -> None:
    """Animated geq opacity survives overlay composition (BL-502-AC-3).

    Overlays a geq-animated foreground over a static background using
    FFmpeg's overlay filter. Verifies the overlay filter chain runs without
    error and produces a non-empty output, proving alpha compositing with
    geq's per-frame alpha doesn't corrupt the overlay ordering.
    """
    filter_str = _build_animated_opacity_filter()
    output = tmp_path / "composed.mp4"

    # Two inputs: background (green) and foreground (red, animated opacity)
    filter_complex = f"[0:v]format=rgba[bg];[1:v]{filter_str}[fg];[bg][fg]overlay=0:0[out]"
    result = _run_ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=green:size=64x64:duration=3:rate=24",
        "-f",
        "lavfi",
        "-i",
        "color=red:size=64x64:duration=3:rate=24",
        "-filter_complex",
        filter_complex,
        "-map",
        "[out]",
        "-frames:v",
        "72",
        "-y",
        str(output),
    )
    assert result.returncode == 0, (
        f"FFmpeg overlay with geq animated opacity failed:\n{result.stderr}"
    )
    assert output.exists() and output.stat().st_size > 0, "Composed output is empty"
