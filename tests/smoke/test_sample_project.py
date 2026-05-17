"""Regression smoke test for the Running Montage sample project (BL-128, BL-239).

Validates that the complete sample project structure — project metadata,
clip frame values, and effect-to-clip mappings — matches canonical definitions,
and that a render job can be queued for the sample project.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.api.settings import get_settings
from stoat_ferret.db.clip_repository import AsyncSQLiteClipRepository
from stoat_ferret.db.models import Clip
from tests.smoke.conftest import SAMPLE_EFFECT_DEFS


async def _seed_clip_for_project(client: httpx.AsyncClient, project_id: str) -> None:
    """Insert a stub clip row so the EMPTY_TIMELINE preflight passes."""
    transport: httpx.ASGITransport = client._transport  # type: ignore[assignment]
    db = transport.app.state.db  # type: ignore[union-attr]
    repo = AsyncSQLiteClipRepository(db)
    now = datetime.now(timezone.utc)
    clip = Clip(
        id=Clip.new_id(),
        project_id=project_id,
        source_video_id="00000000-0000-0000-0000-000000000001",
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await repo.add(clip)


async def test_sample_project_structure(
    smoke_client: httpx.AsyncClient,
    sample_project: dict[str, Any],
) -> None:
    """Verify the Running Montage sample project matches canonical definitions.

    Asserts project metadata (name, output settings), clip count and frame
    values, source video associations, effect-to-clip mappings, and render
    job queueing (BL-239).
    """
    client = smoke_client
    project_id = sample_project["project_id"]
    project = sample_project["project"]

    # --- FR-002: Project metadata ---
    assert project["name"] == "Running Montage"
    assert project["output_width"] == 1280
    assert project["output_height"] == 720
    assert project["output_fps"] == 30

    # --- FR-003 & FR-004: Clip assertions ---
    resp = await client.get(f"/api/v1/projects/{project_id}/clips")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 4

    # Sort clips by timeline_position for deterministic ordering
    clips = sorted(body["clips"], key=lambda c: c["timeline_position"])

    # Canonical frame values: (video_index, in_point, out_point, timeline_position)
    expected_frame_values = [
        (0, 60, 300, 0),
        (1, 90, 540, 300),
        (2, 30, 360, 750),
        (3, 150, 450, 1080),
    ]

    expected_videos = [
        "78888-568004778_medium.mp4",
        "running1.mp4",
        "running2.mp4",
        "81872-577880797_medium.mp4",
    ]

    # Map video IDs to filenames for source video assertions
    resp = await client.get("/api/v1/videos?limit=100")
    videos = resp.json()["videos"]
    id_to_filename = {v["id"]: v["filename"] for v in videos}

    for i, clip in enumerate(clips):
        vid_idx, in_pt, out_pt, tl_pos = expected_frame_values[i]

        assert clip["in_point"] == in_pt, (
            f"Clip {i} in_point: expected {in_pt}, got {clip['in_point']}"
        )
        assert clip["out_point"] == out_pt, (
            f"Clip {i} out_point: expected {out_pt}, got {clip['out_point']}"
        )
        assert clip["timeline_position"] == tl_pos, (
            f"Clip {i} timeline_position: expected {tl_pos}, got {clip['timeline_position']}"
        )

        # Source video association
        filename = id_to_filename[clip["source_video_id"]]
        assert filename == expected_videos[vid_idx], (
            f"Clip {i} source video: expected {expected_videos[vid_idx]}, got {filename}"
        )

    # --- FR-005: Effect assertions ---
    # Build expected effect map: clip_index -> list of (effect_type, key params)
    expected_effects: dict[int, list[tuple[str, dict[str, Any]]]] = {}
    for clip_idx, effect_type, params in SAMPLE_EFFECT_DEFS:
        expected_effects.setdefault(clip_idx, []).append((effect_type, params))

    for i, clip in enumerate(clips):
        clip_effects = clip.get("effects") or []
        if i in expected_effects:
            expected = expected_effects[i]
            assert len(clip_effects) == len(expected), (
                f"Clip {i}: expected {len(expected)} effects, got {len(clip_effects)}"
            )
            # Sort both by effect_type for stable comparison
            actual_sorted = sorted(clip_effects, key=lambda e: e["effect_type"])
            expected_sorted = sorted(expected, key=lambda e: e[0])
            for actual, (exp_type, _exp_params) in zip(actual_sorted, expected_sorted, strict=True):
                assert actual["effect_type"] == exp_type, (
                    f"Clip {i}: expected effect {exp_type}, got {actual['effect_type']}"
                )
        else:
            assert len(clip_effects) == 0, f"Clip {i}: expected no effects, got {len(clip_effects)}"

    # --- BL-239: Render job queueing ---
    # Asserts status=="queued" only — the render background worker
    # (RenderQueue.dequeue) is not wired to FastAPI lifespan, so jobs remain
    # queued indefinitely in test mode. Output file existence is not asserted.
    # See BL-239 design investigation (comms/outbox/versions/design/v034/).
    render_resp = await client.post(
        "/api/v1/render",
        json={"project_id": project_id},
    )
    assert render_resp.status_code == 201
    render_data = render_resp.json()
    assert render_data["status"] == "queued"
    assert render_data["id"]  # non-empty string


@pytest.fixture()
async def smoke_client_noop(tmp_path: Path) -> httpx.AsyncClient:
    """ASGI client with STOAT_RENDER_MODE=noop for noop-mode render tests."""
    db_path = tmp_path / "noop_test.db"

    orig_db = os.environ.get("STOAT_DATABASE_PATH")
    orig_thumb = os.environ.get("STOAT_THUMBNAIL_DIR")
    orig_render_mode = os.environ.get("STOAT_RENDER_MODE")

    os.environ["STOAT_DATABASE_PATH"] = str(db_path)
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")
    os.environ["STOAT_RENDER_MODE"] = "noop"
    get_settings.cache_clear()

    app = create_app()

    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client,
    ):
        yield client

    for key, orig in [
        ("STOAT_DATABASE_PATH", orig_db),
        ("STOAT_THUMBNAIL_DIR", orig_thumb),
        ("STOAT_RENDER_MODE", orig_render_mode),
    ]:
        if orig is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = orig

    get_settings.cache_clear()


async def test_seed_render_plan_noop_completion(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Render job with FFmpeg-vocab render_plan reaches COMPLETED in noop mode (FR-002, BL-340).

    Mirrors the render submission the seed script performs: quality_preset uses
    FFmpeg vocabulary (medium) and render_plan includes total_duration.
    In noop mode the render service short-circuits synchronously, so the job
    status in the API response must be 'completed'.
    """
    client = smoke_client_noop

    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Seed Noop Test Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]
    await _seed_clip_for_project(client, project_id)

    render_plan = {
        "settings": {"quality_preset": "medium"},  # FFmpeg vocabulary
        "total_duration": 46.0,
    }

    resp = await client.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": json.dumps(render_plan)},
    )
    assert resp.status_code == 201
    render_data = resp.json()
    assert render_data["status"] == "completed", (
        f"Expected 'completed' in noop mode, got {render_data['status']!r}"
    )
    assert render_data["id"]
