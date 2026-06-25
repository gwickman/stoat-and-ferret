# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for render preflight validation (BL-551).

Covers multi-clip rejection, per-clip effects warning, single-clip no-effects
pass, and zero-byte output failure marking.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.render.checkpoints import RenderCheckpointManager
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import RenderService

TEST_PROJECT_UUID = "11111111-1111-1111-1111-111111111111"

_RENDER_PLAN = json.dumps({"total_duration": 10.0, "settings": {"quality_preset": "medium"}})


def _make_project() -> Project:
    now = datetime.now(timezone.utc)
    return Project(
        id=TEST_PROJECT_UUID,
        name="Test Project",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )


def _make_clip(*, effects: list[dict[str, Any]] | None = None, clip_id: str = "clip-1") -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=TEST_PROJECT_UUID,
        source_video_id="vid-test",
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
        effects=effects,
    )


def _make_noop_service(render_repo: InMemoryRenderRepository) -> RenderService:
    ws = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock()
    checkpoint_mgr = MagicMock(spec=RenderCheckpointManager)
    checkpoint_mgr.cleanup_stale = AsyncMock(return_value=0)
    return RenderService(
        repository=render_repo,
        queue=RenderQueue(render_repo),
        executor=MagicMock(spec=RenderExecutor),
        checkpoint_manager=checkpoint_mgr,
        connection_manager=ws,
        settings=Settings(render_mode="noop"),
    )


def _build_app(clips: list[Clip], render_repo: InMemoryRenderRepository | None = None) -> FastAPI:
    project_repo = AsyncInMemoryProjectRepository()
    project_repo.seed([_make_project()])
    clip_repo = AsyncInMemoryClipRepository()
    clip_repo.seed(clips)
    if render_repo is None:
        render_repo = InMemoryRenderRepository()
    render_service = _make_noop_service(render_repo)
    return create_app(
        render_repository=render_repo,
        render_service=render_service,
        project_repository=project_repo,
        clip_repository=clip_repo,
    )


# ---------- Tests ----------


def test_single_clip_no_effects() -> None:
    """Single-clip project with no effects passes preflight with 201 and no warnings."""
    app = _build_app([_make_clip()])
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/render",
            json={
                "project_id": TEST_PROJECT_UUID,
                "render_plan": _RENDER_PLAN,
            },
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["warnings"] is None


def test_multi_clip_rejected() -> None:
    """Multi-clip project returns 422 with MULTI_CLIP_NOT_SUPPORTED code."""
    clips = [_make_clip(clip_id="clip-1"), _make_clip(clip_id="clip-2")]
    app = _build_app(clips)
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/render",
            json={
                "project_id": TEST_PROJECT_UUID,
                "render_plan": _RENDER_PLAN,
            },
        )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "MULTI_CLIP_NOT_SUPPORTED"
    assert "Multi-clip" in detail["message"]


def test_single_clip_with_effects_warns() -> None:
    """Single-clip project with per-clip effects returns 201 and non-empty warnings[]."""
    effects = [{"type": "blur", "params": {"radius": 5}}]
    app = _build_app([_make_clip(effects=effects)])
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/render",
            json={
                "project_id": TEST_PROJECT_UUID,
                "render_plan": _RENDER_PLAN,
            },
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["warnings"] is not None
    assert len(body["warnings"]) > 0
    assert any("effect" in w.lower() for w in body["warnings"])


async def test_zero_byte_output() -> None:
    """Zero-byte FFmpeg output causes job to be marked failed."""
    render_repo = InMemoryRenderRepository()
    ws = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock()
    checkpoint_mgr = MagicMock(spec=RenderCheckpointManager)
    checkpoint_mgr.cleanup_stale = AsyncMock(return_value=0)
    executor = MagicMock(spec=RenderExecutor)

    service = RenderService(
        repository=render_repo,
        queue=RenderQueue(render_repo),
        executor=executor,
        checkpoint_manager=checkpoint_mgr,
        connection_manager=ws,
        settings=Settings(render_mode="real", render_retry_count=0),
    )

    # Create a job manually
    job = RenderJob.create(
        project_id=TEST_PROJECT_UUID,
        output_path="/tmp/fake_zero_byte_output.mp4",
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=_RENDER_PLAN,
    )
    await render_repo.create(job)
    # Persist so _handle_failure can read it
    await render_repo.update_status(job.id, RenderStatus.RUNNING)

    # Simulate FFmpeg returning success=True but output file is absent/zero-byte
    executor.execute = AsyncMock(return_value=True)
    executor._progress_callback = None
    executor._cleanup_temp_files = MagicMock()
    service._output_file_ok = MagicMock(return_value=False)  # type: ignore[method-assign]

    await service.run_job(job, ["ffmpeg", "-i", "input.mp4", "/tmp/fake_zero_byte_output.mp4"])

    updated = await render_repo.get(job.id)
    assert updated is not None
    assert updated.status == RenderStatus.FAILED
    assert updated.error_message is not None
    msg = updated.error_message.lower()
    assert "zero-byte" in msg or "missing" in msg
