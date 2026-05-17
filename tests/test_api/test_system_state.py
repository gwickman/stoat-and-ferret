"""Tests for GET /api/v1/system/state endpoint (BL-275)."""

from __future__ import annotations

import copy
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.jobs.queue import InMemoryJobQueue, JobResult, JobStatus, _JobEntry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.render_repository import InMemoryRenderRepository


def _parse_iso(value: str) -> datetime:
    """Parse an ISO8601 timestamp, accepting the ``Z`` UTC suffix.

    Pydantic V2 serializes UTC datetimes with a trailing ``Z``; Python
    3.10's ``datetime.fromisoformat`` rejects that form (fixed in 3.11).
    Normalizing the suffix keeps the tests portable across the CI matrix.
    """
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@pytest.mark.api
def test_system_state_empty_snapshot_is_valid(client: TestClient) -> None:
    """Endpoint returns 200 with a well-formed payload when nothing is in flight."""
    response = client.get("/api/v1/system/state")
    assert response.status_code == 200

    data = response.json()
    assert data["active_jobs"] == []
    assert data["active_connections"] == 0
    assert isinstance(data["uptime_seconds"], float)
    # Timestamp is ISO8601 and parseable as UTC-aware datetime.
    parsed = _parse_iso(data["timestamp"])
    assert parsed.tzinfo is not None


@pytest.mark.api
def test_system_state_lists_submitted_jobs(
    client: TestClient,
    job_queue: InMemoryJobQueue,
) -> None:
    """Jobs tracked by the queue appear in active_jobs with matching fields.

    Fresh terminal jobs (age ≤ 300 s) remain visible; stale terminal jobs
    (age > 300 s) are pruned from active_jobs.
    """
    # Seed three fresh jobs in different states.
    for job_id, status in (
        ("job-pending", JobStatus.PENDING),
        ("job-running", JobStatus.RUNNING),
        ("job-complete", JobStatus.COMPLETE),
    ):
        entry = _JobEntry(job_id=job_id, job_type="scan", payload={})
        entry.result = JobResult(job_id=job_id, status=status, progress=0.5)
        job_queue._jobs[job_id] = entry

    # Seed a stale terminal job (submitted > 300 s ago) — must be absent.
    stale_entry = _JobEntry(job_id="job-stale", job_type="scan", payload={})
    stale_entry.submitted_at = datetime.now(timezone.utc) - timedelta(seconds=301)
    stale_entry.result = JobResult(job_id="job-stale", status=JobStatus.COMPLETE, progress=1.0)
    job_queue._jobs["job-stale"] = stale_entry

    response = client.get("/api/v1/system/state")
    assert response.status_code == 200

    data = response.json()
    by_id = {job["job_id"]: job for job in data["active_jobs"]}
    # Fresh terminal job appears; stale terminal job is pruned.
    assert set(by_id) == {"job-pending", "job-running", "job-complete"}
    assert "job-stale" not in by_id
    assert by_id["job-pending"]["status"] == "pending"
    assert by_id["job-running"]["status"] == "running"
    assert by_id["job-complete"]["status"] == "complete"
    for summary in data["active_jobs"]:
        assert summary["job_type"] == "scan"
        assert summary["progress"] == 0.5
        # submitted_at must round-trip through fromisoformat (with Z→+00:00).
        _parse_iso(summary["submitted_at"])


@pytest.mark.api
def test_system_state_reflects_live_scan_submission(
    client: TestClient,
    tmp_path: object,
) -> None:
    """A scan submitted via the API shows up in the next snapshot (FR-001, FR-004)."""
    submit = client.post(
        "/api/v1/videos/scan",
        json={"path": str(tmp_path)},
    )
    assert submit.status_code == 202
    job_id = submit.json()["job_id"]

    response = client.get("/api/v1/system/state")
    assert response.status_code == 200
    job_ids = [job["job_id"] for job in response.json()["active_jobs"]]
    assert job_id in job_ids


@pytest.mark.api
def test_system_state_reports_active_connections(client: TestClient) -> None:
    """active_connections reflects the ConnectionManager's active_connections."""
    ws_manager = client.app.state.ws_manager  # type: ignore[union-attr]
    # Simulate two open sockets without invoking the full accept() flow.
    ws_manager._connections.add(object())
    ws_manager._connections.add(object())

    response = client.get("/api/v1/system/state")
    assert response.status_code == 200
    assert response.json()["active_connections"] == 2


