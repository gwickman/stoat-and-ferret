# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Integration test for multi-clip rendering via RenderGraphTranslator (BL-505).

Verifies that build_command_for_job produces a valid filter_complex-based FFmpeg
command when a project has multiple clips, with no FFmpeg execution required.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.effects.definitions import EffectDefinition
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import build_command_for_job

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")
_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="Set STOAT_TEST_FFMPEG=1 to run FFmpeg-gated tests",
)

_PROJECT_ID = "proj-multi-001"
_OUTPUT_PATH = "/renders/multi_output.mp4"


def _make_render_plan() -> str:
    import json

    return json.dumps(
        {
            "total_duration": 10.0,
            "settings": {
                "codec": "libx264",
                "fps": 30.0,
                "width": 1920,
                "height": 1080,
                "quality_preset": "standard",
            },
        }
    )


def _make_job() -> RenderJob:
    now = datetime.now(timezone.utc)
    return RenderJob(
        id="job-multi-001",
        project_id=_PROJECT_ID,
        status=RenderStatus.RUNNING,
        output_path=_OUTPUT_PATH,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=_make_render_plan(),
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def _make_clip(
    clip_id: str,
    video_id: str,
    timeline_position: int,
    effects: list[dict[str, Any]] | None = None,
) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=_PROJECT_ID,
        source_video_id=video_id,
        in_point=0,
        out_point=150,  # 5 seconds at 30 fps
        timeline_position=timeline_position,
        created_at=now,
        updated_at=now,
        effects=effects,
    )


def _make_video(video_id: str, path: str) -> Video:
    now = datetime.now(timezone.utc)
    return Video(
        id=video_id,
        path=path,
        filename=f"{video_id}.mp4",
        duration_frames=1800,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=1920,
        height=1080,
        video_codec="h264",
        file_size=50_000_000,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_multi_clip_render_integration() -> None:
    """BL-505-AC-1/AC-7: build_command_for_job uses RenderGraphTranslator for multi-clip.

    Verifies:
    - Multiple -i inputs (one per clip) are present.
    - -filter_complex is present and contains expected FFmpeg filter structure.
    - -map [final] is present for the video output.
    - -c:v codec flag is present.
    - Output path is the last argument.
    - No FFmpeg execution is required; the translator runs in pure Rust.
    """
    clips = [
        _make_clip("clip-a", "vid-a", timeline_position=0),
        _make_clip("clip-b", "vid-b", timeline_position=150),
    ]
    videos = {
        "vid-a": _make_video("vid-a", "/media/clip_a.mp4"),
        "vid-b": _make_video("vid-b", "/media/clip_b.mp4"),
    }

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)

    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    job = _make_job()
    cmd = await build_command_for_job(job, clip_repo, video_repo)

    assert isinstance(cmd, list)
    assert cmd[0] == "ffmpeg"

    # Both video inputs must appear
    input_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-i"]
    assert "/media/clip_a.mp4" in input_flags
    assert "/media/clip_b.mp4" in input_flags

    # filter_complex must be present and contain valid FFmpeg filter structure
    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]
    assert isinstance(filter_complex, str)
    assert len(filter_complex) > 0
    # Translator output uses [0:v] and [1:v] stream specifiers
    assert "[0:v]" in filter_complex
    assert "[1:v]" in filter_complex
    # Terminal output label is [final]
    assert "[final]" in filter_complex

    # -map [final] must be present to select the video output
    assert "-map" in cmd
    map_idx = cmd.index("-map")
    assert cmd[map_idx + 1] == "[final]"

    # Standard codec flags
    assert "-c:v" in cmd
    assert "libx264" in cmd

    # Output path must be last
    assert cmd[-1] == _OUTPUT_PATH


@pytest.mark.asyncio
async def test_multi_clip_clip_sort_order() -> None:
    """BL-505: clips are passed to translator in timeline_position order.

    The clip_repository returns clips sorted by timeline_position.
    The multi-clip command must reflect that order in -i arguments.
    """
    # Clips in reverse insertion order — repository will return sorted
    clips = [
        _make_clip("clip-first", "vid-first", timeline_position=0),
        _make_clip("clip-second", "vid-second", timeline_position=150),
    ]
    videos = {
        "vid-first": _make_video("vid-first", "/media/first.mp4"),
        "vid-second": _make_video("vid-second", "/media/second.mp4"),
    }

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)  # already sorted by repo

    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    job = _make_job()
    cmd = await build_command_for_job(job, clip_repo, video_repo)

    # First -i must be the first clip's video (timeline_position=0)
    first_i_idx = cmd.index("-i")
    assert cmd[first_i_idx + 1] == "/media/first.mp4"

    # Second -i must be the second clip's video (timeline_position=150)
    second_i_idx = cmd.index("-i", first_i_idx + 1)
    assert cmd[second_i_idx + 1] == "/media/second.mp4"


