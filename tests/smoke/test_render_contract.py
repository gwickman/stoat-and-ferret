"""Smoke tests verifying render_plan contract end-to-end (BL-371, BL-372).

Validates:
- render_plan.total_duration is derived from timeline.duration (BL-371-AC-1, AC-2)
- Multiple projects preserve distinct render_plan.total_duration values
- 422 is returned when render_plan.total_duration is absent in noop mode (negative test)
- 4xx responses carry structured detail with a message field (BL-372-AC-1 backend assertion)
- Noop render returns 201 and job appears in render queue (BL-371-AC-1, AC-3)
- Job status polling shows completed state immediately in noop mode (BL-371-AC-3)
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import httpx
import pytest

from stoat_ferret.db.clip_repository import AsyncSQLiteClipRepository
from stoat_ferret.db.models import Clip


async def _seed_stub_clip(client: httpx.AsyncClient, project_id: str) -> str:
    """Insert a stub clip row bypassing video validation. Returns the clip id.

    Uses a placeholder source_video_id (00000000-...-0001) so the EMPTY_TIMELINE
    render preflight passes without requiring a real video scan.
    """
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
    return clip.id


async def _create_project_with_timeline(
    client: httpx.AsyncClient,
    project_name: str,
    timeline_end: float,
) -> tuple[str, float]:
    """Create a project with a single clip spanning [0, timeline_end] seconds.

    Returns (project_id, timeline_end). The timeline duration returned by
    GET /api/v1/projects/{project_id}/timeline will equal timeline_end.
    """
    resp = await client.post("/api/v1/projects", json={"name": project_name})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    clip_id = await _seed_stub_clip(client, project_id)

    resp = await client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[{"track_type": "video", "label": "V1"}],
    )
    assert resp.status_code == 200
    track_id = resp.json()["tracks"][0]["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/clips",
        json={
            "clip_id": clip_id,
            "track_id": track_id,
            "timeline_start": 0.0,
            "timeline_end": timeline_end,
        },
    )
    assert resp.status_code == 201

    return project_id, timeline_end


async def test_render_plan_construction_from_timeline(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Render plan total_duration matches the project's timeline duration.

    Creates a project with a 100s timeline, GETs the timeline to read
    duration, submits a render with render_plan.total_duration == duration,
    and asserts 201 in noop mode.
    """
    project_id, expected_duration = await _create_project_with_timeline(
        smoke_client_noop, "Render Plan Construction Test", 100.0
    )

    timeline_resp = await smoke_client_noop.get(f"/api/v1/projects/{project_id}/timeline")
    assert timeline_resp.status_code == 200
    timeline_duration = timeline_resp.json()["duration"]
    assert timeline_duration == pytest.approx(expected_duration)

    render_plan = json.dumps({"total_duration": timeline_duration})
    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": render_plan},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "completed"


