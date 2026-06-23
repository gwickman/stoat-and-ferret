# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for POST /api/v1/projects/{project_id}/clips/{clip_id}/split endpoint."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository

_PROJECT_ID = "proj-split-1"
_CLIP_ID = "clip-split-1"
_FPS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_project(project_id: str = _PROJECT_ID, output_fps: int = _FPS) -> Project:
    now = _now()
    return Project(
        id=project_id,
        name="Test Project",
        output_width=1920,
        output_height=1080,
        output_fps=output_fps,
        created_at=now,
        updated_at=now,
    )


def _make_clip(
    clip_id: str = _CLIP_ID,
    project_id: str = _PROJECT_ID,
    in_point: int = 0,
    out_point: int = 100,
    timeline_position: int = 0,
    timeline_start: float | None = None,
    timeline_end: float | None = None,
    effects: list[Any] | None = None,
) -> Clip:
    now = _now()
    return Clip(
        id=clip_id,
        project_id=project_id,
        source_video_id="video-1",
        in_point=in_point,
        out_point=out_point,
        timeline_position=timeline_position,
        timeline_start=timeline_start,
        timeline_end=timeline_end,
        effects=effects,
        created_at=now,
        updated_at=now,
    )


def _make_client(
    clip: Clip | None = None,
    project: Project | None = None,
    extra_projects: list[Project] | None = None,
) -> tuple[TestClient, AsyncInMemoryProjectRepository, AsyncInMemoryClipRepository]:
    """Create a TestClient with seeded project and clip for split tests."""
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()

    project_repo.seed([project or _make_project()])
    if extra_projects:
        project_repo.seed(extra_projects)

    clip_repo.seed([clip or _make_clip()])

    app = create_app(
        project_repository=project_repo,
        clip_repository=clip_repo,
    )
    return TestClient(app), project_repo, clip_repo


def _get(coro: Any) -> Any:
    """Run a coroutine synchronously using a fresh event loop."""
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.mark.api
def test_split_clip_valid_in_out_points() -> None:
    """FR-001-AC-1: Valid split sets clip_a.out_point==split_frame, clip_b.in_point==split_frame."""
    client, _, _ = _make_client(clip=_make_clip(in_point=0, out_point=100))

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={"split_frame": 40},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["clip_a"]["out_point"] == 40
    assert data["clip_b"]["in_point"] == 40


@pytest.mark.api
def test_split_clip_coverage_preserved() -> None:
    """FR-002-AC-1: clip_a.in_point == original.in_point; clip_b.out_point == original.out_point."""
    client, _, _ = _make_client(clip=_make_clip(in_point=10, out_point=90))

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={"split_frame": 50},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["clip_a"]["in_point"] == 10
    assert data["clip_b"]["out_point"] == 90


@pytest.mark.api
def test_split_clip_source_video_preserved() -> None:
    """FR-002-AC-2: Both clips preserve source_video_id from the original."""
    client, _, _ = _make_client()

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={"split_frame": 50},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["clip_a"]["source_video_id"] == "video-1"
    assert data["clip_b"]["source_video_id"] == "video-1"


@pytest.mark.api
def test_split_clip_timeline_times_propagated() -> None:
    """FR-002-AC-3: split_time_s = start + (split_frame - in_point) / fps."""
    # timeline_start=0.0, in_point=0, split at frame 30 at 30fps → split_time_s = 1.0
    clip = _make_clip(in_point=0, out_point=60, timeline_start=0.0, timeline_end=2.0)
    client, _, _ = _make_client(clip=clip, project=_make_project(output_fps=30))

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={"split_frame": 30},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["clip_a"]["timeline_start"] == pytest.approx(0.0)
    assert data["clip_a"]["timeline_end"] == pytest.approx(1.0)
    assert data["clip_b"]["timeline_start"] == pytest.approx(1.0)
    assert data["clip_b"]["timeline_end"] == pytest.approx(2.0)


@pytest.mark.api
def test_split_clip_timeline_none_propagation() -> None:
    """FR-002-AC-3: timeline_start is None → both split timeline fields remain None."""
    clip = _make_clip(in_point=0, out_point=100, timeline_start=None)
    client, _, _ = _make_client(clip=clip)

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={"split_frame": 50},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["clip_a"]["timeline_end"] is None
    assert data["clip_b"]["timeline_start"] is None