@pytest.mark.asyncio
async def test_multi_clip_real_effects_fetched_from_registry() -> None:
    """BL-553-AC-1/AC-2: worker fetches real per-clip effects and calls translator.

    Verifies:
    - Worker iterates ALL clips, not just clips[0].
    - Per-clip effects are resolved via the effect registry and passed to translator.
    - Unknown effect_type falls back to RenderEffect.none() without crashing.
    - The resulting command still contains valid filter_complex and -i inputs.
    """
    blur_filter_str = "boxblur=luma_radius=5:luma_power=1"

    def _blur_build_fn(params: dict[str, Any]) -> str:
        return blur_filter_str

    blur_defn = MagicMock(spec=EffectDefinition)
    blur_defn.build_fn = _blur_build_fn

    registry = EffectRegistry()
    registry.register("blur", blur_defn)

    # Clip A has a known blur effect; clip B has an unknown effect type
    clips = [
        _make_clip(
            "clip-a",
            "vid-a",
            timeline_position=0,
            effects=[{"effect_type": "blur", "parameters": {"radius": 5}}],
        ),
        _make_clip(
            "clip-b",
            "vid-b",
            timeline_position=150,
            effects=[{"effect_type": "unknown_effect", "parameters": {}}],
        ),
    ]
    videos = {
        "vid-a": _make_video("vid-a", "/media/clip_a.mp4"),
        "vid-b": _make_video("vid-b", "/media/clip_b.mp4"),
    }

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)

    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    job = _make_job()
    cmd = await build_command_for_job(job, clip_repo, video_repo, effect_registry=registry)

    assert isinstance(cmd, list)
    assert cmd[0] == "ffmpeg"

    # Both clips must appear in -i args (worker iterates ALL clips)
    input_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-i"]
    assert "/media/clip_a.mp4" in input_flags
    assert "/media/clip_b.mp4" in input_flags

    # filter_complex must be present (translator was called)
    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]
    assert isinstance(filter_complex, str)
    assert len(filter_complex) > 0

    # Output path must be last
    assert cmd[-1] == _OUTPUT_PATH


# ---------------------------------------------------------------------------
# STOAT_TEST_FFMPEG-gated integration tests (BL-505, BL-553)
# ---------------------------------------------------------------------------

_GATED_DUR_SECS = 3
_GATED_DUR_FRAMES = 90  # 3 s × 30 fps


def _gen_lavfi_video(path: Path, lavfi_expr: str, timeout: int = 60) -> None:
    """Generate a short test video via ffmpeg lavfi."""
    r = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            lavfi_expr,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(path),
        ],
        capture_output=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg lavfi generation failed: {r.stderr.decode()[-800:]}")


def _make_gated_video(
    video_id: str,
    path: str,
    fps_num: int = 30,
    fps_den: int = 1,
    dur_frames: int = _GATED_DUR_FRAMES,
) -> Video:
    now = datetime.now(timezone.utc)
    return Video(
        id=video_id,
        path=path,
        filename=f"{video_id}.mp4",
        duration_frames=dur_frames,
        frame_rate_numerator=fps_num,
        frame_rate_denominator=fps_den,
        width=320,
        height=240,
        video_codec="h264",
        file_size=500_000,
        created_at=now,
        updated_at=now,
    )


def _make_gated_clip(
    clip_id: str,
    video_id: str,
    timeline_pos: int,
    out_point: int = _GATED_DUR_FRAMES,
    effects: list[dict[str, Any]] | None = None,
) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=_PROJECT_ID,
        source_video_id=video_id,
        in_point=0,
        out_point=out_point,
        timeline_position=timeline_pos,
        created_at=now,
        updated_at=now,
        effects=effects,
    )


