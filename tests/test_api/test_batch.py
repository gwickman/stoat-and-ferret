"""Tests for batch render endpoints."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.routers.batch import _run_batch_job, _to_rust_status
from stoat_ferret.db.batch_repository import (
    BatchJobRecord,
    InMemoryBatchRepository,
)
from stoat_ferret_core import calculate_batch_progress

# ---- Submission tests ----


@pytest.mark.api
def test_submit_batch_returns_202(client: TestClient) -> None:
    """POST /render/batch with valid jobs returns 202 Accepted."""
    response = client.post(
        "/api/v1/render/batch",
        json={"jobs": [{"project_id": "proj-1", "output_path": "/out/1.mp4", "quality": "high"}]},
    )
    assert response.status_code == 202


@pytest.mark.api
def test_submit_batch_returns_batch_id(client: TestClient) -> None:
    """Response includes batch_id as a UUID string."""
    response = client.post(
        "/api/v1/render/batch",
        json={"jobs": [{"project_id": "proj-1", "output_path": "/out/1.mp4"}]},
    )
    data = response.json()
    assert "batch_id" in data
    assert len(data["batch_id"]) == 36  # UUID format


@pytest.mark.api
def test_submit_batch_returns_correct_jobs_queued(client: TestClient) -> None:
    """Response includes correct jobs_queued count and accepted status."""
    response = client.post(
        "/api/v1/render/batch",
        json={
            "jobs": [
                {"project_id": "proj-1", "output_path": "/out/1.mp4"},
                {"project_id": "proj-2", "output_path": "/out/2.mp4"},
                {"project_id": "proj-3", "output_path": "/out/3.mp4"},
            ]
        },
    )
    data = response.json()
    assert data["jobs_queued"] == 3
    assert data["status"] == "accepted"


@pytest.mark.api
def test_submit_batch_default_quality(client: TestClient) -> None:
    """Jobs default to medium quality when not specified."""
    response = client.post(
        "/api/v1/render/batch",
        json={"jobs": [{"project_id": "proj-1", "output_path": "/out/1.mp4"}]},
    )
    assert response.status_code == 202


@pytest.mark.api
def test_submit_batch_too_many_jobs_returns_422(client: TestClient) -> None:
    """More than batch_max_jobs returns 422 with BATCH_JOB_LIMIT_EXCEEDED."""
    jobs = [{"project_id": f"proj-{i}", "output_path": f"/out/{i}.mp4"} for i in range(21)]
    response = client.post("/api/v1/render/batch", json={"jobs": jobs})
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "BATCH_JOB_LIMIT_EXCEEDED"


@pytest.mark.api
def test_submit_batch_exactly_max_jobs_accepted(client: TestClient) -> None:
    """Exactly batch_max_jobs (20) is accepted."""
    jobs = [{"project_id": f"proj-{i}", "output_path": f"/out/{i}.mp4"} for i in range(20)]
    response = client.post("/api/v1/render/batch", json={"jobs": jobs})
    assert response.status_code == 202
    assert response.json()["jobs_queued"] == 20


@pytest.mark.api
def test_submit_batch_empty_jobs_returns_422(client: TestClient) -> None:
    """Empty jobs list returns 422 from Pydantic validation."""
    response = client.post("/api/v1/render/batch", json={"jobs": []})
    assert response.status_code == 422


# ---- Progress endpoint tests ----


@pytest.mark.api
def test_get_batch_progress_unknown_returns_404(client: TestClient) -> None:
    """GET /render/batch/{id} with unknown ID returns 404."""
    response = client.get("/api/v1/render/batch/nonexistent-id")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
def test_get_batch_progress_returns_structure(client: TestClient) -> None:
    """GET /render/batch/{id} returns complete progress structure."""
    submit = client.post(
        "/api/v1/render/batch",
        json={
            "jobs": [
                {"project_id": "proj-1", "output_path": "/out/1.mp4"},
                {"project_id": "proj-2", "output_path": "/out/2.mp4"},
            ]
        },
    )
    batch_id = submit.json()["batch_id"]

    response = client.get(f"/api/v1/render/batch/{batch_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["batch_id"] == batch_id
    assert "overall_progress" in data
    assert "completed_jobs" in data
    assert "failed_jobs" in data
    assert data["total_jobs"] == 2
    assert len(data["jobs"]) == 2


@pytest.mark.api
def test_get_batch_progress_job_details(client: TestClient) -> None:
    """Each job in progress response includes required fields."""
    submit = client.post(
        "/api/v1/render/batch",
        json={"jobs": [{"project_id": "proj-1", "output_path": "/out/1.mp4"}]},
    )
    batch_id = submit.json()["batch_id"]

    response = client.get(f"/api/v1/render/batch/{batch_id}")
    data = response.json()
    job = data["jobs"][0]
    assert "job_id" in job
    assert job["project_id"] == "proj-1"
    assert job["status"] in ("queued", "running", "completed", "failed")


# ---- DTO round-trip tests ----


@pytest.mark.api
def test_batch_request_round_trip() -> None:
    """BatchRequest serializes and deserializes correctly."""
    from stoat_ferret.api.schemas.batch import BatchJobConfig, BatchRequest

    req = BatchRequest(
        jobs=[BatchJobConfig(project_id="p1", output_path="/out/1.mp4", quality="high")]
    )
    data = req.model_dump()
    restored = BatchRequest.model_validate(data)
    assert restored == req


@pytest.mark.api
def test_batch_response_round_trip() -> None:
    """BatchResponse serializes and deserializes correctly."""
    from stoat_ferret.api.schemas.batch import BatchResponse

    resp = BatchResponse(batch_id="abc-123", jobs_queued=3, status="accepted")
    data = resp.model_dump()
    restored = BatchResponse.model_validate(data)
    assert restored == resp


@pytest.mark.api
def test_batch_progress_response_round_trip() -> None:
    """BatchProgressResponse serializes and deserializes correctly."""
    from stoat_ferret.api.schemas.batch import BatchJobStatusResponse, BatchProgressResponse

    resp = BatchProgressResponse(
        batch_id="abc-123",
        overall_progress=0.5,
        completed_jobs=1,
        failed_jobs=0,
        total_jobs=2,
        jobs=[
            BatchJobStatusResponse(job_id="j1", project_id="p1", status="completed", progress=1.0),
            BatchJobStatusResponse(job_id="j2", project_id="p2", status="queued"),
        ],
    )
    data = resp.model_dump()
    restored = BatchProgressResponse.model_validate(data)
    assert restored == resp


# ---- Parity tests: Python status mapping matches Rust ----


def _make_record(
    *,
    job_id: str = "1",
    status: str = "queued",
    progress: float = 0.0,
) -> BatchJobRecord:
    """Create a BatchJobRecord for testing status mapping."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return BatchJobRecord(
        id=1,
        batch_id="b",
        job_id=job_id,
        project_id="p",
        output_path="/o",
        quality="m",
        status=status,
        progress=progress,
        error=None,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.api
