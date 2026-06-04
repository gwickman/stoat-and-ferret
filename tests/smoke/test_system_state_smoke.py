"""Smoke tests for system/state endpoint: terminal pruning and render visibility (BL-357).

Verifies:
- Stale terminal generic-queue jobs are excluded from active_jobs (BL-357-AC-2, FR-001).
- RUNNING/QUEUED render jobs appear in active_jobs with job_type="render" (BL-357-AC-1, FR-002).
- An agent can determine render terminal state via documented endpoints after a
  simulated disconnect without WebSocket access (BL-357-AC-5, FR-003).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from stoat_ferret.db.clip_repository import AsyncSQLiteClipRepository
from stoat_ferret.db.models import Clip
from stoat_ferret.jobs.queue import JobStatus, _AsyncJobEntry


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


async def test_stale_terminal_job_excluded_from_active_jobs(
    smoke_client: httpx.AsyncClient,
) -> None:
    """Stale COMPLETE generic-queue job (>300 s old) is excluded from active_jobs.

    Also verifies a fresh RUNNING job appears — confirming the pruning threshold is
    bounded, not a blanket exclusion (BL-357-AC-2, FR-001).
    """
    transport: httpx.ASGITransport = smoke_client._transport  # type: ignore[assignment]
    job_queue = transport.app.state.job_queue  # type: ignore[union-attr]

    # Seed a stale COMPLETE job (submitted > 300 s ago) — must be pruned
    stale = _AsyncJobEntry(job_id="stale-complete-sm-01", job_type="scan", payload={})
    stale.submitted_at = datetime.now(timezone.utc) - timedelta(seconds=301)
    stale.status = JobStatus.COMPLETE
    job_queue._jobs[stale.job_id] = stale

    # Seed a fresh RUNNING job — must remain visible
    fresh = _AsyncJobEntry(job_id="fresh-running-sm-01", job_type="scan", payload={})
    fresh.status = JobStatus.RUNNING
    job_queue._jobs[fresh.job_id] = fresh

    resp = await smoke_client.get("/api/v1/system/state")
    assert resp.status_code == 200

    active_ids = {job["job_id"] for job in resp.json()["active_jobs"]}
    assert stale.job_id not in active_ids, (
        f"Stale COMPLETE job ({stale.job_id}) must be pruned from active_jobs"
    )
    assert fresh.job_id in active_ids, (
        f"Fresh RUNNING job ({fresh.job_id}) must appear in active_jobs"
    )


async def test_running_render_job_included_in_active_jobs(
    smoke_client: httpx.AsyncClient,
) -> None:
    """RUNNING/QUEUED render appears in active_jobs with job_type='render' (BL-357-AC-1, FR-002).

    After cancellation the terminal render job must not appear in active_jobs.
    """
    # Create a project and seed a clip so the EMPTY_TIMELINE preflight passes
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Render Visibility Smoke Test"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]
    await _seed_clip_for_project(smoke_client, project_id)

    # Submit a render job with render_plan (total_duration required by worker; BL-371)
    render_resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": '{"total_duration": 10.0}'},
    )
    assert render_resp.status_code == 201
    job_id = render_resp.json()["id"]
    initial_status = render_resp.json()["status"]

    if initial_status in ("queued", "running"):
        # Active render must appear in system/state active_jobs with job_type="render"
        state_resp = await smoke_client.get("/api/v1/system/state")
        assert state_resp.status_code == 200
        render_entries = [j for j in state_resp.json()["active_jobs"] if j["job_id"] == job_id]
        assert len(render_entries) == 1, (
            f"QUEUED/RUNNING render job {job_id} must appear in active_jobs"
        )
        assert render_entries[0]["job_type"] == "render", (
            f"Expected job_type='render', got {render_entries[0]['job_type']!r}"
        )

        # Cancel to reach terminal state
        cancel_resp = await smoke_client.post(f"/api/v1/render/{job_id}/cancel")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

    # Terminal render job must not appear in active_jobs
    state_resp = await smoke_client.get("/api/v1/system/state")
    assert state_resp.status_code == 200
    active_render_ids = {
        j["job_id"] for j in state_resp.json()["active_jobs"] if j["job_type"] == "render"
    }
    assert job_id not in active_render_ids, (
        f"Terminal render job {job_id} must not appear in active_jobs"
    )


async def test_agent_can_determine_render_terminal_state_after_disconnect(
    smoke_client: httpx.AsyncClient,
) -> None:
    """Agent determines render terminal state via documented endpoints (BL-357-AC-5, FR-003).

    Simulates an agent that disconnects from WebSocket, then uses only
    GET /api/v1/system/state and GET /api/v1/render/{job_id} to determine
    the render job's terminal state — no WebSocket replay buffer accessed.
    """
    # Submit a render job
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "AC-5 Recovery Scenario"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]
    await _seed_clip_for_project(smoke_client, project_id)

    render_resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": '{"total_duration": 10.0}'},
    )
    assert render_resp.status_code == 201
    job_id = render_resp.json()["id"]

    # Simulate disconnect: cancel to reach terminal state without using WebSocket
    initial_status = render_resp.json()["status"]
    if initial_status in ("queued", "running"):
        cancel_resp = await smoke_client.post(f"/api/v1/render/{job_id}/cancel")
        assert cancel_resp.status_code == 200

    # Recovery step A: poll until the job is no longer in active_jobs (up to 5 s).
    # A fixed sleep is insufficient: in real-mode the render worker may race the cancel
    # on the shared SQLite connection, causing transient retry cycles before the job
    # reaches a durable terminal state (cancelled/failed after max retries).
    terminal_statuses = {"completed", "failed", "cancelled"}
    deadline = 5.0
    interval = 0.1
    elapsed = 0.0
    active_render_ids: set[str] = {job_id}  # assume active until proven otherwise
    while elapsed < deadline:
        state_resp = await smoke_client.get("/api/v1/system/state")
        assert state_resp.status_code == 200
        active_render_ids = {
            j["job_id"] for j in state_resp.json()["active_jobs"] if j["job_type"] == "render"
        }
        if job_id not in active_render_ids:
            break
        await asyncio.sleep(interval)
        elapsed += interval

    assert job_id not in active_render_ids, (
        f"Terminal render job {job_id} must not appear in system/state active_jobs "
        "after simulated disconnect"
    )

    # Recovery step B: terminal state is determinable via GET /api/v1/render/{job_id}
    get_resp = await smoke_client.get(f"/api/v1/render/{job_id}")
    assert get_resp.status_code == 200
    job_data = get_resp.json()
    assert job_data["status"] in terminal_statuses, (
        f"Render job status must be terminal; got {job_data['status']!r}. "
        "Agent cannot determine terminal state via GET /api/v1/render/{job_id}."
    )
