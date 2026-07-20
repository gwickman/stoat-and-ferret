# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke tests for windowed non-T effect fallback (BL-512 split/trim/concat path).

Exercises the full server stack with a zoompan effect (timeline_T_capable=False)
applied inside a time window, confirming:
  - FR-001-AC-1: effect is visually present inside the window and absent outside
  - FR-002-AC-1: rendered output pix_fmt is yuv420p (ffprobe assertion)

Run with: STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/test_smoke_windowed_non_t.py -v
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import httpx
import pytest
from PIL import Image

from tests.smoke.conftest import poll_job_until_terminal, scan_videos_and_wait

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEMO_VIDEOS_DIR = Path(__file__).parent.parent.parent / "videos" / "demo"

# running1.mp4: 960x540, 30fps — chosen because zoompan output dimensions can
# match the input, making the split/trim/concat concat valid.
_TARGET_VIDEO = "running1.mp4"
_VIDEO_WIDTH = 960
_VIDEO_HEIGHT = 540
_VIDEO_FPS = 30

# Clip spans 3 seconds (90 frames at 30 fps).
_CLIP_FRAMES = 90
_CLIP_DURATION_S = float(_CLIP_FRAMES) / _VIDEO_FPS  # 3.0s

# Window from 1.0-2.0s inside the 3s clip — the non-T fallback splits here.
_WINDOW_START_S = 1.0
_WINDOW_END_S = 2.0

# Sample times for frame comparison (inside vs outside window).
_FRAME_OUTSIDE_S = 0.3  # before window
_FRAME_INSIDE_S = 1.5  # inside window


def _extract_frame(output_path: str, time_s: float, tmp_dir: Path) -> Image.Image:
    """Extract a single frame at *time_s* from *output_path* using ffmpeg.

    Args:
        output_path: Absolute path to the rendered MP4.
        time_s: Seek time in seconds.
        tmp_dir: Directory for temporary files.

    Returns:
        PIL Image of the extracted frame.

    Raises:
        AssertionError: If ffmpeg fails to extract the frame.
    """
    out_file = tmp_dir / f"frame_{time_s:.2f}s.png"
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(time_s),
            "-i",
            output_path,
            "-vframes",
            "1",
            "-q:v",
            "2",
            str(out_file),
        ],
        capture_output=True,
    )
    assert result.returncode == 0, (
        f"ffmpeg frame extraction failed at t={time_s}s: {result.stderr.decode(errors='replace')}"
    )
    assert out_file.exists() and out_file.stat().st_size > 0, (
        f"ffmpeg produced empty frame at t={time_s}s"
    )
    return Image.open(out_file).convert("RGB")


