# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_preview_parity — preview uses full composition graph (BL-797 AC-1).

Starts a preview session for a multi-clip project and asserts that:
- The session is created successfully (HTTP 202)
- The FFmpeg command receives multiple -i inputs (one per clip)

All tests are FFmpeg-gated (STOAT_TEST_FFMPEG=1).
Run with: STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/test_uc_media_preview_parity.py -v
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import PreviewQuality, PreviewSession, PreviewStatus, Video
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.preview.manager import PreviewManager
from tests.test_api.conftest import InMemoryAssetRepository

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)

_PROJECT_ID = "proj-preview-parity-001"
_SOURCE_W = 640
_SOURCE_H = 360


def _make_video_fixture(path: Path, duration: int = 2) -> Path:
    """Generate a small test video using lavfi testsrc2."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size={_SOURCE_W}x{_SOURCE_H}:rate=30:duration={duration}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        capture_output=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg fixture generation failed: {result.stderr.decode()[-800:]}")
    return path


def _make_video(vid_id: str, path: str) -> Video:
    now = datetime.now(timezone.utc)
    return Video(
        id=vid_id,
        path=path,
        filename=f"{vid_id}.mp4",
        duration_frames=60,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=_SOURCE_W,
        height=_SOURCE_H,
        video_codec="h264",
        file_size=100_000,
        created_at=now,
        updated_at=now,
        audio_codec=None,
    )


@_FFMPEG_SKIP
@pytest.mark.asyncio
async def test_preview_start_receives_multiple_inputs(tmp_path: Path) -> None:
    """Preview start for a two-clip project calls manager.start with two input paths.

    Verifies AC-1: the start handler builds a composition graph and passes
    input_paths with one entry per clip (not just clips[0]).
    """
    vid_a = tmp_path / "clip_a.mp4"
    vid_b = tmp_path / "clip_b.mp4"
    _make_video_fixture(vid_a)
    _make_video_fixture(vid_b)

    video_repo = AsyncInMemoryVideoRepository()
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()

    video_a = _make_video("vid-a", str(vid_a))
    video_b = _make_video("vid-b", str(vid_b))
    await video_repo.add(video_a)
    await video_repo.add(video_b)

    captured_input_paths: list[str] = []

    mock_manager = MagicMock(spec=PreviewManager)

    async def _capture_start(**kwargs: object) -> PreviewSession:
        from datetime import timedelta

        captured_input_paths.extend(kwargs.get("input_paths", []))  # type: ignore[arg-type]
        now = datetime.now(timezone.utc)
        return PreviewSession(
            id="sess-001",
            project_id=_PROJECT_ID,
            status=PreviewStatus.INITIALIZING,
            manifest_path=None,
            error_message=None,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=1),
            quality_level=PreviewQuality.MEDIUM,
        )

    mock_manager.start = AsyncMock(side_effect=_capture_start)

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        preview_manager=mock_manager,
        asset_repository=InMemoryAssetRepository(),
    )

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "preview-parity-test",
                "output_width": _SOURCE_W,
                "output_height": _SOURCE_H,
                "output_fps": 30,
            },
        )
        assert proj_resp.status_code == 201, proj_resp.text
        project_id = proj_resp.json()["id"]

        # Create clips via HTTP API — BL-831 fix propagates timeline_start/timeline_end
        clip_a_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "clip_type": "file",
                "source_video_id": "vid-a",
                "in_point": 0,
                "out_point": 60,
                "timeline_position": 0,
                "timeline_start": 0.0,
                "timeline_end": 2.0,
            },
        )
        assert clip_a_resp.status_code == 201, clip_a_resp.text
        clip_b_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "clip_type": "file",
                "source_video_id": "vid-b",
                "in_point": 0,
                "out_point": 60,
                "timeline_position": 60,
                "timeline_start": 2.0,
                "timeline_end": 4.0,
            },
        )
        assert clip_b_resp.status_code == 201, clip_b_resp.text

        with patch("stoat_ferret.api.routers.preview.shutil.which", return_value="/usr/bin/ffmpeg"):
            start_resp = await client.post(f"/api/v1/projects/{project_id}/preview/start")

    assert start_resp.status_code == 202, start_resp.text
    assert len(captured_input_paths) == 2, (
        f"expected 2 input paths for 2-clip project, got {captured_input_paths!r}"
    )


# ---- BL-838 AC-6: Preview/render SSIM parity (oracle-verified) ----


def _make_colored_clip_parity(path: Path, color: str, duration: float = 3.0, fps: int = 30) -> Path:
    """Generate a solid-color clip for parity testing."""
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=320x240:r={fps}:d={duration}",
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
        msg = r.stderr.decode()[-400:]
        raise RuntimeError(f"ffmpeg fixture generation failed ({color}): {msg}")
    return path


def _make_parity_reference_render(
    clip1: Path,
    clip2: Path,
    out: Path,
    filter_complex_str: str,
    clip1_in_point: float,
    output_fps: float,
) -> None:
    """Produce a reference render with the same FFmpeg parameters as the preview path."""
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(clip1_in_point),
            "-i",
            str(clip1),
            "-i",
            str(clip2),
            "-r",
            str(int(output_fps)),
            "-filter_complex",
            filter_complex_str,
            "-map",
            "[final]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        capture_output=True,
        timeout=120,
    )
    if r.returncode != 0:
        raise RuntimeError(f"Reference render failed: {r.stderr.decode()[-600:]}")


@_FFMPEG_SKIP
@pytest.mark.asyncio
async def test_preview_render_parity_multiclip_ssim(tmp_path: Path) -> None:
    """Preview and reference render agree (SSIM >= 0.90) for a multi-clip project with
    non-zero in_point, non-default fps, and a visible effect on clip 2 (BL-838-AC-6).

    Test matrix:
    - Clip 1 (red): in_point=0.5s (source seek), duration=2.0s on timeline, no effects
    - Clip 2 (green): in_point=0.0s, duration=2.0s on timeline, hue-shift effect
    - output_fps=24 (non-default)
    """
    import asyncio

    from stoat_ferret.ffmpeg.async_executor import RealAsyncFFmpegExecutor
    from stoat_ferret.preview.hls_generator import HLSGenerator
    from stoat_ferret_core import ClipWithEffects, RenderEffect, RenderGraphTranslator
    from tests.preview_oracle import _compute_ssim_hls_vs_file, materialize_preview_session

    OUTPUT_FPS = 24.0
    CLIP_FPS = 30
    CLIP1_SOURCE_DUR = 3.0
    CLIP2_SOURCE_DUR = 3.0
    CLIP1_IN_POINT = 0.5  # skip first 0.5s of clip1
    CLIP1_TIMELINE_DUR = 2.0
    CLIP2_TIMELINE_DUR = 2.0

    clip1_path = _make_colored_clip_parity(
        tmp_path / "clip1.mp4", "red", CLIP1_SOURCE_DUR, CLIP_FPS
    )
    clip2_path = _make_colored_clip_parity(
        tmp_path / "clip2.mp4", "green", CLIP2_SOURCE_DUR, CLIP_FPS
    )

    # Build ClipWithEffects: clip1 (no effect, has in_point), clip2 (hue-shift effect)
    cwe_list = [
        ClipWithEffects(
            input_index=0,
            duration_secs=CLIP1_TIMELINE_DUR,
            framerate=float(CLIP_FPS),
            source_path=str(clip1_path),
            effects=[RenderEffect.none()],
            outgoing_transition=None,
        ),
        ClipWithEffects(
            input_index=1,
            duration_secs=CLIP2_TIMELINE_DUR,
            framerate=float(CLIP_FPS),
            source_path=str(clip2_path),
            effects=[RenderEffect.custom("hue=h=60")],
            outgoing_transition=None,
        ),
    ]

    translator = RenderGraphTranslator()
    filter_complex_str, _ = translator.translate(cwe_list, OUTPUT_FPS)

    # Reference render: same filter_complex, same in_point for clip1
    render_path = tmp_path / "render.mp4"
    _make_parity_reference_render(
        clip1_path, clip2_path, render_path, filter_complex_str, CLIP1_IN_POINT, OUTPUT_FPS
    )
    assert render_path.exists()

    # Preview: same filter_complex and per-clip args via HLSGenerator
    session_id = "parity-ssim-001"
    hls_base = tmp_path / "hls"
    executor = RealAsyncFFmpegExecutor()
    generator = HLSGenerator(async_executor=executor, output_base_dir=str(hls_base))
    output_dir = await generator.generate(
        session_id=session_id,
        input_paths=[str(clip1_path), str(clip2_path)],
        filter_complex_str=filter_complex_str,
        in_point_secs=[CLIP1_IN_POINT, 0.0],
        output_fps=OUTPUT_FPS,
    )
    assert (output_dir / "manifest.m3u8").exists(), "HLS manifest must exist"
    assert any(f.suffix == ".ts" for f in output_dir.iterdir()), ">=1 .ts segment must exist"

    session = await materialize_preview_session(session_id, output_dir)
    manifest_path = session["manifest_path"]

    # Compare at t=0.7 (within clip1 range) and t=2.3 (within clip2 range)
    for t in [0.7, 2.3]:
        ssim = await asyncio.to_thread(
            _compute_ssim_hls_vs_file,
            manifest_path,
            t,
            render_path,
            t,
        )
        assert ssim >= 0.90, (
            f"SSIM at t={t}s = {ssim:.4f} < 0.90 — preview/render parity failure (BL-838-AC-6)"
        )
