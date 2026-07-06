# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for image clip routing in the render worker (BL-511, BL-604).

Covers:
- Schema verification for clip_type, source_asset_id, and duration constraint
- PNG/JPEG acceptance and TIFF rejection at upload layer (FR-005)
- Effects compatibility for image clips (FR-006)
- Multi-clip and single-clip render path for image clips (FR-001, FR-007)
- Animated opacity via RenderEffect.animated_alpha (FR-008)
"""

from __future__ import annotations

import io
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.api.routers.assets import _validate_image_magic_bytes
from stoat_ferret.api.schemas.clip import ClipCreate, ClipResponse
from stoat_ferret.db.asset_repository import AssetRecord
from stoat_ferret.db.models import Clip
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import CommandBuildError, build_command_for_job

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")
_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="Set STOAT_TEST_FFMPEG=1 to run FFmpeg-gated tests",
)

_PROJECT_ID = "proj-img-001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_render_job(output_path: str, total_duration: float = 3.0) -> RenderJob:
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
        id="job-img-001",
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
        out_point=90,
        timeline_position=timeline_position,
        created_at=now,
        updated_at=now,
        clip_type="image",
        source_asset_id=asset_id,
        timeline_start=timeline_start,
        timeline_end=timeline_end,
        effects=effects,
    )


def _make_asset_record(asset_id: str, file_path: str) -> AssetRecord:
    now = datetime.now(timezone.utc).isoformat()
    return AssetRecord(
        id=asset_id,
        original_filename="test.png",
        content_hash="abc123",
        mime_type="image/png",
        kind="image",
        size_bytes=1024,
        file_path=file_path,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def _write_solid_png(path: Path, width: int, height: int, color: tuple[int, int, int]) -> None:
    """Write a minimal solid-colour PNG via Pillow."""
    from PIL import Image

    img = Image.new("RGB", (width, height), color)
    img.save(str(path), format="PNG")


# ---------------------------------------------------------------------------
# FR-003: Schema verification (BL-511-AC-1, BL-511-AC-2)
# ---------------------------------------------------------------------------


def test_schema_clip_type_includes_image() -> None:
    """BL-511-AC-1: clip.py contains clip_type Literal with 'image'."""
    schema_path = (
        Path(__file__).parent.parent.parent / "src" / "stoat_ferret" / "api" / "schemas" / "clip.py"
    )
    content = schema_path.read_text(encoding="utf-8")
    assert 'clip_type: Literal["file", "generator", "image"]' in content, (
        'clip.py must declare clip_type: Literal["file", "generator", "image"]'
    )


def test_schema_source_asset_id_present() -> None:
    """BL-511-AC-2: clip.py contains source_asset_id: str | None = None."""
    schema_path = (
        Path(__file__).parent.parent.parent / "src" / "stoat_ferret" / "api" / "schemas" / "clip.py"
    )
    content = schema_path.read_text(encoding="utf-8")
    assert "source_asset_id: str | None = None" in content, (
        "clip.py must declare source_asset_id: str | None = None"
    )


# ---------------------------------------------------------------------------
# FR-004: Duration constraint (BL-511-AC-4)
# ---------------------------------------------------------------------------


def test_schema_duration_constraint_message_present() -> None:
    """BL-511-AC-4 grep: clip.py contains the duration constraint error message."""
    schema_path = (
        Path(__file__).parent.parent.parent / "src" / "stoat_ferret" / "api" / "schemas" / "clip.py"
    )
    content = schema_path.read_text(encoding="utf-8")
    assert "timeline_end is required for image clips" in content


def test_image_clip_missing_timeline_end_raises() -> None:
    """FR-004-AC-1 = BL-511-AC-4: image clip without timeline_end raises ValidationError."""
    with pytest.raises(Exception) as exc_info:
        ClipCreate(
            clip_type="image",
            source_asset_id="asset-001",
            in_point=0,
            out_point=90,
            timeline_position=0,
        )
    assert "timeline_end" in str(exc_info.value).lower()


def test_image_clip_with_timeline_end_valid() -> None:
    """FR-004: image clip with timeline_end passes validation."""
    clip = ClipCreate(
        clip_type="image",
        source_asset_id="asset-001",
        in_point=0,
        out_point=90,
        timeline_position=0,
        timeline_end=5.0,
    )
    assert clip.clip_type == "image"
    assert clip.timeline_end == 5.0


# ---------------------------------------------------------------------------
# FR-005: Format acceptance / rejection (BL-511-AC-5)
# ---------------------------------------------------------------------------


def _make_png_bytes() -> bytes:
    buf = io.BytesIO()
    from PIL import Image

    Image.new("RGB", (4, 4), (255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    from PIL import Image

    Image.new("RGB", (4, 4), (0, 255, 0)).save(buf, format="JPEG")
    return buf.getvalue()


def _make_tiff_bytes() -> bytes:
    buf = io.BytesIO()
    from PIL import Image

    Image.new("RGB", (4, 4), (0, 0, 255)).save(buf, format="TIFF")
    return buf.getvalue()


def test_png_format_accepted() -> None:
    """FR-005-AC-1: PNG bytes pass _validate_image_magic_bytes."""
    fmt, mime = _validate_image_magic_bytes(_make_png_bytes())
    assert fmt == "PNG"
    assert mime == "image/png"


def test_jpeg_format_accepted() -> None:
    """FR-005-AC-1: JPEG bytes pass _validate_image_magic_bytes."""
    fmt, mime = _validate_image_magic_bytes(_make_jpeg_bytes())
    assert fmt == "JPEG"
    assert mime == "image/jpeg"


def test_tiff_format_rejected() -> None:
    """FR-005-AC-1: TIFF bytes raise ValueError from _validate_image_magic_bytes."""
    with pytest.raises(ValueError, match="not allowed"):
        _validate_image_magic_bytes(_make_tiff_bytes())


# ---------------------------------------------------------------------------
# FR-006: Effects compatibility (BL-511-AC-6)
# ---------------------------------------------------------------------------


def test_image_clip_effects_stored_in_response() -> None:
    """FR-006-AC-1 = BL-511-AC-6: ClipResponse accepts effects for image clip_type."""
    now = datetime.now(timezone.utc)
    response = ClipResponse(
        id="clip-001",
        project_id=_PROJECT_ID,
        source_video_id=None,
        source_asset_id="asset-001",
        clip_type="image",
        in_point=0,
        out_point=90,
        timeline_position=0,
        timeline_start=0.0,
        timeline_end=3.0,
        effects=[
            {"effect_type": "blur", "parameters": {"sigma": 5.0}},
            {"effect_type": "opacity", "parameters": {"opacity": 0.8}},
        ],
        created_at=now,
        updated_at=now,
    )

    assert response.clip_type == "image"
    assert len(response.effects) == 2
    assert response.effects[0]["effect_type"] == "blur"
    assert response.effects[1]["effect_type"] == "opacity"


# ---------------------------------------------------------------------------
# Unit tests: command structure (no FFmpeg execution)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_image_clip_multi_clip_command_uses_loop_flag() -> None:
    """FR-001: multi-clip image clip emits -loop 1 -i <path> in command."""
    img_path = "/fake/image.png"
    asset_id = "asset-001"

    asset_record = _make_asset_record(asset_id, img_path)
    asset_repo = AsyncMock()
    asset_repo.get_by_id = AsyncMock(return_value=asset_record)

    clips = [
        _make_image_clip("clip-a", asset_id, timeline_position=0),
        _make_image_clip("clip-b", asset_id, timeline_position=90),
    ]

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=None)

    job = _make_render_job("/out/result.mp4", total_duration=6.0)
    cmd = await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)

    assert cmd[0] == "ffmpeg"
    assert "-loop" in cmd
    loop_idx = cmd.index("-loop")
    assert cmd[loop_idx + 1] == "1"
    assert cmd[loop_idx + 2] == "-i"
    assert cmd[loop_idx + 3] == img_path


@pytest.mark.asyncio
async def test_image_clip_single_clip_command_uses_loop_flag() -> None:
    """FR-007: single-clip image path emits -loop 1 -i <path> in command."""
    img_path = "/fake/image.png"
    asset_id = "asset-001"

    asset_record = _make_asset_record(asset_id, img_path)
    asset_repo = AsyncMock()
    asset_repo.get_by_id = AsyncMock(return_value=asset_record)

    clips = [_make_image_clip("clip-a", asset_id, timeline_position=0)]

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=None)

    job = _make_render_job("/out/result.mp4")
    cmd = await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)

    assert cmd[0] == "ffmpeg"
    assert cmd[1] == "-loop"
    assert cmd[2] == "1"
    assert cmd[3] == "-i"
    assert cmd[4] == img_path
    assert "-filter_complex" in cmd


@pytest.mark.asyncio
async def test_image_clip_missing_asset_repository_raises() -> None:
    """Image clip without asset_repository raises CommandBuildError."""
    clips = [_make_image_clip("clip-a", "asset-001", timeline_position=0)]
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()

    job = _make_render_job("/out/result.mp4")
    with pytest.raises(CommandBuildError, match="asset_repository"):
        await build_command_for_job(job, clip_repo, video_repo)


@pytest.mark.asyncio
async def test_image_clip_soft_deleted_asset_raises() -> None:
    """Soft-deleted image asset raises CommandBuildError."""
    now_iso = datetime.now(timezone.utc).isoformat()
    deleted_asset = AssetRecord(
        id="asset-001",
        original_filename="test.png",
        content_hash="abc",
        mime_type="image/png",
        kind="image",
        size_bytes=100,
        file_path="/fake/image.png",
        created_at=now_iso,
        updated_at=now_iso,
        deleted_at=now_iso,
    )
    asset_repo = AsyncMock()
    asset_repo.get_by_id = AsyncMock(return_value=deleted_asset)

    clips = [_make_image_clip("clip-a", "asset-001", timeline_position=0)]
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()

    job = _make_render_job("/out/result.mp4")
    with pytest.raises(CommandBuildError, match="not found"):
        await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)


# ---------------------------------------------------------------------------
# STOAT_TEST_FFMPEG-gated integration tests
# ---------------------------------------------------------------------------


@_FFMPEG_SKIP
async def test_image_clip_multi_clip_render(tmp_path: Path) -> None:
    """FR-001-AC-1 = BL-604-AC-1: multi-clip with image clips renders non-empty mp4."""
    img1 = tmp_path / "img1.png"
    img2 = tmp_path / "img2.png"
    out = tmp_path / "output.mp4"

    _write_solid_png(img1, 320, 240, (200, 50, 50))
    _write_solid_png(img2, 320, 240, (50, 50, 200))

    asset_repo = AsyncMock()
    asset_repo.get_by_id = AsyncMock(
        side_effect=lambda aid: _make_asset_record(aid, str(img1) if aid == "a1" else str(img2))
    )

    clips = [
        _make_image_clip("clip-a", "a1", timeline_position=0, timeline_end=3.0),
        _make_image_clip("clip-b", "a2", timeline_position=90, timeline_end=3.0),
    ]
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=None)

    job = _make_render_job(str(out), total_duration=6.0)
    cmd = await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)
    cmd.append("-y")

    r = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert r.returncode == 0, f"Render failed: {r.stderr.decode()[-800:]}"
    assert out.exists() and out.stat().st_size > 0


@_FFMPEG_SKIP
async def test_image_clip_single_clip_render(tmp_path: Path) -> None:
    """FR-007-AC-1: single image clip renders non-empty mp4."""
    img = tmp_path / "img.png"
    out = tmp_path / "output.mp4"

    _write_solid_png(img, 320, 240, (100, 200, 100))

    asset_repo = AsyncMock()
    asset_repo.get_by_id = AsyncMock(return_value=_make_asset_record("asset-001", str(img)))

    clips = [_make_image_clip("clip-a", "asset-001", timeline_position=0, timeline_end=3.0)]
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()

    job = _make_render_job(str(out), total_duration=3.0)
    cmd = await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)
    cmd.append("-y")

    r = subprocess.run(cmd, capture_output=True, timeout=60)  # noqa: ASYNC221
    assert r.returncode == 0, f"Render failed: {r.stderr.decode()[-800:]}"
    assert out.exists() and out.stat().st_size > 0


@_FFMPEG_SKIP
async def test_image_clip_animated_opacity(tmp_path: Path) -> None:
    """FR-008-AC-1 = BL-511-AC-7: image clip with RenderEffect.animated_alpha renders cleanly.

    Uses RenderEffect.animated_alpha(0.0, 1.0) directly via PyO3 binding.
    """
    from stoat_ferret_core import ClipWithEffects, RenderEffect, RenderGraphTranslator

    effect = RenderEffect.animated_alpha(0.0, 1.0)
    assert effect is not None
    assert "animated_alpha" in repr(effect)

    img = tmp_path / "img.png"
    out = tmp_path / "output.mp4"
    _write_solid_png(img, 320, 240, (128, 64, 200))

    dur_secs = 3.0
    fps = 30.0

    cwe = ClipWithEffects(
        input_index=0,
        duration_secs=dur_secs,
        framerate=fps,
        source_path=str(img),
        effects=[effect],
    )
    translator = RenderGraphTranslator()
    filter_complex, _ = translator.translate([cwe])

    cmd = [
        "ffmpeg",
        "-loop",
        "1",
        "-i",
        str(img),
        "-filter_complex",
        filter_complex,
        "-map",
        "[final]",
        "-an",
        "-c:v",
        "libx264",
        "-r",
        str(fps),
        "-t",
        str(dur_secs),
        "-progress",
        "pipe:1",
        "-y",
        str(out),
    ]

    r = subprocess.run(cmd, capture_output=True, timeout=60)  # noqa: ASYNC221
    assert r.returncode == 0, f"Render failed: {r.stderr.decode()[-800:]}"
    assert out.exists() and out.stat().st_size > 0