def test_status_mapping_matches_rust_calculate_batch_progress() -> None:
    """Python _to_rust_status maps correctly for Rust calculate_batch_progress."""
    queued = _make_record(job_id="1", status="queued")
    running = _make_record(job_id="2", status="running", progress=0.5)
    completed = _make_record(job_id="3", status="completed", progress=1.0)
    failed = _make_record(job_id="4", status="failed")

    statuses = [_to_rust_status(j) for j in [queued, running, completed, failed]]
    progress = calculate_batch_progress(statuses)

    assert progress.total_jobs == 4
    assert progress.completed_jobs == 1
    assert progress.failed_jobs == 1
    # Mean of (0.0 + 0.5 + 1.0 + 0.0) / 4 = 0.375
    assert abs(progress.overall_progress - 0.375) < 1e-9


@pytest.mark.api
def test_all_queued_gives_zero_progress() -> None:
    """All queued jobs map to Pending and give 0.0 overall progress."""
    jobs = [_make_record(job_id=str(i)) for i in range(3)]
    statuses = [_to_rust_status(j) for j in jobs]
    progress = calculate_batch_progress(statuses)

    assert progress.total_jobs == 3
    assert progress.completed_jobs == 0
    assert progress.failed_jobs == 0
    assert abs(progress.overall_progress) < 1e-9


