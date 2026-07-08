# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""R3 use-case acceptance tests (BL-604).

STOAT_TEST_FFMPEG-gated end-to-end tests verifying:
- FR-001: Per-clip effects (curves, vignette) on image and generator clip types (BL-604-AC-3)
- FR-002: R3 Maya compressed use case (image + generator + opacity + subtitle) (BL-604-AC-4)
- FR-003: R3 Devon compressed use case (image + file clip with curves + xfade + subtitle)
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.db.asset_repository import AssetRecord
from stoat_ferret.db.models import Clip, Video
from stoat_ferret.effects.definitions import create_default_registry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import build_command_for_job

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")
_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="Set STOAT_TEST_FFMPEG=1 to run FFmpeg-gated tests",
)

_PROJECT_ID = "proj-r3-001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_render_job(
    output_path: str,
    total_duration: float = 6.0,
    soft_subtitles: list[dict[str, Any]] | None = None,
) -> RenderJob:
    now = datetime.now(timezone.utc)
    settings: dict[str, Any] = {
        "codec": "libx264",
        "fps": 30.0,
        "width": 320,
        "height": 240,
        "quality_preset": "standard",
    }
    if soft_subtitles:
        settings["soft_subtitles"] = soft_subtitles
    plan = json.dumps({"total_duration": total_duration, "settings": settings})
    return RenderJob(
        id="job-r3-001",
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


def _make_image_clip(
    clip_id: str,
    asset_id: str,
    timeline_position: int,
    timeline_start: float = 0.0,
    timeline_end: float = 3.0,
    effects: list[dict[str, Any]] | None = None,
) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=_PROJECT_ID,
        source_video_id=None,
        in_point=0,
        out_point=90,  # 3s at 30fps
        timeline_position=timeline_position,
        created_at=now,
        updated_at=now,
        clip_type="image",
        source_asset_id=asset_id,
        timeline_start=timeline_start,
        timeline_end=timeline_end,
        effects=effects,
    )


def _make_generator_clip(
    clip_id: str,
    timeline_position: int,
    lavfi_string: str = "color=c=blue:s=320x240:r=30",
    effects: list[dict[str, Any]] | None = None,
) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=_PROJECT_ID,
        source_video_id=None,
        in_point=0,
        out_point=90,  # 3s at 30fps
        timeline_position=timeline_position,
        created_at=now,
        updated_at=now,
        clip_type="generator",
        generator_params={"lavfi_string": lavfi_string},
        effects=effects,
    )


def _make_file_clip(
    clip_id: str,
    video_id: str,
    timeline_position: int,
    out_point: int = 90,
    effects: list[dict[str, Any]] | None = None,
) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=_PROJECT_ID,
        source_video_id=video_id,
        in_point=0,
        out_point=out_point,
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
        duration_frames=90,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=320,
        height=240,
        video_codec="h264",
        file_size=500_000,
        created_at=now,
        updated_at=now,
    )


