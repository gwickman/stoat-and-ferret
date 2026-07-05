# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for generator clip (clip_type='generator') support — BL-441."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository


def _project(project_id: str = "proj-1") -> Project:
    now = datetime.now(timezone.utc)
    return Project(
        id=project_id,
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.api
async def test_create_generator_clip_accepts_no_source(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """POST /clips with clip_type=generator and generator_params succeeds."""
    await project_repository.add(_project())

    response = client.post(
        "/api/v1/projects/proj-1/clips",
        json={
            "clip_type": "generator",
            "generator_params": {"type": "sine", "frequency": 440},
            "in_point": 0,
            "out_point": 480,
            "timeline_position": 0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["clip_type"] == "generator"
    assert data["source_video_id"] is None
    assert data["generator_params"] == {"type": "sine", "frequency": 440}


@pytest.mark.api
async def test_create_generator_clip_rejects_missing_params(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """POST /clips with clip_type=generator but no generator_params returns 422."""
    await project_repository.add(_project())

    response = client.post(
        "/api/v1/projects/proj-1/clips",
        json={
            "clip_type": "generator",
            "in_point": 0,
            "out_point": 480,
            "timeline_position": 0,
        },
    )
    assert response.status_code == 422


@pytest.mark.api
async def test_create_file_clip_rejects_missing_source(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """POST /clips with clip_type=file but no source_video_id returns 422."""
    await project_repository.add(_project())

    response = client.post(
        "/api/v1/projects/proj-1/clips",
        json={
            "clip_type": "file",
            "in_point": 0,
            "out_point": 480,
            "timeline_position": 0,
        },
    )
    assert response.status_code == 422


@pytest.mark.api
async def test_generator_params_persist_round_trip(
    clip_repository: AsyncInMemoryClipRepository,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """Generator params survive store and fetch unchanged."""
    await project_repository.add(_project())
    now = datetime.now(timezone.utc)
    params = {"type": "aevalsrc", "expr": "sin(2*PI*440*t)", "duration": 5.0}
    clip = Clip(
        id="clip-gen-1",
        project_id="proj-1",
        source_video_id=None,
        clip_type="generator",
        generator_params=params,
        in_point=0,
        out_point=240,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip)
    fetched = await clip_repository.get("clip-gen-1")
    assert fetched is not None
    assert fetched.clip_type == "generator"
    assert fetched.generator_params == params
    assert fetched.source_video_id is None


@pytest.mark.api
def test_existing_file_clip_default_type(
    client: TestClient,
) -> None:
    """ClipResponse has clip_type='file' for legacy clips without explicit type."""
    from stoat_ferret.api.schemas.clip import ClipResponse

    now = datetime.now(timezone.utc)
    clip = Clip(
        id="c1",
        project_id="p1",
        source_video_id="v1",
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    resp = ClipResponse.model_validate(clip)
    assert resp.clip_type == "file"
    assert resp.source_video_id == "v1"


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="FFmpeg integration test — set STOAT_TEST_FFMPEG=1 to run",
)
def test_generator_clip_render_via_source_filter(tmp_path: object) -> None:
    """Generator sine clip renders to a valid WAV file via aevalsrc source filter."""
    import subprocess
    from pathlib import Path

    from stoat_ferret_core import build_generator_render_command

    params_json = '{"type": "sine", "frequency": 440.0}'
    duration = 0.1
    out = str(Path(str(tmp_path)) / "out.wav")  # type: ignore[arg-type]

    cmd = build_generator_render_command(params_json, duration, out)
    result = subprocess.run(
        ["ffmpeg"] + cmd.args(),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"FFmpeg failed: {result.stderr[-500:]}"
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0
