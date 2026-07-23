# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for render evidence API redaction and access control (BL-554).

Verifies:
- GET /render/{job_id}/evidence returns 403 when STOAT_RENDER_EVIDENCE_FULL_ACCESS is disabled
- GET /render/{job_id}/evidence returns 200 + evidence when enabled
- sk-or-v1-* API keys are redacted from command_args
- STOAT_* env-derived values are redacted from command_args
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import stoat_ferret.api.routers.render as render_router
from stoat_ferret.api.app import create_app
from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.render.checkpoints import RenderCheckpointManager
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import RenderService

TEST_JOB_ID = "evid-job-001"


def _make_settings(*, evidence_enabled: bool = False) -> Settings:
    return Settings(render_mode="noop", render_evidence_full_access=evidence_enabled)


def _enable_evidence(monkeypatch: pytest.MonkeyPatch, *, enabled: bool = True) -> None:
    """Patch get_settings in the render router to control evidence access."""
    monkeypatch.setattr(
        render_router, "get_settings", lambda: _make_settings(evidence_enabled=enabled)
    )


def _make_job(evidence_json: str | None = None) -> RenderJob:
    now = datetime.now(timezone.utc)
    return RenderJob(
        id=TEST_JOB_ID,
        project_id="proj-001",
        status=RenderStatus.COMPLETED,
        output_path="/data/renders/out.mp4",
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=json.dumps({"total_duration": 5.0, "settings": {}}),
        progress=1.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=now,
        evidence_json=evidence_json,
    )


def _build_app(render_repo: InMemoryRenderRepository) -> FastAPI:
    """Build a minimal test app; callers patch render_router.get_settings."""
    ws = MagicMock(spec=ConnectionManager)
    checkpoint_mgr = MagicMock(spec=RenderCheckpointManager)
    settings = Settings(render_mode="noop")
    service = RenderService(
        repository=render_repo,
        queue=RenderQueue(render_repo),
        executor=MagicMock(spec=RenderExecutor),
        checkpoint_manager=checkpoint_mgr,
        connection_manager=ws,
        settings=settings,
    )
    return create_app(
        render_repository=render_repo,
        render_service=service,
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
    )


_FAKE_EVIDENCE = {
    "command_args": ["ffmpeg", "-i", "input.mp4", "-c:v", "libx264", "/data/renders/out.mp4"],
    "exit_code": 0,
    "stderr_tail": "frame=150 fps=30 q=28.0 size=1024kB time=00:00:05.00 bitrate=1677.7kbits/s",
    "output_path": "/data/renders/out.mp4",
    "output_size_bytes": 1048576,
    "filter_script_path": None,
}


async def test_evidence_endpoint_returns_403_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /render/{job_id}/evidence returns 403 when STOAT_RENDER_EVIDENCE_FULL_ACCESS is false."""
    _enable_evidence(monkeypatch, enabled=False)

    repo = InMemoryRenderRepository()
    job = _make_job(evidence_json=json.dumps(_FAKE_EVIDENCE))
    await repo.create(job)

    app = _build_app(repo)
    with TestClient(app) as client:
        resp = client.get(f"/api/v1/render/{TEST_JOB_ID}/evidence")

    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["code"] == "EVIDENCE_ACCESS_DISABLED"


async def test_evidence_endpoint_returns_200_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /render/{job_id}/evidence returns 200 + evidence when access is enabled."""
    _enable_evidence(monkeypatch)

    repo = InMemoryRenderRepository()
    job = _make_job(evidence_json=json.dumps(_FAKE_EVIDENCE))
    await repo.create(job)

    app = _build_app(repo)
    with TestClient(app) as client:
        resp = client.get(f"/api/v1/render/{TEST_JOB_ID}/evidence")

    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == TEST_JOB_ID
    assert body["exit_code"] == 0
    assert body["output_size_bytes"] == 1048576
    assert "command_args" in body
    assert isinstance(body["command_args"], list)