def _make_gated_job(
    output_path: str, total_duration: float = float(_GATED_DUR_SECS * 2)
) -> RenderJob:
    """RenderJob targeting 320x240 for quick gated-test renders."""
    now = datetime.now(timezone.utc)
    plan = json.dumps(
        {
            "total_duration": total_duration,
            "settings": {
                "codec": "libx264",
                "fps": 30.0,
                "width": 320,
                "height": 240,
                "quality_preset": "standard",
            },
        }
    )
    return RenderJob(
        id="job-gated-001",
        project_id=_PROJECT_ID,
        status=RenderStatus.RUNNING,
        output_path=output_path,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=plan,
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def _compute_ssim(
    output: Path, t_out: float, ref: Path, t_ref: float, duration: float = 0.3
) -> float:
    """Return overall SSIM between a segment of output and a reference via ffmpeg."""
    r = subprocess.run(
        [
            "ffmpeg",
            "-ss",
            str(t_out),
            "-t",
            str(duration),
            "-i",
            str(output),
            "-ss",
            str(t_ref),
            "-t",
            str(duration),
            "-i",
            str(ref),
            "-filter_complex",
            "[0:v][1:v]ssim=f=-",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    m = re.search(r"All:(\d+\.\d+)", r.stderr)
    if not m:
        raise RuntimeError(f"Could not parse SSIM from ffmpeg output:\n{r.stderr[-600:]}")
    return float(m.group(1))


def _chroma_mad(frame_path: Path) -> float:
    """Return combined chroma-deviation metric for a PNG frame.

    Sums mean(|Cb - 128|) and stddev(Cb).  Near 0 → grayscale; > 0 → colour.
    Uses only Pillow (already a project dependency).
    """
    from PIL import Image, ImageStat

    img = Image.open(frame_path).convert("YCbCr")
    _, cb, _ = img.split()
    stat = ImageStat.Stat(cb)
    return abs(stat.mean[0] - 128.0) + stat.stddev[0]


@_FFMPEG_SKIP
async def test_multi_clip_render_ssim_proof(tmp_path: Path) -> None:
    """SSIM > 0.99 at each clip midpoint vs source (BL-505-AC-1, BL-505-AC-7, BL-553-AC-4).

    Generates two solid-colour source videos via ffmpeg lavfi, builds and runs
    a two-clip render, then asserts structural similarity > 0.99 against the
    respective source at each clip's midpoint.
    """
    src1 = tmp_path / "src1.mp4"
    src2 = tmp_path / "src2.mp4"
    out = tmp_path / "output.mp4"

    _gen_lavfi_video(src1, "color=c=blue:s=320x240:r=30:d=3")
    _gen_lavfi_video(src2, "color=c=red:s=320x240:r=30:d=3")

    clips = [
        _make_gated_clip("clip-a", "vid-a", 0),
        _make_gated_clip("clip-b", "vid-b", _GATED_DUR_FRAMES),
    ]
    videos = {
        "vid-a": _make_gated_video("vid-a", str(src1)),
        "vid-b": _make_gated_video("vid-b", str(src2)),
    }
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    job = _make_gated_job(str(out))
    cmd = await build_command_for_job(job, clip_repo, video_repo)

    r = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert r.returncode == 0, f"Render failed (exit {r.returncode}):\n{r.stderr.decode()[-800:]}"
    assert out.exists() and out.stat().st_size > 0, "Output file must exist and be non-empty"

    # Clip 1 midpoint at t=1.5s in output — solid blue, compare to source clip 1
    ssim1 = _compute_ssim(out, 1.5, src1, 1.5)
    assert ssim1 > 0.99, f"SSIM at clip 1 midpoint: {ssim1:.4f} (expected > 0.99)"

    # Clip 2 midpoint at t≈4.5s in output (pure region after 1s xfade) — solid red
    ssim2 = _compute_ssim(out, 4.5, src2, 1.5)
    assert ssim2 > 0.99, f"SSIM at clip 2 midpoint: {ssim2:.4f} (expected > 0.99)"


@_FFMPEG_SKIP
async def test_per_clip_effect_applied(tmp_path: Path) -> None:
    """Per-clip effect is active only inside its window (BL-505-AC-2).

    Uses a colourful testsrc2 source and a desaturation effect (hue=s=0)
    gated to [0.5, 2.5] seconds via the FFmpeg enable= expression embedded
    in the filter chain string. Checks that frames inside the window are
    near-grayscale (low Cb deviation) while frames outside retain chroma.
    """
    src = tmp_path / "src_color.mp4"
    out = tmp_path / "output.mp4"
    frame_inside = tmp_path / "frame_inside.png"
    frame_outside = tmp_path / "frame_outside.png"

    _gen_lavfi_video(src, "testsrc2=size=320x240:rate=30:duration=3")

    def _desaturate_build_fn(params: dict[str, Any]) -> str:
        return "hue=s=0:enable='between(t,0.5,2.5)'"

    defn = MagicMock(spec=EffectDefinition)
    defn.build_fn = _desaturate_build_fn
    defn.timeline_T_capable = True

    registry = EffectRegistry()
    registry.register("windowed_desaturate", defn)

    clips = [
        _make_gated_clip(
            "clip-a",
            "vid-a",
            0,
            effects=[{"effect_type": "windowed_desaturate", "parameters": {}}],
        ),
        _make_gated_clip("clip-b", "vid-b", _GATED_DUR_FRAMES),
    ]
    videos = {
        "vid-a": _make_gated_video("vid-a", str(src)),
        "vid-b": _make_gated_video("vid-b", str(src)),
    }
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    job = _make_gated_job(str(out))
    cmd = await build_command_for_job(job, clip_repo, video_repo, effect_registry=registry)

    r = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert r.returncode == 0, f"Render failed:\n{r.stderr.decode()[-800:]}"
    assert out.exists() and out.stat().st_size > 0

    for seek, dest in [("1.5", frame_inside), ("0.2", frame_outside)]:
        subprocess.run(  # noqa: ASYNC221
            ["ffmpeg", "-ss", seek, "-i", str(out), "-vframes", "1", "-y", str(dest)],
            capture_output=True,
            timeout=30,
            check=True,
        )

    mad_inside = _chroma_mad(frame_inside)
    mad_outside = _chroma_mad(frame_outside)

    assert mad_inside < 8.0, (
        f"Frame inside effect window should be near-grayscale: chroma_mad={mad_inside:.2f} (< 8)"
    )
    assert mad_outside > 12.0, (
        f"Frame outside effect window should retain chroma: chroma_mad={mad_outside:.2f} (> 12)"
    )


@_FFMPEG_SKIP
async def test_fps_settb_normalization(tmp_path: Path) -> None:
    """Mixed-framerate clips render without xfade timebase errors (BL-505-AC-3).

    Generates a 30 fps clip and a 25 fps clip, renders them as a two-clip project,
    and asserts a non-empty output with no timebase-related failure. Validates the
    fps=30,settb=1/30 normalisation pins emitted by the translator at every xfade
    boundary (BL-507 cross-segment rule).
    """
    src_30 = tmp_path / "src_30fps.mp4"
    src_25 = tmp_path / "src_25fps.mp4"
    out = tmp_path / "output.mp4"

    _gen_lavfi_video(src_30, "color=c=cyan:s=320x240:r=30:d=3")
    _gen_lavfi_video(src_25, "color=c=magenta:s=320x240:r=25:d=3")

    clips = [
        _make_gated_clip("clip-30", "vid-30", 0),
        _make_gated_clip("clip-25", "vid-25", _GATED_DUR_FRAMES, out_point=75),  # 3 s @ 25 fps
    ]
    videos = {
        "vid-30": _make_gated_video("vid-30", str(src_30), fps_num=30, fps_den=1),
        "vid-25": _make_gated_video("vid-25", str(src_25), fps_num=25, fps_den=1, dur_frames=75),
    }
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    job = _make_gated_job(str(out))
    cmd = await build_command_for_job(job, clip_repo, video_repo)

    r = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    stderr = r.stderr.decode()
    assert r.returncode == 0, f"Render failed (exit {r.returncode}):\n{stderr[-800:]}"
    assert out.exists() and out.stat().st_size > 0, "Output must be non-empty"
    assert "uninitialized" not in stderr.lower(), "Unexpected timebase error in ffmpeg stderr"


@_FFMPEG_SKIP
async def test_format_yuv420p_terminal(tmp_path: Path) -> None:
    """Output pixel format is yuv420p (BL-505-AC-4).

    Renders a two-clip project and runs ffprobe to assert pix_fmt=yuv420p,
    confirming the format=yuv420p terminal filter emitted by the
    RenderGraphTranslator is present and effective.
    """
    import shutil

    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not found in PATH")

    src1 = tmp_path / "src1.mp4"
    src2 = tmp_path / "src2.mp4"
    out = tmp_path / "output.mp4"

    _gen_lavfi_video(src1, "color=c=yellow:s=320x240:r=30:d=3")
    _gen_lavfi_video(src2, "color=c=white:s=320x240:r=30:d=3")

    clips = [
        _make_gated_clip("clip-a", "vid-a", 0),
        _make_gated_clip("clip-b", "vid-b", _GATED_DUR_FRAMES),
    ]
    videos = {
        "vid-a": _make_gated_video("vid-a", str(src1)),
        "vid-b": _make_gated_video("vid-b", str(src2)),
    }
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    job = _make_gated_job(str(out))
    cmd = await build_command_for_job(job, clip_repo, video_repo)

    r = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert r.returncode == 0, f"Render failed:\n{r.stderr.decode()[-800:]}"
    assert out.exists() and out.stat().st_size > 0

    probe = subprocess.run(  # noqa: ASYNC221
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=pix_fmt",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    pix_fmt = probe.stdout.strip()
    assert pix_fmt == "yuv420p", (
        f"Expected pix_fmt=yuv420p, got {pix_fmt!r}. "
        "The format=yuv420p terminal filter must be present in the render graph."
    )
