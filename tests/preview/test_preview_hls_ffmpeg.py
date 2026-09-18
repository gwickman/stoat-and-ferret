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


def test_hls_args_generator_clip_prefixes_lavfi(tmp_path: Path) -> None:
    """build_hls_args with clip_types=['generator'] emits -f lavfi before -i (FR-007-AC-1)."""
    from stoat_ferret.preview.hls_generator import build_hls_args

    lavfi = "color=c=red:s=320x240:r=25:d=3"
    args = build_hls_args(
        input_paths=[lavfi],
        output_dir=tmp_path,
        filter_complex=None,
        segment_duration=2.0,
        clip_types=["generator"],
    )
    i_idx = args.index("-i")
    assert args[i_idx - 2] == "-f", "expected -f flag two positions before -i"
    assert args[i_idx - 1] == "lavfi", "expected lavfi value before -i"
    assert args[i_idx + 1] == lavfi, "expected lavfi string as -i value"


def test_hls_args_image_clip_prefixes_loop(tmp_path: Path) -> None:
    """build_hls_args with clip_types=['image'] emits -loop 1 before -i (FR-007-AC-1)."""
    from stoat_ferret.preview.hls_generator import build_hls_args

    img_path = "/assets/still.png"
    args = build_hls_args(
        input_paths=[img_path],
        output_dir=tmp_path,
        filter_complex=None,
        segment_duration=2.0,
        clip_types=["image"],
    )
    i_idx = args.index("-i")
    assert args[i_idx - 2] == "-loop", "expected -loop flag two positions before -i"
    assert args[i_idx - 1] == "1", "expected 1 value before -i"
    assert args[i_idx + 1] == img_path, "expected image path as -i value"


def test_hls_args_none_clip_types_backward_compatible(tmp_path: Path) -> None:
    """build_hls_args with clip_types=None emits plain -i with no -f or -loop (FR-003-AC-1)."""
    from stoat_ferret.preview.hls_generator import build_hls_args

    vid_path = "/path/to/video.mp4"
    args = build_hls_args(
        input_paths=[vid_path],
        output_dir=tmp_path,
        filter_complex=None,
        segment_duration=2.0,
        clip_types=None,
    )
    assert "-loop" not in args
    assert "-i" in args
    i_idx = args.index("-i")
    assert args[i_idx + 1] == vid_path
    # -f lavfi must not appear as a clip-type prefix; -f hls may still appear as output format
    assert "lavfi" not in args


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


def test_build_hls_args_with_clip_durations(tmp_path: Path) -> None:
    """build_hls_args emits -t before -i when clip_durations provided (BL-887-AC-1)."""
    from stoat_ferret.preview.hls_generator import build_hls_args

    args = build_hls_args(
        input_paths=["/a.mp4", "/b.mp4"],
        output_dir=tmp_path,
        filter_complex=None,
        segment_duration=2.0,
        clip_durations=[10.0, 8.5],
    )
    # Find first -t / -i pair
    t_indices = [i for i, a in enumerate(args) if a == "-t"]
    assert len(t_indices) == 2, f"expected 2 -t flags, got {len(t_indices)}"
    assert args[t_indices[0]] == "-t"
    assert args[t_indices[0] + 1] == "10.0"
    assert args[t_indices[0] + 2] == "-i"
    assert args[t_indices[0] + 3] == "/a.mp4"
    assert args[t_indices[1]] == "-t"
    assert args[t_indices[1] + 1] == "8.5"
    assert args[t_indices[1] + 2] == "-i"
    assert args[t_indices[1] + 3] == "/b.mp4"


def test_build_hls_args_none_durations_unchanged(tmp_path: Path) -> None:
    """build_hls_args with clip_durations=None emits no -t flags (BL-887-AC-4 regression guard)."""
    from stoat_ferret.preview.hls_generator import build_hls_args

    args = build_hls_args(
        input_paths=["/a.mp4", "/b.mp4"],
        output_dir=tmp_path,
        filter_complex=None,
        segment_duration=2.0,
        clip_durations=None,
    )
    assert "-t" not in args, "no -t flags expected when clip_durations=None"


def test_hard_cut_no_xfade(tmp_path: Path) -> None:
    """Explicit 'cut' transition between clips emits concat, not xfade (BL-887-AC-2)."""
    from stoat_ferret_core import (
        ClipWithEffects,
        RenderEffect,
        RenderGraphTranslator,
        RenderTransition,
    )

    cwe_list = [
        ClipWithEffects(
            input_index=0,
            duration_secs=3.0,
            framerate=25.0,
            source_path="/clip1.mp4",
            effects=[RenderEffect.none()],
            outgoing_transition=RenderTransition("cut", 0.0),
        ),
        ClipWithEffects(
            input_index=1,
            duration_secs=3.0,
            framerate=25.0,
            source_path="/clip2.mp4",
            effects=[RenderEffect.none()],
            outgoing_transition=None,
        ),
    ]
    translator = RenderGraphTranslator()
    filter_complex_str, _ = translator.translate(cwe_list, 25.0)

    assert "xfade" not in filter_complex_str, (
        f"hard cut must not emit xfade: {filter_complex_str!r}"
    )
    assert "concat" in filter_complex_str, f"hard cut must emit concat: {filter_complex_str!r}"