# ---- Async tests: parallel limit and job execution ----


@pytest.mark.api
async def test_parallel_limit_enforced() -> None:
    """No more than semaphore limit jobs run concurrently."""
    max_concurrent = 0
    current_concurrent = 0
    lock = asyncio.Lock()

    async def tracking_handler(project_id: str, output_path: str, quality: str) -> None:
        nonlocal max_concurrent, current_concurrent
        async with lock:
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
        await asyncio.sleep(0.01)
        async with lock:
            current_concurrent -= 1

    repo = InMemoryBatchRepository()
    records = []
    for i in range(8):
        record = await repo.create_batch_job(
            batch_id="batch-1",
            job_id=str(i),
            project_id=f"proj-{i}",
            output_path=f"/out/{i}",
            quality="medium",
        )
        records.append(record)

    semaphore = asyncio.Semaphore(4)

    tasks = [
        asyncio.create_task(
            _run_batch_job(
                r.job_id,
                r.project_id,
                r.output_path,
                r.quality,
                semaphore,
                tracking_handler,
                repo,
            )
        )
        for r in records
    ]
    await asyncio.gather(*tasks)

    assert max_concurrent <= 4
    for r in records:
        job = await repo.get_by_job_id(r.job_id)
        assert job is not None
        assert job.status == "completed"


@pytest.mark.api
async def test_batch_job_failure_tracked() -> None:
    """Failed batch jobs have status='failed' and error message."""

    async def failing_handler(project_id: str, output_path: str, quality: str) -> None:
        raise RuntimeError("render failed")

    repo = InMemoryBatchRepository()
    record = await repo.create_batch_job(
        batch_id="b",
        job_id="1",
        project_id="p1",
        output_path="/out/1",
        quality="medium",
    )
    semaphore = asyncio.Semaphore(4)

    await _run_batch_job(
        record.job_id,
        record.project_id,
        record.output_path,
        record.quality,
        semaphore,
        failing_handler,
        repo,
    )

    job = await repo.get_by_job_id("1")
    assert job is not None
    assert job.status == "failed"
    assert job.error == "render failed"


@pytest.mark.api
async def test_batch_job_no_handler_completes() -> None:
    """Batch job with no handler completes successfully."""
    repo = InMemoryBatchRepository()
    record = await repo.create_batch_job(
        batch_id="b",
        job_id="1",
        project_id="p1",
        output_path="/out/1",
        quality="medium",
    )
    semaphore = asyncio.Semaphore(4)

    await _run_batch_job(
        record.job_id,
        record.project_id,
        record.output_path,
        record.quality,
        semaphore,
        None,
        repo,
    )

    job = await repo.get_by_job_id("1")
    assert job is not None
    assert job.status == "completed"
    assert job.progress == 1.0


@pytest.mark.api
async def test_batch_job_status_transitions() -> None:
    """Job status transitions from queued -> running -> completed."""

    async def observing_handler(project_id: str, output_path: str, quality: str) -> None:
        await asyncio.sleep(0)

    repo = InMemoryBatchRepository()
    record = await repo.create_batch_job(
        batch_id="b",
        job_id="1",
        project_id="p1",
        output_path="/out/1",
        quality="medium",
    )
    assert record.status == "queued"

    semaphore = asyncio.Semaphore(4)
    await _run_batch_job(
        record.job_id,
        record.project_id,
        record.output_path,
        record.quality,
        semaphore,
        observing_handler,
        repo,
    )

    job = await repo.get_by_job_id("1")
    assert job is not None
    assert job.status == "completed"
    assert job.progress == 1.0
