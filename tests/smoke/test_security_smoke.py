# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke tests verifying BL-699 (scan path confinement) and BL-700 (concurrent waiter) fixes.

FR-001: Scan path confinement — test_scan_rejects_out_of_root_path asserts 403 for paths
outside allowed_scan_roots; test_scan_accepts_valid_path confirms the happy path is intact.

FR-002: Concurrent job completion — test_concurrent_waiters_both_receive_completion submits
a noop render job and asserts two concurrent pollers both receive terminal status.

All tests run without FFmpeg (STOAT_TEST_FFMPEG not required).
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.api.settings import get_settings
from stoat_ferret.db.clip_repository import AsyncSQLiteClipRepository
from stoat_ferret.db.models import Clip
from tests.smoke.conftest import poll_job_until_terminal

_STUB_VIDEO_ID = "00000000-0000-0000-0000-000000000001"


async def _ensure_stub_video(db: object) -> None:
    """Insert a stub video row required as FK parent for stub clips."""
    now_str = datetime.now(timezone.utc).isoformat()
    await db.execute(  # type: ignore[union-attr]
        "INSERT OR IGNORE INTO videos "
        "(id, path, filename, duration_frames, frame_rate_numerator, frame_rate_denominator, "
        "width, height, video_codec, file_size, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            _STUB_VIDEO_ID,
            "/stub/video.mp4",
            "video.mp4",
            100,
            30,
            1,
            1920,
            1080,
            "h264",
            1000,
            now_str,
            now_str,
        ),
    )
    await db.commit()  # type: ignore[union-attr]


async def _seed_clip_for_project(client: httpx.AsyncClient, project_id: str) -> None:
    """Insert a stub clip so the EMPTY_TIMELINE preflight passes."""
    transport: httpx.ASGITransport = client._transport  # type: ignore[assignment]
    db = transport.app.state.db  # type: ignore[union-attr]
    await _ensure_stub_video(db)
    repo = AsyncSQLiteClipRepository(db)
    now = datetime.now(timezone.utc)
    clip = Clip(
        id=Clip.new_id(),
        project_id=project_id,
        source_video_id=_STUB_VIDEO_ID,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await repo.add(clip)


@pytest.fixture()
async def smoke_client_confined(tmp_path: Path) -> tuple[httpx.AsyncClient, Path]:
    """Async client with STOAT_ALLOWED_SCAN_ROOTS set to a single subdirectory of tmp_path.

    Yields:
        Tuple of (client, scan_root) where scan_root is the only allowed directory.
    """
    db_path = tmp_path / "confined_smoke_test.db"
    scan_root = tmp_path / "scan_root"
    scan_root.mkdir()

    orig_db = os.environ.get("STOAT_DATABASE_PATH")
    orig_thumb = os.environ.get("STOAT_THUMBNAIL_DIR")
    orig_roots = os.environ.get("STOAT_ALLOWED_SCAN_ROOTS")

    os.environ["STOAT_DATABASE_PATH"] = str(db_path)
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")
    os.environ["STOAT_ALLOWED_SCAN_ROOTS"] = json.dumps([str(scan_root)])
    get_settings.cache_clear()

    app = create_app()

    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client,
    ):
        yield client, scan_root

    for key, orig in [
        ("STOAT_DATABASE_PATH", orig_db),
        ("STOAT_THUMBNAIL_DIR", orig_thumb),
        ("STOAT_ALLOWED_SCAN_ROOTS", orig_roots),
    ]:
        if orig is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = orig

    get_settings.cache_clear()


async def test_scan_rejects_out_of_root_path(
    smoke_client_confined: tuple[httpx.AsyncClient, Path],
) -> None:
    """POST /api/v1/videos/scan with out-of-root path returns 403 PATH_NOT_ALLOWED (BL-699)."""
    client, scan_root = smoke_client_confined
    resp = await client.post(
        "/api/v1/videos/scan",
        json={"path": str(scan_root.parent), "recursive": False},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PATH_NOT_ALLOWED"


async def test_scan_accepts_valid_path(
    smoke_client_confined: tuple[httpx.AsyncClient, Path],
) -> None:
    """POST /api/v1/videos/scan with in-root path returns 202 and queues a job (BL-699)."""
    client, scan_root = smoke_client_confined
    resp = await client.post(
        "/api/v1/videos/scan",
        json={"path": str(scan_root), "recursive": False},
    )
    assert resp.status_code == 202
    assert "job_id" in resp.json()


async def test_concurrent_waiters_both_receive_completion(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Two concurrent pollers on same job_id both receive terminal status without hanging.

    Verifies BL-700 fix: per-job Event set allows concurrent waiters to unblock independently.
    """
    client = smoke_client_noop

    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Concurrent Waiters BL-700 Smoke"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]
    await _seed_clip_for_project(client, project_id)

    render_plan = json.dumps({"total_duration": 5.0, "settings": {}})
    resp = await client.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": render_plan},
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    result1, result2 = await asyncio.gather(
        poll_job_until_terminal(client, job_id),
        poll_job_until_terminal(client, job_id),
    )

    terminal_statuses = {"completed", "failed", "timeout", "cancelled"}
    assert result1["status"].lower() in terminal_statuses
    assert result2["status"].lower() in terminal_statuses
