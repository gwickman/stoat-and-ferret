# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""FFmpeg integration tests for OpacityBuilder geq animated opacity (BL-502, BL-681).

Validates that:
  AC-1: geq with uppercase T parses and runs on FFmpeg 8.0.1
  AC-2: alpha channel spans measurable range at t=0.5/2.5/4.5 s (pixel-diff proof)
  AC-3: composition survival — center-pixel luma shifts measurably across animation
  AC-4: render-graph ramp — RenderGraphTranslator animated_alpha produces alpha gradient

All tests are gated on STOAT_TEST_FFMPEG=1.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from stoat_ferret_core import (
    Automation,
    ClipWithEffects,
    Keyframe,
    OpacityBuilder,
    RenderEffect,
    RenderGraphTranslator,
)

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
    """Build geq filter string for 0→1 opacity fade over 5 s."""
    auto = Automation(
        default=0.0,
        keyframes=[
            Keyframe(t=0.0, value=0.0, curve="Linear"),
            Keyframe(t=5.0, value=1.0, curve="Linear"),
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
        "color=black:size=64x64:duration=5:rate=24",
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
    """Alpha plane spans expected range at early/mid/late frames (BL-681-AC-2).

    5-second 0→1 fade at 24 fps.  Measured values with FFmpeg 8.0.1:
      frame 12  (t≈0.50 s, opacity≈0.10): mean_alpha ≈  25
      frame 60  (t≈2.50 s, opacity≈0.50): mean_alpha ≈ 127
      frame 108 (t≈4.50 s, opacity≈0.90): mean_alpha ≈ 229
    Tolerance ±15.
    """
    filter_str = _build_animated_opacity_filter()

    def _mean_alpha(frame_n: int) -> float:
        res = subprocess.run(
            [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                "color=red:size=64x64:rate=24:duration=5",
                "-vf",
                f"{filter_str},select=eq(n\\,{frame_n}),setpts=PTS-STARTPTS,format=rgba,extractplanes=a",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "gray",
                "-frames:v",
                "1",
                "pipe:1",
            ],
            capture_output=True,
            check=True,
        )
        px = res.stdout
        if len(px) != 64 * 64:
            return -1.0
        return sum(px) / (64 * 64)

    early_alpha = _mean_alpha(12)  # t≈0.50 s → opacity=0.10 → mean_alpha≈25
    mid_alpha = _mean_alpha(60)  # t≈2.50 s → opacity=0.50 → mean_alpha≈127
    late_alpha = _mean_alpha(108)  # t≈4.50 s → opacity=0.90 → mean_alpha≈229

    assert 10 <= early_alpha <= 40, f"expected ≈25 ±15, got {early_alpha:.1f}"
    assert mid_alpha > early_alpha, f"mid ({mid_alpha:.1f}) must exceed early ({early_alpha:.1f})"
    assert 214 <= late_alpha <= 244, f"expected ≈229 ±15, got {late_alpha:.1f}"


@_FFMPEG_SKIP
def test_geq_composition_survival(tmp_path: Path) -> None:
    """Composed output shows measurable center-pixel luma shift across animation (BL-681-AC-3).

    White background + black foreground with 0→1 animated alpha over 5 s.
    At t=0.5 s (alpha≈10 %) the blend is ≈213 (mostly white).
    At t=4.5 s (alpha≈90 %) the blend is ≈38 (mostly black).
    Expected luma difference > 50.
    """
    filter_str = _build_animated_opacity_filter()
    output = tmp_path / "composed.mp4"

    filter_complex = f"[0:v]format=rgba[bg];[1:v]{filter_str}[fg];[bg][fg]overlay=0:0[out]"
    result = _run_ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=white:size=64x64:duration=5:rate=24",
        "-f",
        "lavfi",
        "-i",
        "color=black:size=64x64:duration=5:rate=24",
        "-filter_complex",
        filter_complex,
        "-map",
        "[out]",
        "-frames:v",
        "120",
        "-y",
        str(output),
    )
    assert result.returncode == 0, (
        f"FFmpeg overlay with geq animated opacity failed:\n{result.stderr}"
    )
    assert output.exists() and output.stat().st_size > 0, "Composed output is empty"

    def _center_luma(t_secs: float) -> int:
        res = subprocess.run(
            [
                "ffmpeg",
                "-ss",
                str(t_secs),
                "-i",
                str(output),
                "-frames:v",
                "1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "gray",
                "pipe:1",
            ],
            capture_output=True,
        )
        px = res.stdout
        center = (64 // 2) * 64 + (64 // 2)
        return px[center] if len(px) > center else -1

    luma_early = _center_luma(0.5)  # alpha≈10 % → blend≈213 (mostly white)
    luma_late = _center_luma(4.5)  # alpha≈90 % → blend≈38  (mostly black)
    assert luma_early >= 0 and luma_late >= 0, "Center-pixel extraction failed"
    assert abs(luma_early - luma_late) > 50, (
        f"Expected |{luma_early} - {luma_late}| > 50 but got {abs(luma_early - luma_late)}"
    )


@_FFMPEG_SKIP
def test_geq_render_graph_ramp(tmp_path: Path) -> None:
    """RenderGraphTranslator animated_alpha(0, 1) produces measurable alpha ramp (BL-681-AC-4).

    2-clip 3-second project, clip 0 has animated_alpha(0.0, 1.0).
    xfade begins at t=2.0 s (offset = duration - 1.0).
    Measured values with FFmpeg 8.0.1 (format=rgba output):
      frame 3  (t≈0.10 s): opacity≈0.033 → mean_alpha≈  8
      frame 54 (t≈1.80 s): opacity≈0.600 → mean_alpha≈153
    Asserts late_alpha > early_alpha + 10.
    """
    src = tmp_path / "src.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "color=red:size=64x64:duration=3:rate=30",
            "-c:v",
            "libx264",
            "-y",
            str(src),
        ],
        capture_output=True,
        check=True,
    )

    clips = [
        ClipWithEffects(
            input_index=0,
            duration_secs=3.0,
            framerate=30.0,
            source_path=str(src),
            effects=[RenderEffect.animated_alpha(0.0, 1.0)],
        ),
        ClipWithEffects(
            input_index=1,
            duration_secs=3.0,
            framerate=30.0,
            source_path=str(src),
            effects=[RenderEffect.none()],
        ),
    ]
    filter_complex, input_paths = RenderGraphTranslator().translate(clips)
    filter_complex_rgba = filter_complex.replace("format=yuv420p[final]", "format=rgba[final]")

    output_rgba = tmp_path / "ramp.bin"
    cmd = ["ffmpeg"]
    for p in input_paths:
        cmd += ["-i", p]
    cmd += [
        "-filter_complex",
        filter_complex_rgba,
        "-map",
        "[final]",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgba",
        "-y",
        str(output_rgba),
    ]
    result = subprocess.run(cmd, capture_output=True)
    assert result.returncode == 0, result.stderr.decode(errors="replace")[-500:]

    W, H = 64, 64
    FRAME_SIZE = W * H * 4

    def _mean_alpha_at_frame(frame_n: int) -> float:
        with open(output_rgba, "rb") as f:
            f.seek(frame_n * FRAME_SIZE)
            px = f.read(FRAME_SIZE)
        if len(px) != FRAME_SIZE:
            return -1.0
        return sum(px[i * 4 + 3] for i in range(W * H)) / (W * H)

    early_alpha = _mean_alpha_at_frame(3)  # t≈0.10 s → expected ≈  8
    late_alpha = _mean_alpha_at_frame(54)  # t≈1.80 s → expected ≈153

    assert early_alpha >= 0 and late_alpha >= 0, "RGBA frame extraction failed"
    assert late_alpha > early_alpha + 10, (
        f"Expected late ({late_alpha:.1f}) > early ({early_alpha:.1f}) + 10"
    )