def test_evidence_endpoint_returns_404_for_unknown_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /render/{job_id}/evidence returns 404 for non-existent job."""
    _enable_evidence(monkeypatch)

    repo = InMemoryRenderRepository()
    app = _build_app(repo)
    with TestClient(app) as client:
        resp = client.get("/api/v1/render/nonexistent-job/evidence")

    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


async def test_evidence_endpoint_returns_404_when_no_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /render/{job_id}/evidence returns 404 when evidence_json is None."""
    _enable_evidence(monkeypatch)

    repo = InMemoryRenderRepository()
    job = _make_job(evidence_json=None)
    await repo.create(job)

    app = _build_app(repo)
    with TestClient(app) as client:
        resp = client.get(f"/api/v1/render/{TEST_JOB_ID}/evidence")

    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "EVIDENCE_NOT_FOUND"


async def test_sk_api_key_redacted_from_command_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """sk-or-v1-* API keys in command_args are replaced with [REDACTED] (BL-554-AC-4)."""
    _enable_evidence(monkeypatch)

    evidence = {
        **_FAKE_EVIDENCE,
        "command_args": [
            "ffmpeg",
            "-headers",
            "sk-or-v1-fake-openrouter-api-key",
            "-i",
            "input.mp4",
            "/data/renders/out.mp4",
        ],
    }
    repo = InMemoryRenderRepository()
    job = _make_job(evidence_json=json.dumps(evidence))
    await repo.create(job)

    app = _build_app(repo)
    with TestClient(app) as client:
        resp = client.get(f"/api/v1/render/{TEST_JOB_ID}/evidence")

    assert resp.status_code == 200
    args = resp.json()["command_args"]
    # sk-or-v1-fake-openrouter-api-key must NOT appear in the response
    assert not any("sk-or-v1" in arg for arg in args), f"API key leaked in command_args: {args}"
    # [REDACTED] must appear in place of the key
    assert "[REDACTED]" in args


async def test_stoat_env_var_value_redacted_from_command_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """STOAT_* env var values in command_args are replaced with [REDACTED] (BL-554-AC-4)."""
    secret_value = "stoat-secret-token-xyz"
    monkeypatch.setenv("STOAT_FAKE_SECRET", secret_value)
    _enable_evidence(monkeypatch)

    evidence = {
        **_FAKE_EVIDENCE,
        "command_args": [
            "ffmpeg",
            "-i",
            "input.mp4",
            "-metadata",
            secret_value,
            "/data/renders/out.mp4",
        ],
    }
    repo = InMemoryRenderRepository()
    job = _make_job(evidence_json=json.dumps(evidence))
    await repo.create(job)

    app = _build_app(repo)
    with TestClient(app) as client:
        resp = client.get(f"/api/v1/render/{TEST_JOB_ID}/evidence")

    assert resp.status_code == 200
    args = resp.json()["command_args"]
    # secret_value must NOT appear in the response
    assert secret_value not in args, f"STOAT_ secret leaked in command_args: {args}"
    assert "[REDACTED]" in args


async def test_non_sensitive_args_are_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-sensitive command args are passed through unchanged."""
    _enable_evidence(monkeypatch)

    evidence = {
        **_FAKE_EVIDENCE,
        "command_args": ["ffmpeg", "-i", "input.mp4", "-c:v", "libx264", "/data/renders/out.mp4"],
    }
    repo = InMemoryRenderRepository()
    job = _make_job(evidence_json=json.dumps(evidence))
    await repo.create(job)

    app = _build_app(repo)
    with TestClient(app) as client:
        resp = client.get(f"/api/v1/render/{TEST_JOB_ID}/evidence")

    assert resp.status_code == 200
    args = resp.json()["command_args"]
    assert args == ["ffmpeg", "-i", "input.mp4", "-c:v", "libx264", "/data/renders/out.mp4"]