@pytest.mark.api
def test_system_state_timestamp_is_recent(client: TestClient) -> None:
    """The response timestamp is within a second of the request."""
    before = datetime.now(timezone.utc)
    response = client.get("/api/v1/system/state")
    after = datetime.now(timezone.utc)
    assert response.status_code == 200

    ts = _parse_iso(response.json()["timestamp"])
    assert before.replace(microsecond=0) <= ts <= after.replace(microsecond=999999)


@pytest.mark.api
def test_system_state_uptime_is_non_negative(client: TestClient) -> None:
    """Uptime is a non-negative float once the startup gate has opened."""
    response = client.get("/api/v1/system/state")
    assert response.status_code == 200
    assert response.json()["uptime_seconds"] >= 0.0


@pytest.mark.api
def test_system_state_handles_broken_job_queue(client: TestClient) -> None:
    """A raising job_queue yields an empty active_jobs list, not a 500 (NFR-003)."""

    class _BrokenQueue:
        def list_jobs(self) -> list[object]:
            raise RuntimeError("queue temporarily unavailable")

    client.app.state.job_queue = _BrokenQueue()  # type: ignore[union-attr]

    response = client.get("/api/v1/system/state")
    assert response.status_code == 200
    assert response.json()["active_jobs"] == []


@pytest.mark.api
def test_system_state_returns_under_500ms_with_many_jobs(
    client: TestClient,
    job_queue: InMemoryJobQueue,
) -> None:
    """Performance target FR-003: snapshot responds in <500ms with 100 queued jobs."""
    for i in range(100):
        jid = f"perf-job-{i:03d}"
        entry = _JobEntry(job_id=jid, job_type="scan", payload={})
        entry.result = JobResult(job_id=jid, status=JobStatus.RUNNING, progress=0.25)
        job_queue._jobs[jid] = entry

    start = time.perf_counter()
    response = client.get("/api/v1/system/state")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert len(response.json()["active_jobs"]) >= 100
    assert elapsed_ms < 500, f"snapshot latency {elapsed_ms:.1f}ms exceeded 500ms"


@pytest.mark.api
def test_system_state_includes_running_render_jobs(
    client: TestClient,
    render_repository: InMemoryRenderRepository,
) -> None:
    """RUNNING render jobs from render_repository appear in active_jobs."""
    render_job = RenderJob.create(
        project_id="proj-render-1",
        output_path="/tmp/out.mp4",
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan="{}",
    )
    render_job.status = RenderStatus.RUNNING
    render_repository._jobs[render_job.id] = copy.deepcopy(render_job)

    response = client.get("/api/v1/system/state")
    assert response.status_code == 200

    data = response.json()
    render_summaries = [j for j in data["active_jobs"] if j["job_type"] == "render"]
    assert len(render_summaries) == 1
    assert render_summaries[0]["job_id"] == render_job.id
    assert render_summaries[0]["status"] == "running"
    assert render_summaries[0]["progress"] == 0.0
    _parse_iso(render_summaries[0]["submitted_at"])


@pytest.mark.api
def test_system_state_excludes_terminal_render_jobs(
    client: TestClient,
    render_repository: InMemoryRenderRepository,
) -> None:
    """Terminal render jobs (COMPLETED/FAILED/CANCELLED) do not appear in active_jobs."""
    completed_job = RenderJob.create(
        project_id="proj-render-2",
        output_path="/tmp/done.mp4",
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan="{}",
    )
    completed_job.status = RenderStatus.COMPLETED
    render_repository._jobs[completed_job.id] = copy.deepcopy(completed_job)

    response = client.get("/api/v1/system/state")
    assert response.status_code == 200

    render_summaries = [j for j in response.json()["active_jobs"] if j["job_type"] == "render"]
    assert render_summaries == []


@pytest.mark.api
def test_system_state_render_repository_absent_valid(
    client: TestClient,
) -> None:
    """When render_repository is absent, response is valid with no render jobs."""
    client.app.state.render_repository = None  # type: ignore[union-attr]

    response = client.get("/api/v1/system/state")
    assert response.status_code == 200

    data = response.json()
    render_summaries = [j for j in data["active_jobs"] if j["job_type"] == "render"]
    assert render_summaries == []
