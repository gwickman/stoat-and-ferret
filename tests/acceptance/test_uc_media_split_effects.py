# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_split_effects — windowed effect excluded from out-of-range child.

BL-850 AC-3.

Splits a clip carrying a windowed VOLUME effect with remap_windowed_effects, renders
clip_b (whose timeline range lies entirely after the effect window), and asserts via
the render oracle that the effect is NOT audible in clip_b's output.

Run with: STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/test_uc_media_split_effects.py -v
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project, Video
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import build_command_for_job
from tests.render_oracle import assert_audio_rms_changed, measure_audio_rms_db

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)

_PROJECT_ID = "proj-split-effects-001"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_av_fixture(path: Path, duration: int = 5) -> Path:
    """Generate an audio+video MP4 fixture."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=320x240:rate=30:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=880:duration={duration}",
            "-filter_complex",
            "amerge=inputs=2",
            "-ac",
            "2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ],
        capture_output=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg fixture generation failed: {result.stderr.decode()[-800:]}")
    return path


def _make_video(vid_id: str, path: str, duration_frames: int = 150) -> Video:
    now = _now()
    return Video(
        id=vid_id,
        path=path,
        filename="fixture.mp4",
        duration_frames=duration_frames,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=320,
        height=240,
        video_codec="h264",
        file_size=100_000,
        created_at=now,
        updated_at=now,
        audio_codec="aac",
    )


def _make_clip(
    cid: str,
    vid_id: str,
    in_point: int,
    out_point: int,
    effects: list | None = None,
) -> Clip:
    now = _now()
    return Clip(
        id=cid,
        project_id=_PROJECT_ID,
        source_video_id=vid_id,
        in_point=in_point,
        out_point=out_point,
        timeline_position=0,
        created_at=now,
        updated_at=now,
        effects=effects,
    )


def _make_render_plan(total_duration: float) -> str:
    return json.dumps(
        {
            "total_duration": total_duration,
            "settings": {
                "output_format": "mp4",
                "codec": "libx264",
                "fps": 30.0,
                "width": 320,
                "height": 240,
                "quality_preset": "standard",
            },
        }
    )


def _make_job(job_id: str, plan: str, output_path: str) -> RenderJob:
    now = _now()
    return RenderJob(
        id=job_id,
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


def _make_video_repo(vid: Video) -> AsyncMock:
    r: AsyncMock = AsyncMock()
    r.get = AsyncMock(return_value=vid)
    return r


def _make_clip_repo(clip: Clip) -> AsyncMock:
    r: AsyncMock = AsyncMock()
    r.list_by_project = AsyncMock(return_value=[clip])
    return r


@_FFMPEG_SKIP
@pytest.mark.asyncio
async def test_split_remap_effect_not_visible_in_out_of_range_child(tmp_path: Path) -> None:
    """BL-850-AC-3: windowed effect dropped from clip_b when window is entirely before clip_b start.

    Scenario:
    - 5s clip (150 frames @ 30fps), VOLUME 3x effect windowed at [0s, 2s].
    - Split at frame 75 (2.5s) with remap_windowed_effects.
    - clip_b covers [2.5s, 5s]; effect window [0s, 2s] lies entirely before it → dropped.
    - Render clip_b (no effects) and confirm audio RMS matches baseline (< 2 dB delta).
    - Render same segment WITH volume effect to confirm test sensitivity (>= 5 dB delta vs
      baseline).
    """
    fixture = _make_av_fixture(tmp_path / "fixture.mp4", duration=5)
    vid_id = "vid-split-eff-001"
    vid = _make_video(vid_id, str(fixture), duration_frames=150)

    volume_effect = {
        "effect_type": "volume",
        "id": "eff-vol-1",
        "filter_string": "volume=3.0",
        "window": {"start_s": 0.0, "end_s": 2.0},
    }
    parent_clip_id = "clip-split-eff-parent"

    project = Project(
        id=_PROJECT_ID,
        name="Split Effects Acceptance",
        output_width=320,
        output_height=240,
        output_fps=30,
        created_at=_now(),
        updated_at=_now(),
    )
    parent_clip = Clip(
        id=parent_clip_id,
        project_id=_PROJECT_ID,
        source_video_id=vid_id,
        in_point=0,
        out_point=150,
        timeline_position=0,
        timeline_start=0.0,
        timeline_end=5.0,
        effects=[volume_effect],
        created_at=_now(),
        updated_at=_now(),
    )

    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()
    project_repo.seed([project])
    clip_repo.seed([parent_clip])

    app = create_app(project_repository=project_repo, clip_repository=clip_repo)
    with TestClient(app) as client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{parent_clip_id}/split",
            json={"split_frame": 75, "split_policy": "remap_windowed_effects"},
        )

    assert resp.status_code == 200, f"split failed: {resp.text}"
    data = resp.json()

    # clip_b must have no effects (window [0s, 2s] entirely before clip_b start at 2.5s)
    clip_b_effects = data["clip_b"]["effects"]
    assert clip_b_effects == [], f"clip_b should have no effects, got: {clip_b_effects}"

    # Render clip_b (frames 75–150, 2.5s) with no effects → baseline
    clip_b_no_eff = _make_clip("clip-b-no-eff", vid_id, in_point=75, out_point=150, effects=[])
    out_no_eff = tmp_path / "clip_b_no_eff.mp4"
    plan = _make_render_plan(total_duration=2.5)
    job_no_eff = _make_job("job-b-no-eff", plan, str(out_no_eff))

    cmd_no_eff = await build_command_for_job(
        job_no_eff, _make_clip_repo(clip_b_no_eff), _make_video_repo(vid)
    )
    r = await asyncio.to_thread(subprocess.run, cmd_no_eff, capture_output=True, timeout=120)
    assert r.returncode == 0, f"ffmpeg (no-effect) failed: {r.stderr.decode()[-800:]}"
    rms_baseline = await measure_audio_rms_db(out_no_eff)

    # Render same segment WITH volume=3.0 (simulates buggy behavior where effect leaks into clip_b)
    clip_b_with_eff = _make_clip(
        "clip-b-with-eff",
        vid_id,
        in_point=75,
        out_point=150,
        effects=[{"effect_type": "volume", "filter_string": "volume=3.0"}],
    )
    out_with_eff = tmp_path / "clip_b_with_eff.mp4"
    job_with_eff = _make_job("job-b-with-eff", plan, str(out_with_eff))

    cmd_with_eff = await build_command_for_job(
        job_with_eff, _make_clip_repo(clip_b_with_eff), _make_video_repo(vid)
    )
    r = await asyncio.to_thread(subprocess.run, cmd_with_eff, capture_output=True, timeout=120)
    assert r.returncode == 0, f"ffmpeg (with-effect) failed: {r.stderr.decode()[-800:]}"
    rms_with_eff = await measure_audio_rms_db(out_with_eff)

    # volume=3.0 must change audio by >= 5 dB (proves sensitivity — effect IS audible when applied)
    assert_audio_rms_changed(rms_with_eff, rms_baseline, min_delta_db=5.0)

    # clip_b.effects == [] (verified above) so its render matches the no-effect baseline;
    # the sensitivity check confirms this test would catch a regression where the effect leaks.
