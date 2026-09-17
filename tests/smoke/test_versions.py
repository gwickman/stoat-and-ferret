# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke tests for project version listing, creation, and restore.

Validates listing, creating, and restoring project versions through the
full HTTP stack.
"""

from __future__ import annotations

import httpx
import pytest

from stoat_ferret.api.settings import get_settings


async def test_version_list_empty_project(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/projects/{id}/versions returns 200 with empty list for new project."""
    client = smoke_client

    # Create a project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Version Smoke Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # List versions — new project has no versions
    resp = await client.get(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["versions"] == []
    assert body["limit"] == 20
    assert body["offset"] == 0


async def test_version_create_and_list(smoke_client: httpx.AsyncClient) -> None:
    """POST creates a version snapshot, verify via subsequent GET in the version list."""
    client = smoke_client

    # Create a project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Version Create Smoke Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Create a version via POST
    resp = await client.post(
        f"/api/v1/projects/{project_id}/versions",
        json={"timeline_json": '{"clips": [1, 2, 3]}'},
    )
    assert resp.status_code == 201
    version_data = resp.json()
    assert version_data["version_number"] == 1
    assert "checksum" in version_data
    assert "created_at" in version_data

    # Verify the version appears in GET list
    resp = await client.get(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["versions"]) == 1
    assert body["versions"][0]["version_number"] == 1
    assert body["versions"][0]["checksum"] == version_data["checksum"]


async def test_version_list_nonexistent_project(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/projects/{id}/versions returns 404 for nonexistent project."""
    resp = await smoke_client.get("/api/v1/projects/nonexistent-id/versions")
    assert resp.status_code == 404


async def test_version_restore(smoke_client: httpx.AsyncClient) -> None:
    """POST restore returns 200 and replaces live timeline with saved snapshot."""
    client = smoke_client

    # Create a project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Version Restore Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Snapshot version 1 via auto-snapshot (empty timeline)
    resp = await client.post(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 201

    # Restore version 1
    resp = await client.post(
        f"/api/v1/projects/{project_id}/versions/1/restore",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["restored_version"] == 1
    assert body["new_version"] == 2
    assert "message" in body

    # Live timeline reflects the restored snapshot (empty)
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    assert resp.json()["tracks"] == []


async def test_version_restore_not_found(smoke_client: httpx.AsyncClient) -> None:
    """POST restore for nonexistent version returns 404."""
    client = smoke_client

    # Create a project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Version Restore 404 Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Restore nonexistent version 999
    resp = await client.post(
        f"/api/v1/projects/{project_id}/versions/999/restore",
    )
    assert resp.status_code == 404


async def test_version_restore_nonexistent_project(
    smoke_client: httpx.AsyncClient,
) -> None:
    """POST restore for nonexistent project returns 404."""
    resp = await smoke_client.post(
        "/api/v1/projects/nonexistent-id/versions/1/restore",
    )
    assert resp.status_code == 404


async def test_version_default_retains_all(smoke_client: httpx.AsyncClient) -> None:
    """Default (no retention config) retains all versions."""
    client = smoke_client

    resp = await client.post("/api/v1/projects", json={"name": "Retain All Project"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    for i in range(5):
        resp = await client.post(
            f"/api/v1/projects/{project_id}/versions",
            json={"timeline_json": f'{{"v": {i + 1}}}'},
        )
        assert resp.status_code == 201

    resp = await client.get(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 200
    assert resp.json()["total"] == 5


async def test_version_retention_prunes(
    tmp_path: object,
    request: pytest.FixtureRequest,
    smoke_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retention count prunes old versions through the full stack."""
    client = smoke_client

    # Set retention and refresh settings
    monkeypatch.setenv("STOAT_VERSION_RETENTION_COUNT", "2")
    request.addfinalizer(get_settings.cache_clear)
    get_settings.cache_clear()

    resp = await client.post("/api/v1/projects", json={"name": "Retention Prune Project"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    for i in range(4):
        resp = await client.post(
            f"/api/v1/projects/{project_id}/versions",
            json={"timeline_json": f'{{"v": {i + 1}}}'},
        )
        assert resp.status_code == 201

    resp = await client.get(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["versions"][0]["version_number"] == 4
    assert body["versions"][1]["version_number"] == 3


async def test_version_save_no_body_list_restore_round_trip(
    smoke_client: httpx.AsyncClient,
) -> None:
    """Body-less POST snapshot → list → restore round-trip works end-to-end."""
    client = smoke_client

    # Create a project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Version Round-Trip Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Step 1 — Save: body-less POST auto-snapshots the live timeline
    resp = await client.post(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 201
    snapshot = resp.json()
    assert snapshot["version_number"] == 1
    assert snapshot["checksum"]

    # Step 2 — List: version appears in listing
    resp = await client.get(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["versions"][0]["version_number"] == 1
    assert body["versions"][0]["checksum"] == snapshot["checksum"]

    # Step 3 — Restore: live-restore creates a new version and replaces live timeline
    resp = await client.post(
        f"/api/v1/projects/{project_id}/versions/{snapshot['version_number']}/restore"
    )
    assert resp.status_code == 200
    restore_body = resp.json()
    assert restore_body["restored_version"] == 1
    assert restore_body["new_version"] == 2

    # Live timeline reflects the restored snapshot (empty)
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    assert resp.json()["tracks"] == []

    # Confirm two versions exist after restore
    resp = await client.get(f"/api/v1/projects/{project_id}/versions")
    assert resp.json()["total"] == 2


async def test_version_retention_keep_more_than_total(
    request: pytest.FixtureRequest,
    smoke_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """keep_count > total versions is a no-op."""
    client = smoke_client

    monkeypatch.setenv("STOAT_VERSION_RETENTION_COUNT", "10")
    request.addfinalizer(get_settings.cache_clear)
    get_settings.cache_clear()

    resp = await client.post("/api/v1/projects", json={"name": "Keep More Project"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    for i in range(3):
        resp = await client.post(
            f"/api/v1/projects/{project_id}/versions",
            json={"timeline_json": f'{{"v": {i + 1}}}'},
        )
        assert resp.status_code == 201

    resp = await client.get(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 200
    assert resp.json()["total"] == 3


async def test_create_version_with_no_body(smoke_client: httpx.AsyncClient) -> None:
    """POST /versions with no body returns 201 with an auto-snapshot (BL-404-AC-1).

    The response exposes version_number and checksum; the checksum is the
    SHA-256 of the auto-snapshotted timeline data, confirming the server
    performed the snapshot server-side.
    """
    resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Version No Body Test"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    resp = await smoke_client.post(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 201
    version = resp.json()
    assert version["version_number"] == 1
    assert version["checksum"]  # non-empty SHA-256 hex digest proves auto-snapshot


async def test_restore_preserves_clip_metadata_smoke(
    smoke_client: httpx.AsyncClient,
) -> None:
    """Restored clip retains generator_params from the saved snapshot (BL-842).

    Creates a generator clip with specific params, saves a version, adds a second
    clip with different params to mutate the live timeline, restores version 1,
    and asserts the original clip's generator_params are non-null and match the
    saved snapshot value.
    """
    client = smoke_client
    params_v1 = {"type": "tone", "frequency": 440.0, "duration": 3.0}

    # Create project and a video track
    resp = await client.post("/api/v1/projects", json={"name": "Restore Metadata Smoke"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    resp = await client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[{"track_type": "video", "label": "V1"}],
    )
    assert resp.status_code == 200
    track_id: str = resp.json()["tracks"][0]["id"]

    # Create generator clip with params_v1 and place it on the track
    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "clip_type": "generator",
            "generator_params": params_v1,
            "in_point": 0,
            "out_point": 90,
            "timeline_position": 0,
        },
    )
    assert resp.status_code == 201
    clip1_id: str = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/clips",
        json={
            "clip_id": clip1_id,
            "track_id": track_id,
            "timeline_start": 0.0,
            "timeline_end": 3.0,
        },
    )
    assert resp.status_code == 201

    # Save version 1 (snapshot captures clip1 with params_v1)
    resp = await client.post(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 201
    version_number: int = resp.json()["version_number"]

    # Mutate the live timeline: add a second clip with different generator_params
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
    assert resp.status_code == 201

    # Restore version 1
    resp = await client.post(f"/api/v1/projects/{project_id}/versions/{version_number}/restore")
    assert resp.status_code == 200

    # Restored timeline must contain clip1 with the original params_v1 (not null)
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    restored_clips = [c for t in timeline["tracks"] for c in t["clips"]]
    clip1_data = next((c for c in restored_clips if c["id"] == clip1_id), None)
    assert clip1_data is not None, "Clip 1 must be present in restored timeline"
    assert clip1_data["generator_params"] is not None, (
        "generator_params must not be None after restore"
    )
    assert clip1_data["generator_params"] == params_v1, (
        f"Restored generator_params {clip1_data['generator_params']!r} "
        f"must match saved snapshot {params_v1!r}"
    )


async def test_restore_removes_unplaced_clips_smoke(
    smoke_client: httpx.AsyncClient,
) -> None:
    """Unplaced clips absent from GET /clips after restore (BL-844).

    Creates an unplaced clip (not on any track), saves a version without the clip
    on any track, restores that version, and asserts the unplaced clip is absent.
    """
    client = smoke_client

    # Create project (no tracks — version snapshot will have empty timeline)
    resp = await client.post("/api/v1/projects", json={"name": "Restore Unplaced Smoke"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Create an unplaced clip (not placed on any track)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "clip_type": "generator",
            "generator_params": {"type": "tone", "frequency": 440.0, "duration": 2.0},
            "in_point": 0,
            "out_point": 60,
            "timeline_position": 0,
        },
    )
    assert resp.status_code == 201
    unplaced_clip_id: str = resp.json()["id"]

    # Save version 1 — the unplaced clip is not part of any track snapshot
    resp = await client.post(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 201
    version_number = resp.json()["version_number"]

    # Confirm the unplaced clip is visible before restore
    resp = await client.get(f"/api/v1/projects/{project_id}/clips")
    assert resp.status_code == 200
    clip_ids_before = {c["id"] for c in resp.json()["clips"]}
    assert unplaced_clip_id in clip_ids_before, (
        "Unplaced clip must be visible via GET /clips before restore"
    )

    # Restore version 1
    resp = await client.post(f"/api/v1/projects/{project_id}/versions/{version_number}/restore")
    assert resp.status_code == 200

    # Unplaced clip must be absent after restore
    resp = await client.get(f"/api/v1/projects/{project_id}/clips")
    assert resp.status_code == 200
    clip_ids_after = {c["id"] for c in resp.json()["clips"]}
    assert unplaced_clip_id not in clip_ids_after, (
        f"Unplaced clip {unplaced_clip_id} must be absent after restore"
    )