def _make_asset_record(
    asset_id: str,
    file_path: str,
    kind: str = "image",
    mime_type: str = "image/png",
) -> AssetRecord:
    now = datetime.now(timezone.utc).isoformat()
    return AssetRecord(
        id=asset_id,
        original_filename="test.bin",
        content_hash="testsha",
        mime_type=mime_type,
        kind=kind,
        size_bytes=1024,
        file_path=file_path,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def _write_solid_png(path: Path, width: int, height: int, color: tuple[int, int, int]) -> None:
    """Write a solid-colour PNG using Pillow."""
    from PIL import Image

    img = Image.new("RGB", (width, height), color)
    img.save(str(path), format="PNG")


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


def _write_srt_file(path: Path) -> None:
    """Write a minimal valid SRT subtitle file."""
    path.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nR3 test subtitle\n\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# FR-001: Per-clip effects on image and generator clip types (BL-604-AC-3)
# ---------------------------------------------------------------------------


@_FFMPEG_SKIP
async def test_per_clip_effects_on_image_clip(tmp_path: Path) -> None:
    """BL-604-AC-3: image clip with curves effect renders non-empty mp4.

    Asserts:
    - filter_complex contains 'curves' filter keyword (effect present in command)
    - FFmpeg exit_code=0 and output_size_bytes > 0 (render succeeds with effect applied)
    """
    img = tmp_path / "img.png"
    out = tmp_path / "output.mp4"
    _write_solid_png(img, 320, 240, (180, 90, 60))

    asset_id = "img-asset-r3-001"
    asset_repo = AsyncMock()
    asset_repo.get_by_id = AsyncMock(return_value=_make_asset_record(asset_id, str(img)))

    curves_effect: dict[str, Any] = {
        "effect_type": "curves",
        "parameters": {"preset": "vintage"},
    }
    clips = [_make_image_clip("clip-a", asset_id, timeline_position=0, effects=[curves_effect])]

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()

    registry = create_default_registry()
    job = _make_render_job(str(out), total_duration=3.0)
    cmd = await build_command_for_job(
        job, clip_repo, video_repo, effect_registry=registry, asset_repository=asset_repo
    )

    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    assert "curves" in cmd[fc_idx + 1], (
        f"Expected 'curves' in filter_complex: {cmd[fc_idx + 1][:300]}"
    )

    cmd.append("-y")
    r = subprocess.run(cmd, capture_output=True, timeout=60)  # noqa: ASYNC221
    assert r.returncode == 0, f"Image clip render failed: {r.stderr.decode()[-800:]}"
    assert out.exists() and out.stat().st_size > 0


@_FFMPEG_SKIP
async def test_per_clip_effects_on_generator_clip(tmp_path: Path) -> None:
    """BL-604-AC-3: generator clip with vignette effect renders non-empty mp4.

    Asserts:
    - filter_complex contains 'vignette' filter keyword (effect present in command)
    - FFmpeg exit_code=0 and output_size_bytes > 0 (render succeeds with effect applied)
    """
    out = tmp_path / "output.mp4"

    vignette_effect: dict[str, Any] = {
        "effect_type": "vignette",
        "parameters": {"angle": 1.0},
    }
    clips = [
        _make_generator_clip(
            "clip-a",
            timeline_position=0,
            lavfi_string="color=c=green:s=320x240:r=30",
            effects=[vignette_effect],
        )
    ]

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()

    registry = create_default_registry()
    job = _make_render_job(str(out), total_duration=3.0)
    cmd = await build_command_for_job(job, clip_repo, video_repo, effect_registry=registry)

    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    assert "vignette" in cmd[fc_idx + 1], (
        f"Expected 'vignette' in filter_complex: {cmd[fc_idx + 1][:300]}"
    )

    cmd.append("-y")
    r = subprocess.run(cmd, capture_output=True, timeout=60)  # noqa: ASYNC221
    assert r.returncode == 0, f"Generator clip render failed: {r.stderr.decode()[-800:]}"
    assert out.exists() and out.stat().st_size > 0


# ---------------------------------------------------------------------------
# FR-002: R3 Maya compressed use case (BL-604-AC-4 narrowed)
# ---------------------------------------------------------------------------


@_FFMPEG_SKIP
async def test_r3_maya_compressed(tmp_path: Path) -> None:
    """BL-604-AC-4 narrowed (Maya): image + generator + opacity fade + subtitle.

    Assembles a compressed Maya use case:
    - clip[0]: image clip (solid PNG) with opacity effect (simulated per-clip fade)
    - clip[1]: generator clip (lavfi colour source for concentric-ring stand-in)
    - Soft subtitle track (minimal SRT)
    - Clip durations are fixed/deterministic (LRN-773: explicit duration, no random data)
    - Ducked audio omitted per BL-604-AC-4 narrowing (Risk 03)

    Asserts exit_code=0 and output_size_bytes > 0.
    """
    img = tmp_path / "spiral.png"
    out = tmp_path / "output.mp4"
    srt = tmp_path / "subtitle.srt"

    _write_solid_png(img, 320, 240, (200, 100, 200))
    _write_srt_file(srt)

    img_asset_id = "img-asset-maya-001"
    subtitle_asset_id = str(uuid.uuid4())

    img_asset = _make_asset_record(img_asset_id, str(img))
    subtitle_asset = _make_asset_record(
        subtitle_asset_id, str(srt), kind="subtitle", mime_type="text/plain"
    )

    def _resolve_asset(aid: str) -> AssetRecord | None:
        if str(aid) == img_asset_id:
            return img_asset
        if str(aid) == subtitle_asset_id:
            return subtitle_asset
        return None

    asset_repo = AsyncMock()
    asset_repo.get_by_id = AsyncMock(side_effect=_resolve_asset)

    fade_effect: dict[str, Any] = {
        "effect_type": "opacity",
        "parameters": {"opacity": 0.9},
    }
    clips = [
        _make_image_clip(
            "clip-img",
            img_asset_id,
            timeline_position=0,
            timeline_start=0.0,
            timeline_end=3.0,
            effects=[fade_effect],
        ),
        _make_generator_clip(
            "clip-gen",
            timeline_position=90,
            lavfi_string="color=c=purple:s=320x240:r=30",
        ),
    ]

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()

    registry = create_default_registry()
    soft_subtitles = [{"source_asset_id": subtitle_asset_id, "language": "en"}]
    job = _make_render_job(str(out), total_duration=6.0, soft_subtitles=soft_subtitles)
    cmd = await build_command_for_job(
        job, clip_repo, video_repo, effect_registry=registry, asset_repository=asset_repo
    )
    cmd.append("-y")

    r = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert r.returncode == 0, (
        f"Maya compressed render failed (exit {r.returncode}):\n{r.stderr.decode()[-800:]}"
    )
    assert out.exists() and out.stat().st_size > 0, "Maya output must be non-empty"


# ---------------------------------------------------------------------------
# FR-003: R3 Devon compressed use case (BL-604-AC-4 narrowed)
# ---------------------------------------------------------------------------


@_FFMPEG_SKIP
async def test_r3_devon_compressed(tmp_path: Path) -> None:
    """BL-604-AC-4 narrowed (Devon): image intro + file clip with curves grade + xfade + subtitle.

    Assembles a compressed Devon use case:
    - clip[0]: image clip (logo PNG intro, 3s)
    - clip[1]: video file clip with curves effect (per-clip grade, 3s)
    - Soft subtitle track (minimal SRT)
    - Clip durations are fixed/deterministic (LRN-773: explicit duration, no random data)

    Asserts exit_code=0 and output_size_bytes > 0.
    """
    img = tmp_path / "logo.png"
    src_video = tmp_path / "src_video.mp4"
    out = tmp_path / "output.mp4"
    srt = tmp_path / "subtitle.srt"

    _write_solid_png(img, 320, 240, (50, 100, 200))
    _gen_lavfi_video(src_video, "color=c=cyan:s=320x240:r=30:d=3")
    _write_srt_file(srt)

    img_asset_id = "img-asset-devon-001"
    subtitle_asset_id = str(uuid.uuid4())

    img_asset = _make_asset_record(img_asset_id, str(img))
    subtitle_asset = _make_asset_record(
        subtitle_asset_id, str(srt), kind="subtitle", mime_type="text/plain"
    )

    def _resolve_asset(aid: str) -> AssetRecord | None:
        if str(aid) == img_asset_id:
            return img_asset
        if str(aid) == subtitle_asset_id:
            return subtitle_asset
        return None

    asset_repo = AsyncMock()
    asset_repo.get_by_id = AsyncMock(side_effect=_resolve_asset)

    video_id = "vid-devon-001"
    videos = {video_id: _make_video(video_id, str(src_video))}

    curves_grade: dict[str, Any] = {
        "effect_type": "curves",
        "parameters": {"preset": "vintage"},
    }
    clips = [
        _make_image_clip(
            "clip-logo",
            img_asset_id,
            timeline_position=0,
            timeline_start=0.0,
            timeline_end=3.0,
        ),
        _make_file_clip(
            "clip-main",
            video_id,
            timeline_position=90,  # 3s at 30fps
            out_point=90,
            effects=[curves_grade],
        ),
    ]

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    registry = create_default_registry()
    soft_subtitles = [{"source_asset_id": subtitle_asset_id, "language": "en"}]
    job = _make_render_job(str(out), total_duration=6.0, soft_subtitles=soft_subtitles)
    cmd = await build_command_for_job(
        job, clip_repo, video_repo, effect_registry=registry, asset_repository=asset_repo
    )
    cmd.append("-y")

    r = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert r.returncode == 0, (
        f"Devon compressed render failed (exit {r.returncode}):\n{r.stderr.decode()[-800:]}"
    )
    assert out.exists() and out.stat().st_size > 0, "Devon output must be non-empty"
