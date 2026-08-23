# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_restore_roundtrip — full create/save/modify/restore cycle.

BL-799 AC-5. Drives create → add track+clip → save version → add second clip →
restore → assert the live timeline equals the saved snapshot (same track count,
clip count, IDs). No FFmpeg required; exercised via ASGITransport (API/DB layer only).
"""

from __future__ import annotations

import os

import httpx
import pytest

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.api.settings import get_settings


@pytest.fixture
async def client(tmp_path: object) -> httpx.AsyncClient:
    """Isolated ASGI test client backed by a fresh SQLite database.

    Follows the same pattern as tests/smoke/conftest.py::smoke_client but is
    local to this acceptance test to avoid a cross-package fixture dependency.
    """
    from pathlib import Path

    base = Path(str(tmp_path))
    db_path = base / "roundtrip_test.db"

    orig_db = os.environ.get("STOAT_DATABASE_PATH")
    orig_thumb = os.environ.get("STOAT_THUMBNAIL_DIR")

    os.environ["STOAT_DATABASE_PATH"] = str(db_path)
    os.environ["STOAT_THUMBNAIL_DIR"] = str(base / "thumbnails")
    get_settings.cache_clear()

    app = create_app()
    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as c,
    ):
        yield c  # type: ignore[misc]

    if orig_db is None:
        os.environ.pop("STOAT_DATABASE_PATH", None)
    else:
        os.environ["STOAT_DATABASE_PATH"] = orig_db

    if orig_thumb is None:
        os.environ.pop("STOAT_THUMBNAIL_DIR", None)
    else:
        os.environ["STOAT_THUMBNAIL_DIR"] = orig_thumb

    get_settings.cache_clear()


async def test_uc_media_restore_roundtrip(client: httpx.AsyncClient) -> None:
    """Full restore roundtrip: create/save/modify/restore asserts live timeline == snapshot.

    Steps:
    1. POST /api/v1/projects — create project.
    2. PUT /api/v1/projects/{id}/timeline — create a video track.
    3. POST /api/v1/projects/{id}/clips — add first generator clip.
    4. POST /api/v1/projects/{id}/timeline/clips — place first clip on track.
    5. POST /api/v1/projects/{id}/versions — save version (auto-snapshot of live timeline).
    6. POST /api/v1/projects/{id}/clips — add second generator clip (modifies timeline).
    7. POST /api/v1/projects/{id}/timeline/clips — place second clip on track.
    8. Verify live timeline now has 2 clips (modification confirmed).
    9. POST /api/v1/projects/{id}/versions/{version}/restore — restore saved version.
    10. GET /api/v1/projects/{id}/timeline — assert live timeline == saved snapshot:
        - Track count and clip count match.
        - Track IDs and clip IDs match exactly.
    11. GET /api/v1/projects/{id}/versions — assert a new version row was created by restore.
    """
    # Step 1: Create project
    resp = await client.post("/api/v1/projects", json={"name": "Restore Roundtrip Project"})
    assert resp.status_code == 201, f"Project create failed: {resp.text}"
    project_id = resp.json()["id"]

    # Step 2: Create a timeline track
    resp = await client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[{"track_type": "video", "label": "V1"}],
    )
    assert resp.status_code == 200, f"Timeline PUT failed: {resp.text}"
    track_id: str = resp.json()["tracks"][0]["id"]

    # Step 3: Create first generator clip
    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "clip_type": "generator",
            "generator_params": {"type": "tone", "frequency": 440.0, "duration": 3.0},
            "in_point": 0,
            "out_point": 90,
            "timeline_position": 0,
        },
    )
    assert resp.status_code == 201, f"Clip 1 create failed: {resp.text}"
    clip1_id: str = resp.json()["id"]

    # Step 4: Place first clip on the timeline track
    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/clips",
        json={
            "clip_id": clip1_id,
            "track_id": track_id,
            "timeline_start": 0.0,
            "timeline_end": 3.0,
        },
    )
    assert resp.status_code == 201, f"Timeline clip 1 place failed: {resp.text}"

    # Step 5: Save version (body-less POST auto-snapshots the live timeline)
    resp = await client.post(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 201, f"Version save failed: {resp.text}"
    saved_version_number: int = resp.json()["version_number"]

    # Capture saved snapshot state
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    saved_timeline = resp.json()
    saved_track_ids = {t["id"] for t in saved_timeline["tracks"]}
    saved_clip_ids = {c["id"] for t in saved_timeline["tracks"] for c in t["clips"]}

    # Step 6: Add second generator clip to modify the live timeline
    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "clip_type": "generator",
            "generator_params": {"type": "tone", "frequency": 880.0, "duration": 3.0},
            "in_point": 0,
            "out_point": 90,
            "timeline_position": 0,
        },
    )
    assert resp.status_code == 201, f"Clip 2 create failed: {resp.text}"
    clip2_id: str = resp.json()["id"]

    # Step 7: Place second clip on the timeline track
    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/clips",
        json={
            "clip_id": clip2_id,
            "track_id": track_id,
            "timeline_start": 3.0,
            "timeline_end": 6.0,
        },
    )
    assert resp.status_code == 201, f"Timeline clip 2 place failed: {resp.text}"

    # Step 8: Verify timeline has 2 clips now (modification confirmed)
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    modified_clip_count = sum(len(t["clips"]) for t in resp.json()["tracks"])
    assert modified_clip_count == 2, (
        f"Expected 2 clips after modification, got {modified_clip_count}"
    )

    # Step 9: Restore the saved version
    resp = await client.post(
        f"/api/v1/projects/{project_id}/versions/{saved_version_number}/restore"
    )
    assert resp.status_code == 200, f"Restore failed: {resp.text}"
    restore_body = resp.json()
    assert restore_body["restored_version"] == saved_version_number

    # Step 10: Verify restored timeline matches saved snapshot (FR-001-AC-2)
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    restored_timeline = resp.json()

    assert len(restored_timeline["tracks"]) == len(saved_timeline["tracks"]), (
        f"Track count mismatch: restored={len(restored_timeline['tracks'])}"
        f" expected={len(saved_timeline['tracks'])}"
    )
    restored_clip_count = sum(len(t["clips"]) for t in restored_timeline["tracks"])
    saved_clip_count = sum(len(t["clips"]) for t in saved_timeline["tracks"])
    assert restored_clip_count == saved_clip_count, (
        f"Clip count mismatch: restored={restored_clip_count} expected={saved_clip_count}"
    )

    restored_track_ids = {t["id"] for t in restored_timeline["tracks"]}
    restored_clip_ids = {c["id"] for t in restored_timeline["tracks"] for c in t["clips"]}
    assert restored_track_ids == saved_track_ids, (
        f"Track IDs mismatch: restored={restored_track_ids} expected={saved_track_ids}"
    )
    assert restored_clip_ids == saved_clip_ids, (
        f"Clip IDs mismatch: restored={restored_clip_ids} expected={saved_clip_ids}"
    )

    # Step 11: Assert a new version row was created by restore (FR-001-AC-3)
    resp = await client.get(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 200
    versions_body = resp.json()
    assert versions_body["total"] >= 2, (
        f"Expected at least 2 versions after restore, got {versions_body['total']}"
    )
    version_numbers = {v["version_number"] for v in versions_body["versions"]}
    new_version = restore_body["new_version"]
    assert new_version in version_numbers, (
        f"New version {new_version} not found in version list {version_numbers}"
    )