async def test_render_plan_multiple_projects(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Distinct projects produce distinct render_plan.total_duration values.

    Creates two projects with different timeline durations (100s, 200s)
    and verifies both render calls succeed with their respective durations.
    """
    project_id_a, duration_a = await _create_project_with_timeline(
        smoke_client_noop, "Project A - 100s", 100.0
    )
    project_id_b, duration_b = await _create_project_with_timeline(
        smoke_client_noop, "Project B - 200s", 200.0
    )

    assert duration_a != duration_b

    resp_a = await smoke_client_noop.post(
        "/api/v1/render",
        json={
            "project_id": project_id_a,
            "render_plan": json.dumps({"total_duration": duration_a}),
        },
    )
    assert resp_a.status_code == 201
    assert resp_a.json()["status"] == "completed"

    resp_b = await smoke_client_noop.post(
        "/api/v1/render",
        json={
            "project_id": project_id_b,
            "render_plan": json.dumps({"total_duration": duration_b}),
        },
    )
    assert resp_b.status_code == 201
    assert resp_b.json()["status"] == "completed"


async def test_render_422_without_render_plan(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Omitting total_duration in noop mode returns 422 PREFLIGHT_FAILED.

    Negative test: verifies the guard that prevents renders without a
    valid render_plan.total_duration. This confirms that the positive tests
    above are actually exercising the guard, not bypassing it.
    """
    resp = await smoke_client_noop.post("/api/v1/projects", json={"name": "Render 422 Test"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]
    await _seed_stub_clip(smoke_client_noop, project_id)

    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": json.dumps({})},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["code"] == "PREFLIGHT_FAILED"
    assert "total_duration" in body["detail"]["message"]


async def test_error_response_detail_message(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """4xx render responses carry structured detail with a non-empty message field.

    Verifies that the backend emits detail as a dict (not a plain string or
    object) so the frontend can safely extract detail.message without hitting
    the 'Objects are not valid as a React child' invariant (BL-372-AC-1 backend
    assertion — frontend display verified by Feature 002 unit tests).
    """
    resp = await smoke_client_noop.post("/api/v1/projects", json={"name": "Error Detail Test"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]
    await _seed_stub_clip(smoke_client_noop, project_id)

    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": json.dumps({})},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert isinstance(body["detail"], dict), (
        "detail must be a dict so frontend can extract detail.message safely"
    )
    assert "code" in body["detail"]
    assert "message" in body["detail"]
    assert isinstance(body["detail"]["message"], str)
    assert len(body["detail"]["message"]) > 0


async def test_error_response_missing_detail(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Non-existent project returns 404 with structured detail.code and detail.message.

    Verifies the fallback path: when render_plan is present but the project
    doesn't exist, the response still has a structured error (not a missing-
    detail scenario). The 'detail absent' case on the frontend falls back to
    HTTP status text (verified by Feature 002 unit tests).
    """
    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={
            "project_id": "00000000-0000-0000-0000-000000000000",
            "render_plan": json.dumps({"total_duration": 5.0}),
        },
    )
    assert resp.status_code == 404
    body = resp.json()
    assert isinstance(body["detail"], dict)
    assert "code" in body["detail"]
    assert "message" in body["detail"]


async def test_noop_render_success(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Noop render returns 201 and the new job appears in the render queue.

    Satisfies BL-371-AC-1 (returns 201, not 422) and BL-371-AC-3 (job visible
    in queue) for the backend smoke test contract.
    """
    project_id, duration = await _create_project_with_timeline(
        smoke_client_noop, "Noop Render Success", 50.0
    )

    render_plan = json.dumps({"total_duration": duration})
    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": render_plan},
    )
    assert resp.status_code == 201
    body = resp.json()
    job_id = body["id"]
    assert body["status"] == "completed"

    list_resp = await smoke_client_noop.get("/api/v1/render")
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    assert list_body["total"] >= 1
    job_ids = [item["id"] for item in list_body["items"]]
    assert job_id in job_ids, f"Submitted job {job_id} not found in render queue (items: {job_ids})"


async def test_job_polling_noop_completed(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Job status polling shows completed state immediately in noop mode.

    Satisfies BL-371-AC-3: job status re-fetch reports completed. In noop mode
    the job is synchronously marked completed, so polling should see it
    immediately or within one 0.1s sleep.
    """
    project_id, duration = await _create_project_with_timeline(
        smoke_client_noop, "Noop Polling Test", 30.0
    )

    render_plan = json.dumps({"total_duration": duration})
    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": render_plan},
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    # Poll until completed; timeout = 10s per NFR-002
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 10.0
    final_status: str | None = None
    while loop.time() < deadline:
        get_resp = await smoke_client_noop.get(f"/api/v1/render/{job_id}")
        assert get_resp.status_code == 200
        final_status = get_resp.json()["status"]
        if final_status == "completed":
            break
        await asyncio.sleep(0.1)

    assert final_status == "completed", (
        f"Expected 'completed' status after polling, got {final_status!r}"
    )
