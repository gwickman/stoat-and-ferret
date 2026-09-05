# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Acceptance test: uc_media_preview_oracle — preview media oracle SSIM comparison (BL-839).

Verifies:
- FR-002-AC-1: SSIM >= 0.90 agreement between preview and render at t=0.5 and t=clip1_dur+0.5.
- FR-003-AC-1: Preview shows clip-2 content at clip-2 range time (not clip-1 content).

Uses two visually distinct colored clips (red/blue) to make content-correctness assertions
reliable. The reference render is produced by a direct FFmpeg concat so that preview/render
comparison is independent of render-path divergences (those are tested by BL-838).

All tests gated on STOAT_TEST_FFMPEG=1.
Run with: STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/test_uc_media_preview_oracle.py -v
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import pytest

from stoat_ferret.ffmpeg.async_executor import RealAsyncFFmpegExecutor
from stoat_ferret.preview.hls_generator import HLSGenerator
from stoat_ferret_core import CompositionClip, build_composition_graph
from tests.preview_oracle import (
    _compute_ssim_hls_vs_file,
    compare_preview_render,
    materialize_preview_session,
)

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

pytestmark = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)

_CLIP1_DUR = 2.0  # seconds
_CLIP2_DUR = 2.0  # seconds
_W = 320
_H = 240
_FPS = 30


def _make_colored_clip(path: Path, color: str, duration: float = 2.0) -> Path:
    """Generate a solid-color video clip using lavfi color source."""
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s={_W}x{_H}:r={_FPS}:d={duration}",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        capture_output=True,
        timeout=60,
    )
    if r.returncode != 0:
        raise RuntimeError(
            f"ffmpeg fixture generation failed ({color}): {r.stderr.decode()[-400:]}"
        )
    return path


def _make_reference_render(clip1: Path, clip2: Path, out: Path) -> None:
    """Produce a reference render by direct FFmpeg concat (clip1 → clip2, hard cut)."""
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(clip1),
            "-i",
            str(clip2),
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0[outv]",
            "-map",
            "[outv]",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        capture_output=True,
        timeout=60,
    )
    if r.returncode != 0:
        raise RuntimeError(f"Reference render failed: {r.stderr.decode()[-400:]}")


async def test_preview_render_ssim_agreement(tmp_path: Path) -> None:
    """Two-clip preview and reference render agree (SSIM >= 0.90) at t=0.5 and t=2.5.

    Also asserts that clip-2 content (blue) is visible at the clip-2 range time,
    not clip-1 content (red) — distinguishing media-level correctness from routing-level.

    Verifies BL-839 AC-1, AC-2, AC-3, AC-4.
    """
    clip1_path = _make_colored_clip(tmp_path / "clip1.mp4", "red", _CLIP1_DUR)
    clip2_path = _make_colored_clip(tmp_path / "clip2.mp4", "blue", _CLIP2_DUR)
    render_path = tmp_path / "render.mp4"
    _make_reference_render(clip1_path, clip2_path, render_path)
    assert render_path.exists(), "Reference render must be produced"

    # Build composition graph (concat, no transitions)
    clips = [
        CompositionClip(0, 0.0, _CLIP1_DUR, 0, 0),
        CompositionClip(1, _CLIP1_DUR, _CLIP1_DUR + _CLIP2_DUR, 0, 0),
    ]
    graph = build_composition_graph(clips, [], None, None, _W, _H)

    # Generate HLS preview
    session_id = "oracle-ssim-001"
    hls_base = tmp_path / "hls"
    executor = RealAsyncFFmpegExecutor()
    generator = HLSGenerator(async_executor=executor, output_base_dir=str(hls_base))
    output_dir = await generator.generate(
        session_id=session_id,
        input_paths=[str(clip1_path), str(clip2_path)],
        filter_graph=graph,
    )

    assert (output_dir / "manifest.m3u8").exists(), "HLS manifest must exist"
    assert any(f.suffix == ".ts" for f in output_dir.iterdir()), ">=1 .ts segment must exist"

    # Materialize preview session (oracle primitive FR-001-AC-1)
    session = await materialize_preview_session(session_id, output_dir)

    # FR-002-AC-1: SSIM >= 0.90 at t=0.5 (clip1 range) and t=2.5 (clip2 range)
    clip2_stable_t = _CLIP1_DUR + 0.5
    await compare_preview_render(session, render_path, [0.5, clip2_stable_t], 0.90)

    # FR-003-AC-1: At clip-2 range time, preview must show clip-2 content (blue),
    # not clip-1 content (red). SSIM between preview@2.5 and clip1_source@0.5 must be LOW.
    manifest_path = session["manifest_path"]
    wrong_content_ssim = await asyncio.to_thread(
        _compute_ssim_hls_vs_file,
        manifest_path,
        clip2_stable_t,  # preview at clip-2 range time
        clip1_path,  # reference: clip-1 source content (red)
        0.5,  # stable time within clip-1 content
    )
    assert wrong_content_ssim < 0.5, (
        f"Preview at clip-2 range (t={clip2_stable_t}s) appears to show clip-1 content "
        f"(SSIM vs clip-1 source = {wrong_content_ssim:.4f}, expected < 0.5). "
        "This indicates clip-1 content is playing at clip-2 time — a content-correctness failure."
    )
