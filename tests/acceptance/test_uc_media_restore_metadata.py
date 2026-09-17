# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_restore_metadata — restore preserves generator_params, effects,
source_asset_id (BL-842).

Tests that restore_version correctly propagates the three new fields from snapshot to live clips,
and that pre-v142 snapshots without these fields deserialize to None without error.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

import aiosqlite
import httpx
import pytest

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.api.settings import get_settings


@pytest.fixture
async def client(tmp_path: object) -> httpx.AsyncClient:
    """Isolated ASGI test client backed by a fresh SQLite database."""
    from pathlib import Path

    base = Path(str(tmp_path))
    db_path = base / "restore_metadata_test.db"

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


async def _setup_project_with_track(client: httpx.AsyncClient) -> tuple[str, str]:
    """Create a project with a single video track. Returns (project_id, track_id)."""
    resp = await client.post("/api/v1/projects", json={"name": "Restore Metadata Test"})
    assert resp.status_code == 201, f"Project create failed: {resp.text}"
    project_id = resp.json()["id"]

    resp = await client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[{"track_type": "video", "label": "V1"}],
    )
    assert resp.status_code == 200, f"Timeline PUT failed: {resp.text}"
    track_id: str = resp.json()["tracks"][0]["id"]

    return project_id, track_id


async def test_restore_preserves_generator_params(client: httpx.AsyncClient) -> None:
    """After restore, a generator clip's generator_params match the snapshot values.

    FR-001-AC-1 / BL-842-AC-1
    """
    project_id, track_id = await _setup_project_with_track(client)

    gen_params = {"type": "tone", "frequency": 440.0, "duration": 3.0, "lavfi_string": "sine=f=440"}

    # Create generator clip with generator_params
    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "clip_type": "generator",
            "generator_params": gen_params,
            "in_point": 0,
            "out_point": 90,
            "timeline_position": 0,
        },
    )
    assert resp.status_code == 201, f"Clip create failed: {resp.text}"
    clip_id = resp.json()["id"]

    # Place on timeline
    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/clips",
        json={"clip_id": clip_id, "track_id": track_id, "timeline_start": 0.0, "timeline_end": 3.0},
    )
    assert resp.status_code == 201, f"Timeline place failed: {resp.text}"

    # Save version (auto-snapshot)
    resp = await client.post(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 201, f"Version save failed: {resp.text}"
    saved_version = resp.json()["version_number"]

    # Fully delete the clip so restore can re-INSERT it from the snapshot
    # (DELETE /timeline/clips only detaches; the record stays in DB and conflicts on restore)
    resp = await client.delete(f"/api/v1/projects/{project_id}/clips/{clip_id}")
    assert resp.status_code == 204, f"Clip delete failed: {resp.text}"

    # Restore the saved version
    resp = await client.post(f"/api/v1/projects/{project_id}/versions/{saved_version}/restore")
    assert resp.status_code == 200, f"Restore failed: {resp.text}"

    # Verify restored timeline: generator_params matches saved values
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    timeline = resp.json()

    clips = [c for t in timeline["tracks"] for c in t["clips"]]
    assert len(clips) == 1, f"Expected 1 clip after restore, got {len(clips)}"
    restored_clip = clips[0]

    assert restored_clip["generator_params"] is not None, (
        "generator_params must not be None after restore"
    )
    assert restored_clip["generator_params"] == gen_params, (
        f"generator_params mismatch: got {restored_clip['generator_params']!r}, "
        f"expected {gen_params!r}"
    )


async def test_restore_preserves_effects(client: httpx.AsyncClient) -> None:
    """After restore from a snapshot containing effects, the clip's effects list is preserved.

    FR-001-AC-1 / BL-842-AC-1
    Uses a manually-crafted snapshot to target the restore path directly —
    effects are applied to clips via the effects endpoint separately from clip creation.
    """
    project_id, track_id = await _setup_project_with_track(client)

    effects_value = [{"effect_type": "volume", "parameters": {"volume": 0.5}}]
    clip_id = "effects-test-clip-id"

    # Craft a snapshot with effects on a generator clip
    snapshot_with_effects = {
        "project_id": project_id,
        "tracks": [
            {
                "id": track_id,
                "project_id": project_id,
                "track_type": "video",
                "label": "V1",
                "z_index": 0,
                "muted": False,
                "locked": False,
                "kind": None,
                "volume_envelope": None,
                "weight": 1.0,
                "clips": [
                    {
                        "id": clip_id,
                        "project_id": project_id,
                        "source_video_id": None,
                        "clip_type": "generator",
                        "track_id": track_id,
                        "timeline_start": 0.0,
                        "timeline_end": 3.0,
                        "in_point": 0,
                        "out_point": 90,
                        "generator_params": {"lavfi_string": "sine=f=440"},
                        "effects": effects_value,
                        "source_asset_id": None,
                    }
                ],
            }
        ],
        "duration": 3.0,
        "version": 1,
    }

    # Save the snapshot as a version
    resp = await client.post(
        f"/api/v1/projects/{project_id}/versions",
        json={"timeline_json": json.dumps(snapshot_with_effects)},
    )
    assert resp.status_code == 201, f"Version save failed: {resp.text}"
    saved_version = resp.json()["version_number"]

    # Restore
    resp = await client.post(f"/api/v1/projects/{project_id}/versions/{saved_version}/restore")
    assert resp.status_code == 200, f"Restore failed: {resp.text}"

    # Verify effects preserved through restore
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    clips = [c for t in timeline["tracks"] for c in t["clips"]]
    assert len(clips) == 1
    restored_clip = clips[0]

    assert restored_clip["effects"] == effects_value, (
        f"effects mismatch: got {restored_clip['effects']!r}, expected {effects_value!r}"
    )


async def test_restore_preserves_source_asset_id(client: httpx.AsyncClient) -> None:
    """After restore from a snapshot containing source_asset_id, the field is preserved.

    FR-001-AC-1 / BL-842-AC-1
    Seeds the assets table directly to satisfy the FK constraint on source_asset_id
    (the clips table has FOREIGN KEY (source_asset_id) REFERENCES assets (id)).
    """
    project_id, track_id = await _setup_project_with_track(client)

    # Seed an asset row directly (API requires file upload, FK requires a real row)
    db_path = os.environ["STOAT_DATABASE_PATH"]
    asset_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(db_path) as seed_conn:
        await seed_conn.execute(
            """INSERT INTO assets
               (id, original_filename, content_hash, mime_type, kind,
                size_bytes, file_path, deleted_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                asset_id,
                "test_image.png",
                f"sha256:fake-hash-{asset_id}",
                "image/png",
                "image",
                1024,
                "/tmp/test_image.png",
                None,
                now_iso,
                now_iso,
            ),
        )
        await seed_conn.commit()

    clip_id = str(uuid.uuid4())
    snapshot_with_asset = {
        "project_id": project_id,
        "tracks": [
            {
                "id": track_id,
                "project_id": project_id,
                "track_type": "video",
                "label": "V1",
                "z_index": 0,
                "muted": False,
                "locked": False,
                "kind": None,
                "volume_envelope": None,
                "weight": 1.0,
                "clips": [
                    {
                        "id": clip_id,
                        "project_id": project_id,
                        "source_video_id": None,
                        "clip_type": "image",
                        "track_id": track_id,
                        "timeline_start": 0.0,
                        "timeline_end": 3.0,
                        "in_point": 0,
                        "out_point": 90,
                        "generator_params": None,
                        "effects": None,
                        "source_asset_id": asset_id,
                    }
                ],
            }
        ],
        "duration": 3.0,
        "version": 1,
    }

    resp = await client.post(
        f"/api/v1/projects/{project_id}/versions",
        json={"timeline_json": json.dumps(snapshot_with_asset)},
    )
    assert resp.status_code == 201, f"Version save failed: {resp.text}"
    saved_version = resp.json()["version_number"]

    resp = await client.post(f"/api/v1/projects/{project_id}/versions/{saved_version}/restore")
    assert resp.status_code == 200, f"Restore failed: {resp.text}"

    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    clips = [c for t in timeline["tracks"] for c in t["clips"]]
    assert len(clips) == 1
    restored_clip = clips[0]

    assert restored_clip["source_asset_id"] == asset_id, (
        f"source_asset_id mismatch: got {restored_clip['source_asset_id']!r}, expected {asset_id!r}"
    )


async def test_restore_pre_v142_snapshot_none_defaults(client: httpx.AsyncClient) -> None:
    """Restoring a pre-v142 snapshot without the 3 new fields yields None defaults, no error.

    FR-001-AC-2 / BL-842-AC-1 (backward compat)
    """
    project_id, track_id = await _setup_project_with_track(client)

    # Craft a minimal pre-v142 snapshot JSON without generator_params/effects/source_asset_id
    pre_v142_snapshot = {
        "project_id": project_id,
        "tracks": [
            {
                "id": track_id,
                "project_id": project_id,
                "track_type": "video",
                "label": "V1",
                "z_index": 0,
                "muted": False,
                "locked": False,
                "kind": None,
                "volume_envelope": None,
                "weight": 1.0,
                "clips": [
                    {
                        "id": "pre-v142-clip-id",
                        "project_id": project_id,
                        "source_video_id": None,
                        "clip_type": "generator",
                        "track_id": track_id,
                        "timeline_start": 0.0,
                        "timeline_end": 3.0,
                        "in_point": 0,
                        "out_point": 90,
                        # no generator_params, effects, source_asset_id fields
                    }
                ],
            }
        ],
        "duration": 3.0,
        "version": 1,
    }

    # Save this pre-v142 snapshot directly via the versioned save endpoint
    resp = await client.post(
        f"/api/v1/projects/{project_id}/versions",
        json={"timeline_json": json.dumps(pre_v142_snapshot)},
    )
    assert resp.status_code == 201, f"Version save failed: {resp.text}"
    saved_version = resp.json()["version_number"]

    # Restore: must not raise an exception
    resp = await client.post(f"/api/v1/projects/{project_id}/versions/{saved_version}/restore")
    assert resp.status_code == 200, f"Restore of pre-v142 snapshot failed: {resp.text}"

    # Verify restored clips have None for the new fields (not an error)
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    clips = [c for t in timeline["tracks"] for c in t["clips"]]
    assert len(clips) == 1
    restored_clip = clips[0]

    assert restored_clip["generator_params"] is None, (
        "Expected generator_params=None for pre-v142 snapshot, "
        f"got {restored_clip['generator_params']!r}"
    )
    assert restored_clip["effects"] is None, (
        f"Expected effects=None for pre-v142 snapshot, got {restored_clip['effects']!r}"
    )
    assert restored_clip["source_asset_id"] is None, (
        "Expected source_asset_id=None for pre-v142 snapshot, "
        f"got {restored_clip['source_asset_id']!r}"
    )


@pytest.mark.skipif(
    not os.getenv("STOAT_TEST_FFMPEG"),
    reason="FFmpeg gate: requires STOAT_TEST_FFMPEG=1",
)
async def test_restore_generator_clip_renders_without_error(client: httpx.AsyncClient) -> None:
    """After restoring a version with a generator clip, render completes without CommandBuildError.

    FR-004-AC-1 / BL-842-AC-4
    """
    project_id, track_id = await _setup_project_with_track(client)

    gen_params = {"lavfi_string": "sine=frequency=440:duration=1"}

    # Create generator clip
    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "clip_type": "generator",
            "generator_params": gen_params,
            "in_point": 0,
            "out_point": 30,
            "timeline_position": 0,
        },
    )
    assert resp.status_code == 201, f"Clip create failed: {resp.text}"
    clip_id = resp.json()["id"]

    # Place on timeline
    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/clips",
        json={"clip_id": clip_id, "track_id": track_id, "timeline_start": 0.0, "timeline_end": 1.0},
    )
    assert resp.status_code == 201

    # Save version
    resp = await client.post(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 201
    saved_version = resp.json()["version_number"]

    # Remove clip and restore to verify generator_params survive round-trip
    resp = await client.delete(f"/api/v1/projects/{project_id}/clips/{clip_id}")
    assert resp.status_code == 204

    resp = await client.post(f"/api/v1/projects/{project_id}/versions/{saved_version}/restore")
    assert resp.status_code == 200, f"Restore failed: {resp.text}"

    # Trigger a render — must not produce CommandBuildError on generator_params path
    import asyncio

    resp = await client.post(
        "/api/v1/render",
        json={
            "project_id": project_id,
            "output_format": "mp4",
            "quality_preset": "draft",
            "render_plan": "{}",
        },
    )
    assert resp.status_code == 201, f"Render job create failed: {resp.text}"
    job_id = resp.json()["id"]

    # Poll for completion (max 60s)
    for _ in range(60):
        resp = await client.get(f"/api/v1/render/{job_id}")
        assert resp.status_code == 200
        job_status = resp.json()["status"]
        if job_status in ("completed", "failed"):
            break
        await asyncio.sleep(1.0)

    final_status = resp.json()["status"]
    error_msg = resp.json().get("error_message", "")

    assert final_status == "completed", (
        f"Render did not complete (status={final_status}, error={error_msg!r}). "
        "CommandBuildError may indicate generator_params not preserved through restore."
    )
