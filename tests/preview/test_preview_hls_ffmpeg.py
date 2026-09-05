# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Preview HLS FFmpeg integration tests.

deferred_post_merge: These tests require STOAT_TEST_FFMPEG=1 and a real FFmpeg binary.
CI skip is expected on empty-commit discharge runs (paths-filter skips when no code changes).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from stoat_ferret.ffmpeg.async_executor import RealAsyncFFmpegExecutor
from stoat_ferret.preview.hls_generator import HLSGenerator
from stoat_ferret_core import (
    CompositionClip,
    TransitionSpec,
    TransitionType,
    build_composition_graph,
)

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG")

_requires_ffmpeg = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires FFmpeg (STOAT_TEST_FFMPEG=1)",
)


def _make_clip(path: Path, duration: float = 3.0) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s=320x240:r=25:d={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-t",
            str(duration),
            "-y",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


@_requires_ffmpeg
async def test_hls_single_clip_map(tmp_path: Path) -> None:
    """Single-clip scale graph ([outv] only): exit 0, manifest.m3u8, >=1 .ts segment."""
    src = tmp_path / "single.mp4"
    _make_clip(src)

    clips = [CompositionClip(0, 0.0, 3.0, 0, 0)]
    graph = build_composition_graph(clips, [], None, None, 320, 240)

    executor = RealAsyncFFmpegExecutor()
    generator = HLSGenerator(async_executor=executor, output_base_dir=str(tmp_path / "hls"))
    output_dir = await generator.generate(
        session_id="test-single",
        input_paths=[str(src)],
        filter_graph=graph,
    )

    assert (output_dir / "manifest.m3u8").exists()
    assert any(f.suffix == ".ts" for f in output_dir.iterdir())


@_requires_ffmpeg
async def test_hls_multi_clip_concat_map(tmp_path: Path) -> None:
    """Multi-clip concat graph ([outv][outa]): exit 0, manifest.m3u8, >=1 .ts segment."""
    src1 = tmp_path / "clip1.mp4"
    src2 = tmp_path / "clip2.mp4"
    _make_clip(src1, duration=2.0)
    _make_clip(src2, duration=2.0)

    clips = [
        CompositionClip(0, 0.0, 2.0, 0, 0),
        CompositionClip(1, 2.0, 4.0, 0, 0),
    ]
    graph = build_composition_graph(clips, [], None, None, 320, 240)

    executor = RealAsyncFFmpegExecutor()
    generator = HLSGenerator(async_executor=executor, output_base_dir=str(tmp_path / "hls"))
    output_dir = await generator.generate(
        session_id="test-concat",
        input_paths=[str(src1), str(src2)],
        filter_graph=graph,
    )

    assert (output_dir / "manifest.m3u8").exists()
    assert any(f.suffix == ".ts" for f in output_dir.iterdir())


@_requires_ffmpeg
async def test_hls_multi_clip_xfade_map(tmp_path: Path) -> None:
    """Multi-clip xfade+acrossfade graph ([outv][outa]): exit 0, manifest.m3u8, >=1 .ts segment."""
    src1 = tmp_path / "xfade1.mp4"
    src2 = tmp_path / "xfade2.mp4"
    _make_clip(src1, duration=4.0)
    _make_clip(src2, duration=4.0)

    # 1-second overlap: clip2 starts 1s before clip1 ends
    clips = [
        CompositionClip(0, 0.0, 3.0, 0, 0),
        CompositionClip(1, 2.0, 5.0, 0, 0),
    ]
    transitions = [TransitionSpec(TransitionType.Fade, 1.0, 0.0)]
    graph = build_composition_graph(clips, transitions, None, None, 320, 240)

    executor = RealAsyncFFmpegExecutor()
    generator = HLSGenerator(async_executor=executor, output_base_dir=str(tmp_path / "hls"))
    output_dir = await generator.generate(
        session_id="test-xfade",
        input_paths=[str(src1), str(src2)],
        filter_graph=graph,
    )

    assert (output_dir / "manifest.m3u8").exists()
    assert any(f.suffix == ".ts" for f in output_dir.iterdir())


@_requires_ffmpeg
async def test_hls_partial_transition_xfade(tmp_path: Path) -> None:
    """3-clip timeline with 1 transition (partial): exit 0, manifest.m3u8, >=1 .ts (BL-843-AC-2).

    Red-then-green: without the fix, build_xfade_graph emits [xv0]/[xa0] instead of
    [outv]/[outa], causing FFmpeg to crash with an unconnected-filter error.
    """
    src1 = tmp_path / "partial1.mp4"
    src2 = tmp_path / "partial2.mp4"
    src3 = tmp_path / "partial3.mp4"
    _make_clip(src1, duration=3.0)
    _make_clip(src2, duration=3.0)
    _make_clip(src3, duration=3.0)

    # 3 clips, only 1 transition (between clip1 and clip2; clip3 has no transition)
    clips = [
        CompositionClip(0, 0.0, 2.0, 0, 0),
        CompositionClip(1, 1.5, 3.5, 0, 0),
        CompositionClip(2, 3.5, 6.5, 0, 0),
    ]
    transitions = [TransitionSpec(TransitionType.Fade, 0.5, 0.0)]
    graph = build_composition_graph(clips, transitions, None, None, 320, 240)

    executor = RealAsyncFFmpegExecutor()
    generator = HLSGenerator(async_executor=executor, output_base_dir=str(tmp_path / "hls"))
    output_dir = await generator.generate(
        session_id="test-partial-xfade",
        input_paths=[str(src1), str(src2), str(src3)],
        filter_graph=graph,
    )

    assert (output_dir / "manifest.m3u8").exists()
    assert any(f.suffix == ".ts" for f in output_dir.iterdir())


@_requires_ffmpeg
async def test_draft_quality_simplify_hls(tmp_path: Path) -> None:
    """Draft-quality simplify_filter_graph preserves labels so FFmpeg gets valid -map (BL-845-AC-2).

    Red-then-green: before the fix, simplify_filter_chain drops input/output labels at Draft
    quality, so filter_complex lacks [outv]/[outa] and build_hls_args emits no -map, causing
    FFmpeg to fail with an unconnected-filter error.
    """
    from stoat_ferret.preview.hls_generator import build_hls_args, get_segment_duration
    from stoat_ferret_core import PreviewQuality, simplify_filter_graph

    src1 = tmp_path / "draft1.mp4"
    src2 = tmp_path / "draft2.mp4"
    _make_clip(src1, duration=2.0)
    _make_clip(src2, duration=2.0)

    clips = [
        CompositionClip(0, 0.0, 2.0, 0, 0),
        CompositionClip(1, 2.0, 4.0, 0, 0),
    ]
    graph = build_composition_graph(clips, [], None, None, 320, 240)

    # Explicitly apply Draft simplification — bypasses cost-based auto-selection so the
    # label-preservation fix is exercised regardless of the graph's computed cost.
    simplified = simplify_filter_graph(graph, PreviewQuality.Draft)
    filter_complex = str(simplified)

    output_dir = tmp_path / "hls_draft"
    output_dir.mkdir()
    args = build_hls_args(
        input_paths=[str(src1), str(src2)],
        output_dir=output_dir,
        filter_complex=filter_complex,
        segment_duration=get_segment_duration(),
    )

    executor = RealAsyncFFmpegExecutor()
    result = await executor.run(args)
    assert result.returncode == 0, f"FFmpeg failed: {result.stderr.decode(errors='replace')[:300]}"

    assert (output_dir / "manifest.m3u8").exists()
    assert any(f.suffix == ".ts" for f in output_dir.iterdir())


@_requires_ffmpeg
async def test_hls_wipeleft_transition(tmp_path: Path) -> None:
    """wipeleft xfade transition generates valid HLS without FFmpeg error (BL-846-AC-5)."""
    src1 = tmp_path / "wipeleft1.mp4"
    src2 = tmp_path / "wipeleft2.mp4"
    _make_clip(src1, duration=4.0)
    _make_clip(src2, duration=4.0)

    clips = [
        CompositionClip(0, 0.0, 3.0, 0, 0),
        CompositionClip(1, 2.5, 5.0, 0, 0),
    ]
    transitions = [TransitionSpec(TransitionType.Wipeleft, 0.5, 0.0)]
    graph = build_composition_graph(clips, transitions, None, None, 320, 240)

    executor = RealAsyncFFmpegExecutor()
    generator = HLSGenerator(async_executor=executor, output_base_dir=str(tmp_path / "hls"))
    output_dir = await generator.generate(
        session_id="test-wipeleft",
        input_paths=[str(src1), str(src2)],
        filter_graph=graph,
    )

    assert (output_dir / "manifest.m3u8").exists()
    assert any(f.suffix == ".ts" for f in output_dir.iterdir())