def _mean_channel_diff(img1: Image.Image, img2: Image.Image) -> float:
    """Compute mean per-channel absolute pixel difference between two RGB images.

    Returns:
        Float in [0, 255]: 0 means identical, 255 means maximally different.
    """
    pixels1 = list(img1.get_flattened_data())
    pixels2 = list(img2.get_flattened_data())
    total = 0
    for (r1, g1, b1), (r2, g2, b2) in zip(pixels1, pixels2, strict=False):
        total += abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2)
    return total / (3 * len(pixels1)) if pixels1 else 0.0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def _setup_windowed_zoompan_project(
    client: httpx.AsyncClient,
    videos_dir: Path,
) -> tuple[str, float]:
    """Scan demo videos, create a project with a clip, apply windowed zoompan.

    Returns:
        (project_id, render_total_duration)
    """
    await scan_videos_and_wait(client, videos_dir)

    # Resolve the target video.
    resp = await client.get("/api/v1/videos?limit=100")
    assert resp.status_code == 200
    videos: list[dict[str, Any]] = resp.json()["videos"]
    video = next((v for v in videos if v["filename"] == _TARGET_VIDEO), None)
    assert video is not None, (
        f"{_TARGET_VIDEO!r} not found after scan; available: {[v['filename'] for v in videos]}"
    )
    video_id = video["id"]

    # Create a project.
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Windowed Non-T Smoke Test"},
    )
    assert proj_resp.status_code == 201
    project_id: str = proj_resp.json()["id"]

    # Add a 3-second clip (90 frames at 30 fps).
    clip_resp = await client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "source_video_id": video_id,
            "in_point": 0,
            "out_point": _CLIP_FRAMES,
            "timeline_position": 0,
        },
    )
    assert clip_resp.status_code == 201
    clip_id: str = clip_resp.json()["id"]

    # Apply zoompan (timeline_T_capable=False) with a 1-2s window.
    # Output dimensions match running1.mp4 (960x540) so concat is valid.
    effect_resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={
            "effect_type": "zoompan",
            "parameters": {
                "z_expr": "1.5",
                "x_expr": "iw/2-(iw/zoom/2)",
                "y_expr": "ih/2-(ih/zoom/2)",
                "d": 30,
                "width": _VIDEO_WIDTH,
                "height": _VIDEO_HEIGHT,
                "fps": _VIDEO_FPS,
            },
            "window": {"start_s": _WINDOW_START_S, "end_s": _WINDOW_END_S},
        },
    )
    assert effect_resp.status_code == 201, f"Failed to apply zoompan effect: {effect_resp.text}"

    return project_id, _CLIP_DURATION_S


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("STOAT_TEST_FFMPEG"),
    reason="Requires STOAT_TEST_FFMPEG=1 and real FFmpeg",
)
@pytest.mark.usefixtures("videos_dir")
async def test_windowed_non_t_effect_renders_bounded(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
    tmp_path: Path,
) -> None:
    """BL-512 FR-001-AC-1: non-T windowed effect is present inside window, absent outside.

    Renders a zoompan (non-T-capable) effect bounded to t=[1.0, 2.0] on a 3s clip.
    Extracts frames at t=0.3s (outside) and t=1.5s (inside) and asserts they differ
    significantly, confirming the split/trim/concat path applied the effect only within
    the window boundaries.
    """
    project_id, total_duration = await _setup_windowed_zoompan_project(smoke_client, videos_dir)

    # Submit render.
    render_plan = json.dumps({"total_duration": total_duration, "settings": {}})
    resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": render_plan},
    )
    assert resp.status_code == 201, f"Render submit failed: {resp.text}"
    job_id: str = resp.json()["id"]

    # Poll until terminal (120s budget for FFmpeg render).
    final = await poll_job_until_terminal(smoke_client, job_id, timeout=120.0)
    assert final["status"] == "completed", (
        f"Render did not complete successfully — status={final['status']!r}, "
        f"error={final.get('error_message')!r}"
    )

    output_path = final.get("output_path", "")
    assert output_path, "output_path must be populated for a completed render"
    assert Path(output_path).exists(), f"Rendered file not found on disk: {output_path!r}"

    # Extract frames inside and outside the effect window.
    frame_outside = _extract_frame(output_path, _FRAME_OUTSIDE_S, tmp_path)
    frame_inside = _extract_frame(output_path, _FRAME_INSIDE_S, tmp_path)

    # Frames must differ: zoompan crops/scales the inside-window frames.
    # A 1.5x zoom produces a visually distinct frame vs the unzoomed original.
    diff = _mean_channel_diff(frame_outside, frame_inside)
    assert diff > 2.0, (
        f"Expected significant pixel difference between inside/outside window frames "
        f"(zoompan 1.5x zoom should be visible), got mean_diff={diff:.2f} — "
        f"the split/trim/concat path may not have applied the effect"
    )


@pytest.mark.skipif(
    not os.getenv("STOAT_TEST_FFMPEG"),
    reason="Requires STOAT_TEST_FFMPEG=1 and real FFmpeg",
)
@pytest.mark.usefixtures("videos_dir")
async def test_windowed_non_t_effect_yuv420p(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
    tmp_path: Path,
) -> None:
    """BL-512 FR-002-AC-1: non-T windowed render output pix_fmt is yuv420p.

    Renders a zoompan (non-T-capable) effect with a window, then uses ffprobe to
    assert the rendered output stream's pix_fmt is yuv420p. This confirms the
    explicit format=yuv420p conversion at each split/trim/concat segment junction
    is working correctly.
    """
    project_id, total_duration = await _setup_windowed_zoompan_project(smoke_client, videos_dir)

    # Submit render.
    render_plan = json.dumps({"total_duration": total_duration, "settings": {}})
    resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": render_plan},
    )
    assert resp.status_code == 201, f"Render submit failed: {resp.text}"
    job_id: str = resp.json()["id"]

    # Poll until terminal.
    final = await poll_job_until_terminal(smoke_client, job_id, timeout=120.0)
    assert final["status"] == "completed", (
        f"Render did not complete successfully — status={final['status']!r}, "
        f"error={final.get('error_message')!r}"
    )

    output_path = final.get("output_path", "")
    assert output_path, "output_path must be populated for a completed render"
    assert Path(output_path).exists(), f"Rendered file not found on disk: {output_path!r}"

    # Assert pix_fmt=yuv420p via ffprobe.
    result = subprocess.run(  # noqa: ASYNC221
        [
            "ffprobe",
            "-v",
            "quiet",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=pix_fmt",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            output_path,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"ffprobe failed: {result.stderr}"
    pix_fmt = result.stdout.strip()
    assert pix_fmt == "yuv420p", (
        f"Expected pix_fmt=yuv420p for non-T windowed render, got {pix_fmt!r}. "
        f"The format=yuv420p junction conversion may be missing."
    )