@_requires_ffmpeg
@pytest.mark.asyncio
async def test_parity_hardcut_acceptance(tmp_path: Path) -> None:
    """Two-clip hard-cut: clip_durations trims source, no-transition seam is concat (BL-887-AC-3).

    Exercises both FR-001 (clip_durations -t bounds) and FR-002 (concat instead of xfade).
    Asserts HLS generates without FFmpeg error, video stream present, and SSIM >= 0.90
    between preview and a reference render built from the same filter_complex.
    """
    import asyncio

    from stoat_ferret.ffmpeg.async_executor import RealAsyncFFmpegExecutor
    from stoat_ferret.preview.hls_generator import build_hls_args, get_segment_duration
    from stoat_ferret_core import (
        ClipWithEffects,
        RenderEffect,
        RenderGraphTranslator,
        RenderTransition,
    )
    from tests.preview_oracle import _compute_ssim_hls_vs_file, materialize_preview_session
    from tests.render_oracle import assert_stream_inventory

    CLIP1_SOURCE_DUR = 6.0
    CLIP2_SOURCE_DUR = 5.0
    CLIP1_TIMELINE_DUR = 3.0
    CLIP2_TIMELINE_DUR = 2.0
    CLIP_FPS = 25
    OUTPUT_FPS = 25.0

    clip1_path = tmp_path / "clip1.mp4"
    clip2_path = tmp_path / "clip2.mp4"
    _make_clip(clip1_path, duration=CLIP1_SOURCE_DUR)
    _make_clip(clip2_path, duration=CLIP2_SOURCE_DUR)

    # Clip 1 has "cut" outgoing transition — no stored transition in project data.
    cwe_list = [
        ClipWithEffects(
            input_index=0,
            duration_secs=CLIP1_TIMELINE_DUR,
            framerate=float(CLIP_FPS),
            source_path=str(clip1_path),
            effects=[RenderEffect.none()],
            outgoing_transition=RenderTransition("cut", 0.0),
        ),
        ClipWithEffects(
            input_index=1,
            duration_secs=CLIP2_TIMELINE_DUR,
            framerate=float(CLIP_FPS),
            source_path=str(clip2_path),
            effects=[RenderEffect.none()],
            outgoing_transition=None,
        ),
    ]
    translator = RenderGraphTranslator()
    filter_complex_str, _ = translator.translate(cwe_list, OUTPUT_FPS)

    assert "xfade" not in filter_complex_str, "hard cut must not emit xfade in acceptance path"

    # Reference render: same filter_complex + per-input -t bounds
    render_path = tmp_path / "render.mp4"
    await asyncio.to_thread(
        subprocess.run,
        [
            "ffmpeg",
            "-t",
            str(CLIP1_TIMELINE_DUR),
            "-i",
            str(clip1_path),
            "-t",
            str(CLIP2_TIMELINE_DUR),
            "-i",
            str(clip2_path),
            "-filter_complex",
            filter_complex_str,
            "-map",
            "[final]",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-an",
            "-y",
            str(render_path),
        ],
        check=True,
        capture_output=True,
    )

    # HLS preview: same filter_complex + clip_durations
    hls_dir = tmp_path / "hls"
    hls_dir.mkdir()
    args = build_hls_args(
        input_paths=[str(clip1_path), str(clip2_path)],
        output_dir=hls_dir,
        filter_complex=filter_complex_str,
        segment_duration=get_segment_duration(),
        clip_durations=[CLIP1_TIMELINE_DUR, CLIP2_TIMELINE_DUR],
    )
    executor = RealAsyncFFmpegExecutor()
    result = await executor.run(args)
    assert result.returncode == 0, (
        f"FFmpeg preview failed: {result.stderr.decode(errors='replace')[:300]}"
    )

    manifest = hls_dir / "manifest.m3u8"
    assert manifest.exists(), "manifest.m3u8 must exist"
    assert any(f.suffix == ".ts" for f in hls_dir.iterdir()), ">=1 .ts segment required"

    await assert_stream_inventory(manifest, video=True, audio=False)

    session_id = "hardcut-acceptance-001"
    session = await materialize_preview_session(session_id, hls_dir)
    ssim = await asyncio.to_thread(
        _compute_ssim_hls_vs_file,
        session["manifest_path"],
        0.5,
        render_path,
        0.5,
    )
    assert ssim >= 0.90, f"SSIM at t=0.5s = {ssim:.4f} < 0.90 (preview/render parity failure)"


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