@pytest.mark.api
def test_split_clip_effects_empty() -> None:
    """FR-003-AC-1: Both resulting clips have empty effects lists."""
    existing_effects: list[Any] = [{"effect_type": "reverse", "filter_string": "reverse"}]
    clip = _make_clip(effects=existing_effects)
    client, _, _ = _make_client(clip=clip)

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={"split_frame": 50},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["clip_a"]["effects"] == []
    assert data["clip_b"]["effects"] == []


@pytest.mark.api
def test_split_clip_original_deleted() -> None:
    """NFR-001: Original clip is deleted after successful split."""
    client, _, clip_repo = _make_client()

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={"split_frame": 50},
        )
    assert resp.status_code == 200
    assert _get(clip_repo.get(_CLIP_ID)) is None


@pytest.mark.api
def test_split_clip_two_clips_created() -> None:
    """After split, exactly two new clips exist in the project."""
    client, _, clip_repo = _make_client()

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={"split_frame": 50},
        )
    assert resp.status_code == 200
    data = resp.json()
    clips = _get(clip_repo.list_by_project(_PROJECT_ID))
    assert len(clips) == 2
    ids = {c.id for c in clips}
    assert data["clip_a"]["id"] in ids
    assert data["clip_b"]["id"] in ids


@pytest.mark.api
def test_split_clip_invalid_split_frame_at_in_point() -> None:
    """FR-001-AC-2: split_frame == in_point → 422 with invalid_split_frame error."""
    client, _, _ = _make_client(clip=_make_clip(in_point=10, out_point=90))

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={"split_frame": 10},
        )
    assert resp.status_code == 422
    data = resp.json()
    assert data["detail"]["error"] == "invalid_split_frame"
    assert data["detail"]["valid_range"] == [11, 89]


@pytest.mark.api
def test_split_clip_invalid_split_frame_below_in_point() -> None:
    """FR-001-AC-2: split_frame < in_point → 422."""
    client, _, _ = _make_client(clip=_make_clip(in_point=10, out_point=90))

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={"split_frame": 5},
        )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "invalid_split_frame"


@pytest.mark.api
def test_split_clip_invalid_split_frame_at_out_point() -> None:
    """FR-001-AC-2: split_frame == out_point → 422."""
    client, _, _ = _make_client(clip=_make_clip(in_point=0, out_point=100))

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={"split_frame": 100},
        )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "invalid_split_frame"


@pytest.mark.api
def test_split_clip_missing_split_frame() -> None:
    """FR-001-AC-3: Missing split_frame → 422 from Pydantic validation."""
    client, _, _ = _make_client()

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={},
        )
    assert resp.status_code == 422


@pytest.mark.api
def test_split_clip_not_found() -> None:
    """FR-001-AC-4: Unknown clip_id → 404."""
    client, _, _ = _make_client()

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/nonexistent/split",
            json={"split_frame": 50},
        )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
def test_split_clip_wrong_project() -> None:
    """FR-001-AC-4: clip belonging to different project → 404."""
    now = _now()
    proj2 = Project(
        id="proj-2",
        name="Other Project",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    client, _, _ = _make_client(
        clip=_make_clip(project_id=_PROJECT_ID),
        extra_projects=[proj2],
    )

    with client:
        resp = client.post(
            f"/api/v1/projects/proj-2/clips/{_CLIP_ID}/split",
            json={"split_frame": 50},
        )
    assert resp.status_code == 404


@pytest.mark.api
def test_split_clip_effect_independence() -> None:
    """FR-003-AC-2: Each resulting clip has an independent empty effects list."""
    client, _, clip_repo = _make_client()

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={"split_frame": 50},
        )
    assert resp.status_code == 200
    data = resp.json()
    clip_a_id = data["clip_a"]["id"]
    clip_b_id = data["clip_b"]["id"]

    stored_a = _get(clip_repo.get(clip_a_id))
    stored_b = _get(clip_repo.get(clip_b_id))
    assert stored_a is not None
    assert stored_b is not None
    assert stored_a.id != stored_b.id
    assert stored_a.effects == [] or stored_a.effects is None
    assert stored_b.effects == [] or stored_b.effects is None


@pytest.mark.api
def test_split_clip_new_ids_assigned() -> None:
    """clip_a and clip_b have new IDs different from the original."""
    client, _, _ = _make_client()

    with client:
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={"split_frame": 50},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["clip_a"]["id"] != _CLIP_ID
    assert data["clip_b"]["id"] != _CLIP_ID
    assert data["clip_a"]["id"] != data["clip_b"]["id"]
