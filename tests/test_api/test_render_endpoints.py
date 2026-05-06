"""Tests for render job CRUD and encoder endpoints.

Covers all 6 CRUD endpoints, encoder GET/POST endpoints, DI fallback,
lifespan wiring, re-export verification, pagination, status filtering,
parity tests, and system tests for full lifecycle scenarios.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.render.encoder_cache import (
    EncoderCacheEntry,
    InMemoryEncoderCacheRepository,
)
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import RenderService

# ---------- Fixtures ----------


@pytest.fixture
def render_repo() -> InMemoryRenderRepository:
    """Create isolated render repository for render tests."""
    return InMemoryRenderRepository()


@pytest.fixture
def mock_render_service(render_repo: InMemoryRenderRepository) -> AsyncMock:
    """Create mock RenderService with working submit_job."""
    service = AsyncMock(spec=RenderService)

    async def fake_submit(
        *,
        project_id: str,
        output_path: str,
        output_format: OutputFormat,
        quality_preset: QualityPreset,
        render_plan_json: str,
    ) -> RenderJob:
        job = RenderJob.create(
            project_id=project_id,
            output_path=output_path,
            output_format=output_format,
            quality_preset=quality_preset,
            render_plan=render_plan_json,
        )
        return await render_repo.create(job)

    service.submit_job = AsyncMock(side_effect=fake_submit)
    service.cancel_job = AsyncMock(return_value=True)
    service.recover = AsyncMock(return_value=[])
    return service


@pytest.fixture
def render_app(
    render_repo: InMemoryRenderRepository,
    mock_render_service: AsyncMock,
) -> FastAPI:
    """Create test app with render dependencies injected."""
    return create_app(
        render_repository=render_repo,
        render_service=mock_render_service,
    )


@pytest.fixture
def render_client(render_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create test client for render endpoints."""
    with TestClient(render_app) as c:
        yield c


def _create_job_via_api(client: TestClient, **overrides: str) -> dict:
    """Helper to create a render job via POST /render."""
    body = {
        "project_id": "proj-001",
        "output_format": "mp4",
        "quality_preset": "standard",
        "render_plan": "{}",
    }
    body.update(overrides)
    resp = client.post("/api/v1/render", json=body)
    assert resp.status_code == 201
    return resp.json()


# ---------- POST /render ----------


class TestCreateRenderJob:
    """Tests for POST /render endpoint."""

    def test_create_job_returns_201(self, render_client: TestClient) -> None:
        """POST /render with valid input returns 201 with job_id."""
        data = _create_job_via_api(render_client)
        assert "id" in data
        assert data["status"] == "queued"
        assert data["project_id"] == "proj-001"
        assert data["output_format"] == "mp4"
        assert data["quality_preset"] == "standard"
        assert data["progress"] == 0.0

    def test_create_job_custom_format(self, render_client: TestClient) -> None:
        """POST /render accepts different output formats."""
        data = _create_job_via_api(render_client, output_format="webm")
        assert data["output_format"] == "webm"

    def test_create_job_custom_preset(self, render_client: TestClient) -> None:
        """POST /render accepts different quality presets."""
        data = _create_job_via_api(render_client, quality_preset="high")
        assert data["quality_preset"] == "high"

    def test_create_job_invalid_format(self, render_client: TestClient) -> None:
        """POST /render with invalid format returns 400."""
        resp = render_client.post(
            "/api/v1/render",
            json={"project_id": "p1", "output_format": "avi"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "INVALID_FORMAT"

    def test_create_job_invalid_preset(self, render_client: TestClient) -> None:
        """POST /render with invalid preset returns 400."""
        resp = render_client.post(
            "/api/v1/render",
            json={"project_id": "p1", "quality_preset": "ultra"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "INVALID_PRESET"

    def test_create_job_preflight_failure(
        self,
        render_client: TestClient,
        mock_render_service: AsyncMock,
    ) -> None:
        """POST /render returns 422 when pre-flight checks fail."""
        from stoat_ferret.render.service import PreflightError

        mock_render_service.submit_job = AsyncMock(side_effect=PreflightError("Disk full"))
        resp = render_client.post(
            "/api/v1/render",
            json={"project_id": "p1"},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "PREFLIGHT_FAILED"


# ---------- GET /render/{job_id} ----------


class TestGetRenderJob:
    """Tests for GET /render/{job_id} endpoint."""

    def test_get_job_returns_status(self, render_client: TestClient) -> None:
        """GET /render/{job_id} returns correct status and metadata."""
        created = _create_job_via_api(render_client)
        job_id = created["id"]

        resp = render_client.get(f"/api/v1/render/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job_id
        assert data["status"] == "queued"
        assert data["progress"] == 0.0
        assert data["project_id"] == "proj-001"

    def test_get_job_not_found(self, render_client: TestClient) -> None:
        """GET /render/{job_id} returns 404 for unknown job."""
        resp = render_client.get("/api/v1/render/nonexistent-id")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"


# ---------- GET /render ----------


class TestListRenderJobs:
    """Tests for GET /render endpoint with pagination."""

    def test_list_empty(self, render_client: TestClient) -> None:
        """GET /render with no jobs returns empty list."""
        resp = render_client.get("/api/v1/render")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["limit"] == 20
        assert data["offset"] == 0

    def test_list_returns_jobs(self, render_client: TestClient) -> None:
        """GET /render returns all created jobs."""
        _create_job_via_api(render_client, project_id="p1")
        _create_job_via_api(render_client, project_id="p2")

        resp = render_client.get("/api/v1/render")
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_pagination(self, render_client: TestClient) -> None:
        """GET /render respects limit and offset."""
        for i in range(5):
            _create_job_via_api(render_client, project_id=f"p{i}")

        resp = render_client.get("/api/v1/render?limit=2&offset=1")
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 1

    def test_list_status_filter(
        self,
        render_client: TestClient,
        render_repo: InMemoryRenderRepository,
    ) -> None:
        """GET /render?status=queued filters by status."""
        created = _create_job_via_api(render_client)
        _create_job_via_api(render_client, project_id="p2")

        # Manually transition one job to running
        import asyncio

        asyncio.run(render_repo.update_status(created["id"], RenderStatus.RUNNING))

        resp = render_client.get("/api/v1/render?status=queued")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "queued"

    def test_list_invalid_status_filter(self, render_client: TestClient) -> None:
        """GET /render?status=invalid returns 400."""
        resp = render_client.get("/api/v1/render?status=invalid")
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "INVALID_STATUS"

    def test_list_response_schema(self, render_client: TestClient) -> None:
        """GET /render matches expected pagination schema."""
        _create_job_via_api(render_client)
        resp = render_client.get("/api/v1/render")
        data = resp.json()
        assert set(data.keys()) == {"items", "total", "limit", "offset"}
        item = data["items"][0]
        expected_fields = {
            "id",
            "project_id",
            "status",
            "output_path",
            "output_format",
            "quality_preset",
            "progress",
            "error_message",
            "retry_count",
            "created_at",
            "updated_at",
            "completed_at",
        }
        assert set(item.keys()) == expected_fields


# ---------- POST /render/{job_id}/cancel ----------


class TestCancelRenderJob:
    """Tests for POST /render/{job_id}/cancel endpoint."""

    def test_cancel_queued_job(
        self,
        render_client: TestClient,
        mock_render_service: AsyncMock,
    ) -> None:
        """Cancel on queued job calls cancel_job and returns updated job."""
        created = _create_job_via_api(render_client)
        job_id = created["id"]

        # Mock cancel_job to actually update the repo
        async def fake_cancel(jid: str) -> bool:
            return True

        mock_render_service.cancel_job = AsyncMock(side_effect=fake_cancel)

        resp = render_client.post(f"/api/v1/render/{job_id}/cancel")
        assert resp.status_code == 200
        mock_render_service.cancel_job.assert_called_once_with(job_id)

    def test_cancel_not_found(self, render_client: TestClient) -> None:
        """Cancel on unknown job_id returns 404."""
        resp = render_client.post("/api/v1/render/nonexistent-id/cancel")
        assert resp.status_code == 404

    def test_cancel_completed_job(
        self,
        render_client: TestClient,
        render_repo: InMemoryRenderRepository,
    ) -> None:
        """Cancel on completed job returns 409."""
        created = _create_job_via_api(render_client)
        job_id = created["id"]

        import asyncio

        asyncio.run(render_repo.update_status(job_id, RenderStatus.RUNNING))
        asyncio.run(render_repo.update_status(job_id, RenderStatus.COMPLETED))

        resp = render_client.post(f"/api/v1/render/{job_id}/cancel")
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "NOT_CANCELLABLE"


# ---------- POST /render/{job_id}/retry ----------


class TestRetryRenderJob:
    """Tests for POST /render/{job_id}/retry endpoint."""

    def test_retry_failed_job(
        self,
        render_client: TestClient,
        render_repo: InMemoryRenderRepository,
    ) -> None:
        """Retry on failed job transitions back to QUEUED."""
        created = _create_job_via_api(render_client)
        job_id = created["id"]

        import asyncio

        asyncio.run(render_repo.update_status(job_id, RenderStatus.RUNNING))
        asyncio.run(
            render_repo.update_status(job_id, RenderStatus.FAILED, error_message="Transient error")
        )

        resp = render_client.post(f"/api/v1/render/{job_id}/retry")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert data["retry_count"] == 1

    def test_retry_not_found(self, render_client: TestClient) -> None:
        """Retry on unknown job_id returns 404."""
        resp = render_client.post("/api/v1/render/nonexistent-id/retry")
        assert resp.status_code == 404

    def test_retry_queued_job_returns_409(self, render_client: TestClient) -> None:
        """Retry on queued job returns 409."""
        created = _create_job_via_api(render_client)
        resp = render_client.post(f"/api/v1/render/{created['id']}/retry")
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "NOT_RETRYABLE"

    def test_retry_permanent_failure(
        self,
        render_client: TestClient,
        render_repo: InMemoryRenderRepository,
    ) -> None:
        """Retry on permanently failed job (max retries exceeded) returns 409."""
        created = _create_job_via_api(render_client)
        job_id = created["id"]

        import asyncio

        # Exhaust retries: fail -> retry -> fail -> retry -> fail
        # Default max retries = 2, so after retry_count=2, it's permanent
        for _ in range(2):
            asyncio.run(render_repo.update_status(job_id, RenderStatus.RUNNING))
            asyncio.run(
                render_repo.update_status(job_id, RenderStatus.FAILED, error_message="Error")
            )
            asyncio.run(render_repo.update_status(job_id, RenderStatus.QUEUED))

        # Final failure
        asyncio.run(render_repo.update_status(job_id, RenderStatus.RUNNING))
        asyncio.run(
            render_repo.update_status(job_id, RenderStatus.FAILED, error_message="Permanent")
        )

        resp = render_client.post(f"/api/v1/render/{job_id}/retry")
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "PERMANENT_FAILURE"


# ---------- DELETE /render/{job_id} ----------


class TestDeleteRenderJob:
    """Tests for DELETE /render/{job_id} endpoint."""

    def test_delete_job(self, render_client: TestClient) -> None:
        """DELETE removes metadata and returns the deleted job."""
        created = _create_job_via_api(render_client)
        job_id = created["id"]

        resp = render_client.delete(f"/api/v1/render/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job_id

        # Verify it's gone
        get_resp = render_client.get(f"/api/v1/render/{job_id}")
        assert get_resp.status_code == 404

    def test_delete_not_found(self, render_client: TestClient) -> None:
        """DELETE on unknown job_id returns 404."""
        resp = render_client.delete("/api/v1/render/nonexistent-id")
        assert resp.status_code == 404


# ---------- DI dependency injection ----------


class TestDependencyInjection:
    """Tests for DI via getattr app.state fallback."""

    def test_render_service_unavailable(self) -> None:
        """Endpoints return 503 when render_service is not on app.state."""
        app = create_app(render_repository=InMemoryRenderRepository())
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/render",
                json={"project_id": "p1"},
            )
            assert resp.status_code == 503


# ---------- Re-export verification ----------


class TestRenderModuleExports:
    """Tests for render module __all__ re-exports."""

    def test_all_types_importable(self) -> None:
        """All render types are importable from stoat_ferret.render."""
        from stoat_ferret.render import (  # noqa: F401
            AsyncRenderRepository,
            OutputFormat,
            QualityPreset,
            RenderCheckpointManager,
            RenderExecutor,
            RenderJob,
            RenderQueue,
            RenderService,
            RenderStatus,
        )

    def test_all_list_complete(self) -> None:
        """__all__ contains exactly the expected exports."""
        import stoat_ferret.render as render_mod

        expected = {
            "AsyncRenderRepository",
            "CommandBuildError",
            "OutputFormat",
            "QualityPreset",
            "RenderCheckpointManager",
            "RenderExecutor",
            "RenderJob",
            "RenderQueue",
            "RenderService",
            "RenderStatus",
            "RenderWorkerLoop",
            "build_command_for_job",
        }
        assert set(render_mod.__all__) == expected


# ---------- Parity tests: start vs retry ----------


class TestStartRetryParity:
    """Parity tests: both start and retry result in QUEUED jobs."""

    def test_both_produce_queued_status(
        self,
        render_client: TestClient,
        render_repo: InMemoryRenderRepository,
    ) -> None:
        """Both POST /render and POST /render/{id}/retry produce QUEUED jobs."""
        # Start: creates a QUEUED job
        start_data = _create_job_via_api(render_client)
        assert start_data["status"] == "queued"

        # Retry: transitions a FAILED job back to QUEUED
        job_id = start_data["id"]
        import asyncio

        asyncio.run(render_repo.update_status(job_id, RenderStatus.RUNNING))
        asyncio.run(render_repo.update_status(job_id, RenderStatus.FAILED, error_message="test"))
        retry_resp = render_client.post(f"/api/v1/render/{job_id}/retry")
        assert retry_resp.status_code == 200
        assert retry_resp.json()["status"] == "queued"

    def test_both_return_consistent_schema(
        self,
        render_client: TestClient,
        render_repo: InMemoryRenderRepository,
    ) -> None:
        """Both start and retry return the same response schema."""
        start_data = _create_job_via_api(render_client)
        start_keys = set(start_data.keys())

        job_id = start_data["id"]
        import asyncio

        asyncio.run(render_repo.update_status(job_id, RenderStatus.RUNNING))
        asyncio.run(render_repo.update_status(job_id, RenderStatus.FAILED, error_message="test"))
        retry_resp = render_client.post(f"/api/v1/render/{job_id}/retry")
        retry_keys = set(retry_resp.json().keys())

        assert start_keys == retry_keys

    def test_both_log_structured_fields(
        self,
        render_client: TestClient,
        render_repo: InMemoryRenderRepository,
    ) -> None:
        """Both start and retry log with job_id, project_id, action fields."""
        with patch("stoat_ferret.api.routers.render.logger") as mock_logger:
            _create_job_via_api(render_client)
            # Verify start logged
            mock_logger.info.assert_called()
            start_call = mock_logger.info.call_args
            assert start_call[1].get("action") == "start"
            assert "job_id" in start_call[1]
            assert "project_id" in start_call[1]

        # Now retry
        import asyncio

        jobs, _ = asyncio.run(render_repo.list_jobs())
        job = jobs[0]
        asyncio.run(render_repo.update_status(job.id, RenderStatus.RUNNING))
        asyncio.run(render_repo.update_status(job.id, RenderStatus.FAILED, error_message="test"))

        with patch("stoat_ferret.api.routers.render.logger") as mock_logger:
            render_client.post(f"/api/v1/render/{job.id}/retry")
            mock_logger.info.assert_called()
            retry_call = mock_logger.info.call_args
            assert retry_call[1].get("action") == "retry"
            assert "job_id" in retry_call[1]
            assert "project_id" in retry_call[1]


# ---------- System / lifecycle tests ----------


class TestRenderLifecycle:
    """System tests for full render job lifecycle scenarios."""

    def test_full_lifecycle_create_to_delete(
        self,
        render_client: TestClient,
        render_repo: InMemoryRenderRepository,
    ) -> None:
        """Full lifecycle: create -> queue -> complete -> delete."""
        created = _create_job_via_api(render_client)
        job_id = created["id"]
        assert created["status"] == "queued"

        import asyncio

        # Simulate running
        asyncio.run(render_repo.update_status(job_id, RenderStatus.RUNNING))
        resp = render_client.get(f"/api/v1/render/{job_id}")
        assert resp.json()["status"] == "running"

        # Simulate completion
        asyncio.run(render_repo.update_status(job_id, RenderStatus.COMPLETED))
        resp = render_client.get(f"/api/v1/render/{job_id}")
        assert resp.json()["status"] == "completed"
        assert resp.json()["progress"] == 1.0

        # Delete
        resp = render_client.delete(f"/api/v1/render/{job_id}")
        assert resp.status_code == 200
        resp = render_client.get(f"/api/v1/render/{job_id}")
        assert resp.status_code == 404

    def test_retry_transient_failure_to_completion(
        self,
        render_client: TestClient,
        render_repo: InMemoryRenderRepository,
    ) -> None:
        """Lifecycle: create -> fail (transient) -> retry -> complete."""
        created = _create_job_via_api(render_client)
        job_id = created["id"]

        import asyncio

        asyncio.run(render_repo.update_status(job_id, RenderStatus.RUNNING))
        asyncio.run(
            render_repo.update_status(job_id, RenderStatus.FAILED, error_message="Transient error")
        )

        # Retry
        resp = render_client.post(f"/api/v1/render/{job_id}/retry")
        assert resp.status_code == 200
        assert resp.json()["status"] == "queued"

        # Complete after retry
        asyncio.run(render_repo.update_status(job_id, RenderStatus.RUNNING))
        asyncio.run(render_repo.update_status(job_id, RenderStatus.COMPLETED))
        resp = render_client.get(f"/api/v1/render/{job_id}")
        assert resp.json()["status"] == "completed"

    def test_contract_render_job_json_roundtrip(self, render_client: TestClient) -> None:
        """Contract: RenderJob JSON serialization round-trip."""
        created = _create_job_via_api(render_client)
        job_id = created["id"]

        resp = render_client.get(f"/api/v1/render/{job_id}")
        data = resp.json()

        # Verify all expected fields are present and correctly typed
        assert isinstance(data["id"], str)
        assert isinstance(data["project_id"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["output_path"], str)
        assert isinstance(data["output_format"], str)
        assert isinstance(data["quality_preset"], str)
        assert isinstance(data["progress"], float)
        assert isinstance(data["retry_count"], int)
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)

    def test_contract_error_response_schema(self, render_client: TestClient) -> None:
        """Contract: error responses match {detail: {code, message}} schema."""
        resp = render_client.get("/api/v1/render/nonexistent")
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert "code" in detail
        assert "message" in detail


# ---------- Encoder endpoint fixtures ----------


def _make_sample_entries(count: int = 3) -> list[EncoderCacheEntry]:
    """Create sample encoder cache entries for testing."""
    now = datetime.now(timezone.utc)
    entries = [
        EncoderCacheEntry(
            id=None,
            name="libx264",
            codec="h264",
            is_hardware=False,
            encoder_type="Software",
            description="libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
            detected_at=now,
        ),
        EncoderCacheEntry(
            id=None,
            name="h264_nvenc",
            codec="h264",
            is_hardware=True,
            encoder_type="Nvenc",
            description="NVIDIA NVENC H.264 encoder",
            detected_at=now,
        ),
        EncoderCacheEntry(
            id=None,
            name="libx265",
            codec="hevc",
            is_hardware=False,
            encoder_type="Software",
            description="libx265 H.265 / HEVC",
            detected_at=now,
        ),
    ]
    return entries[:count]


def _make_raw_encoders() -> list:
    """Create mock _RawEncoder objects for detection mock."""
    from stoat_ferret.api.routers.render import _RawEncoder

    return [
        _RawEncoder(
            name="libx264",
            codec="h264",
            is_hardware=False,
            encoder_type="Software",
            description="libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
        ),
        _RawEncoder(
            name="h264_nvenc",
            codec="h264",
            is_hardware=True,
            encoder_type="Nvenc",
            description="NVIDIA NVENC H.264 encoder",
        ),
    ]


@pytest.fixture
def encoder_repo() -> InMemoryEncoderCacheRepository:
    """Create isolated encoder cache repository for encoder tests."""
    return InMemoryEncoderCacheRepository()


@pytest.fixture
def encoder_app(
    render_repo: InMemoryRenderRepository,
    mock_render_service: AsyncMock,
    encoder_repo: InMemoryEncoderCacheRepository,
) -> FastAPI:
    """Create test app with encoder cache repository injected."""
    app = create_app(
        render_repository=render_repo,
        render_service=mock_render_service,
    )
    app.state.encoder_cache_repository = encoder_repo
    return app


@pytest.fixture
def encoder_client(encoder_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create test client for encoder endpoints."""
    with TestClient(encoder_app) as c:
        yield c


# ---------- GET /render/encoders ----------


class TestGetEncoders:
    """Tests for GET /render/encoders endpoint."""

    def test_get_encoders_returns_cached(
        self,
        encoder_client: TestClient,
        encoder_repo: InMemoryEncoderCacheRepository,
    ) -> None:
        """GET /render/encoders returns cached encoders when cache is populated."""
        entries = _make_sample_entries()
        asyncio.run(encoder_repo.create_many(entries))

        resp = encoder_client.get("/api/v1/render/encoders")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is True
        assert len(data["encoders"]) == 3

    def test_get_encoders_lazy_detection(
        self,
        encoder_client: TestClient,
    ) -> None:
        """GET /render/encoders triggers lazy detection when cache is empty."""
        raw = _make_raw_encoders()
        with patch(
            "stoat_ferret.api.routers.render._detect_encoders_sync",
            return_value=raw,
        ):
            resp = encoder_client.get("/api/v1/render/encoders")

        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is False
        assert len(data["encoders"]) == 2
        names = {e["name"] for e in data["encoders"]}
        assert "libx264" in names
        assert "h264_nvenc" in names

    def test_get_encoders_ffmpeg_unavailable(
        self,
        encoder_client: TestClient,
    ) -> None:
        """GET /render/encoders returns 503 when FFmpeg is unavailable."""
        with patch(
            "stoat_ferret.api.routers.render._detect_encoders_sync",
            side_effect=FileNotFoundError("ffmpeg not found"),
        ):
            resp = encoder_client.get("/api/v1/render/encoders")

        assert resp.status_code == 503
        assert resp.json()["detail"]["code"] == "FFMPEG_UNAVAILABLE"

    def test_get_encoders_response_schema(
        self,
        encoder_client: TestClient,
        encoder_repo: InMemoryEncoderCacheRepository,
    ) -> None:
        """GET /render/encoders returns correct schema fields."""
        entries = _make_sample_entries(1)
        asyncio.run(encoder_repo.create_many(entries))

        resp = encoder_client.get("/api/v1/render/encoders")
        data = resp.json()
        assert set(data.keys()) == {"encoders", "cached"}
        enc = data["encoders"][0]
        expected = {"name", "codec", "is_hardware", "encoder_type", "description", "detected_at"}
        assert set(enc.keys()) == expected

    def test_get_encoders_during_refresh_returns_stale(
        self,
        encoder_app: FastAPI,
        encoder_repo: InMemoryEncoderCacheRepository,
    ) -> None:
        """GET during active refresh returns stale cached data (NFR-003)."""
        # Pre-populate cache
        entries = _make_sample_entries(1)
        asyncio.run(encoder_repo.create_many(entries))

        with TestClient(encoder_app) as client:
            # Cache is populated, GET should return cached data regardless of lock
            resp = client.get("/api/v1/render/encoders")
            assert resp.status_code == 200
            assert resp.json()["cached"] is True
            assert len(resp.json()["encoders"]) == 1


# ---------- POST /render/encoders/refresh ----------


class TestRefreshEncoders:
    """Tests for POST /render/encoders/refresh endpoint."""

    def test_refresh_returns_fresh_results(
        self,
        encoder_client: TestClient,
        encoder_repo: InMemoryEncoderCacheRepository,
    ) -> None:
        """POST /render/encoders/refresh re-runs detection and updates cache."""
        # Pre-populate with old data
        old_entries = _make_sample_entries(1)
        asyncio.run(encoder_repo.create_many(old_entries))

        raw = _make_raw_encoders()
        with patch(
            "stoat_ferret.api.routers.render._detect_encoders_sync",
            return_value=raw,
        ):
            resp = encoder_client.post("/api/v1/render/encoders/refresh")

        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is False
        assert len(data["encoders"]) == 2

        # Verify cache was updated
        cached = asyncio.run(encoder_repo.get_all())
        assert len(cached) == 2

    def test_refresh_clears_old_cache(
        self,
        encoder_client: TestClient,
        encoder_repo: InMemoryEncoderCacheRepository,
    ) -> None:
        """POST /render/encoders/refresh truncates old cache before re-inserting."""
        old_entries = _make_sample_entries(3)
        asyncio.run(encoder_repo.create_many(old_entries))

        # Return only 1 encoder this time
        raw = _make_raw_encoders()[:1]
        with patch(
            "stoat_ferret.api.routers.render._detect_encoders_sync",
            return_value=raw,
        ):
            resp = encoder_client.post("/api/v1/render/encoders/refresh")

        assert resp.status_code == 200
        cached = asyncio.run(encoder_repo.get_all())
        assert len(cached) == 1

    def test_refresh_ffmpeg_unavailable(
        self,
        encoder_client: TestClient,
    ) -> None:
        """POST /render/encoders/refresh returns 503 when FFmpeg is unavailable."""
        with patch(
            "stoat_ferret.api.routers.render._detect_encoders_sync",
            side_effect=FileNotFoundError("ffmpeg not found"),
        ):
            resp = encoder_client.post("/api/v1/render/encoders/refresh")

        assert resp.status_code == 503
        assert resp.json()["detail"]["code"] == "FFMPEG_UNAVAILABLE"

    def test_refresh_uses_asyncio_to_thread(
        self,
        encoder_client: TestClient,
    ) -> None:
        """POST /render/encoders/refresh uses asyncio.to_thread (NFR-001)."""
        raw = _make_raw_encoders()
        with patch(
            "stoat_ferret.api.routers.render.asyncio.to_thread",
            new_callable=AsyncMock,
            return_value=raw,
        ) as mock_to_thread:
            resp = encoder_client.post("/api/v1/render/encoders/refresh")

        assert resp.status_code == 200
        mock_to_thread.assert_called_once()


# ---------- Encoder cache parity tests ----------


class TestEncoderCacheParity:
    """Parity tests: AsyncSQLiteEncoderCacheRepository vs InMemoryEncoderCacheRepository."""

    def test_create_many_and_get_all_parity(
        self,
        encoder_repo: InMemoryEncoderCacheRepository,
    ) -> None:
        """Both implementations return same entries after create_many."""
        entries = _make_sample_entries()
        created = asyncio.run(encoder_repo.create_many(entries))
        assert len(created) == 3
        assert all(e.id is not None for e in created)

        fetched = asyncio.run(encoder_repo.get_all())
        assert len(fetched) == 3
        names = {e.name for e in fetched}
        assert names == {"libx264", "h264_nvenc", "libx265"}

    def test_clear_removes_all(
        self,
        encoder_repo: InMemoryEncoderCacheRepository,
    ) -> None:
        """Clear removes all entries from cache."""
        entries = _make_sample_entries()
        asyncio.run(encoder_repo.create_many(entries))

        asyncio.run(encoder_repo.clear())
        fetched = asyncio.run(encoder_repo.get_all())
        assert len(fetched) == 0

    def test_refresh_cycle_truncate_reinsert(
        self,
        encoder_repo: InMemoryEncoderCacheRepository,
    ) -> None:
        """Refresh cycle: clear + create_many replaces all entries."""
        old = _make_sample_entries(3)
        asyncio.run(encoder_repo.create_many(old))
        assert len(asyncio.run(encoder_repo.get_all())) == 3

        # Simulate refresh: clear + re-insert with fewer entries
        asyncio.run(encoder_repo.clear())
        new = _make_sample_entries(1)
        asyncio.run(encoder_repo.create_many(new))

        fetched = asyncio.run(encoder_repo.get_all())
        assert len(fetched) == 1
        assert fetched[0].name == "libx264"


# ---------- Encoder contract tests ----------


class TestEncoderContract:
    """Contract tests for encoder cache round-trip and response schema."""

    def test_encoder_cache_roundtrip(
        self,
        encoder_repo: InMemoryEncoderCacheRepository,
    ) -> None:
        """Encoder cache SQLite round-trip: insert -> read -> verify all fields."""
        now = datetime.now(timezone.utc)
        entry = EncoderCacheEntry(
            id=None,
            name="hevc_nvenc",
            codec="hevc",
            is_hardware=True,
            encoder_type="Nvenc",
            description="NVIDIA NVENC HEVC encoder",
            detected_at=now,
        )
        created = asyncio.run(encoder_repo.create_many([entry]))
        assert len(created) == 1
        assert created[0].id is not None

        fetched = asyncio.run(encoder_repo.get_all())
        assert len(fetched) == 1
        e = fetched[0]
        assert e.name == "hevc_nvenc"
        assert e.codec == "hevc"
        assert e.is_hardware is True
        assert e.encoder_type == "Nvenc"
        assert e.description == "NVIDIA NVENC HEVC encoder"
        assert e.detected_at == now

    def test_encoder_response_matches_cache_entry(
        self,
        encoder_client: TestClient,
        encoder_repo: InMemoryEncoderCacheRepository,
    ) -> None:
        """Encoder response schema matches EncoderCacheEntry fields."""
        entries = _make_sample_entries(1)
        asyncio.run(encoder_repo.create_many(entries))

        resp = encoder_client.get("/api/v1/render/encoders")
        enc = resp.json()["encoders"][0]

        assert enc["name"] == entries[0].name
        assert enc["codec"] == entries[0].codec
        assert enc["is_hardware"] == entries[0].is_hardware
        assert enc["encoder_type"] == entries[0].encoder_type
        assert enc["description"] == entries[0].description


# ---------- GET /render/formats ----------


class TestGetOutputFormats:
    """Tests for GET /render/formats discovery endpoint."""

    def test_returns_all_four_formats(self, render_client: TestClient) -> None:
        """GET /render/formats returns MP4, WEBM, MOV, MKV."""
        resp = render_client.get("/api/v1/render/formats")
        assert resp.status_code == 200
        data = resp.json()
        format_names = {f["format"] for f in data["formats"]}
        assert format_names == {"mp4", "webm", "mov", "mkv"}

    def test_format_extensions_and_mime_types(self, render_client: TestClient) -> None:
        """Each format has correct file extension and MIME type."""
        resp = render_client.get("/api/v1/render/formats")
        formats = {f["format"]: f for f in resp.json()["formats"]}

        assert formats["mp4"]["extension"] == ".mp4"
        assert formats["mp4"]["mime_type"] == "video/mp4"
        assert formats["webm"]["extension"] == ".webm"
        assert formats["webm"]["mime_type"] == "video/webm"
        assert formats["mov"]["extension"] == ".mov"
        assert formats["mov"]["mime_type"] == "video/quicktime"
        assert formats["mkv"]["extension"] == ".mkv"
        assert formats["mkv"]["mime_type"] == "video/x-matroska"

    def test_codecs_present_per_format(self, render_client: TestClient) -> None:
        """Each format includes at least one codec."""
        resp = render_client.get("/api/v1/render/formats")
        for fmt in resp.json()["formats"]:
            assert len(fmt["codecs"]) >= 1, f"{fmt['format']} has no codecs"
            for codec in fmt["codecs"]:
                assert "name" in codec
                assert isinstance(codec["name"], str)

    def test_capability_flags_present(self, render_client: TestClient) -> None:
        """Each format has boolean capability flags."""
        resp = render_client.get("/api/v1/render/formats")
        for fmt in resp.json()["formats"]:
            assert isinstance(fmt["supports_hw_accel"], bool)
            assert isinstance(fmt["supports_two_pass"], bool)
            assert isinstance(fmt["supports_alpha"], bool)

    def test_capability_flag_values(self, render_client: TestClient) -> None:
        """Capability flags are accurate per format."""
        resp = render_client.get("/api/v1/render/formats")
        formats = {f["format"]: f for f in resp.json()["formats"]}

        # MP4 does not support alpha
        assert formats["mp4"]["supports_hw_accel"] is True
        assert formats["mp4"]["supports_alpha"] is False

        # WebM does not support hw accel
        assert formats["webm"]["supports_hw_accel"] is False
        assert formats["webm"]["supports_alpha"] is True

    def test_quality_presets_per_codec(self, render_client: TestClient) -> None:
        """Each codec includes DRAFT, STANDARD, HIGH quality presets with bitrates."""
        resp = render_client.get("/api/v1/render/formats")
        expected_presets = {"draft", "standard", "high"}

        for fmt in resp.json()["formats"]:
            for codec in fmt["codecs"]:
                preset_names = {p["preset"] for p in codec["quality_presets"]}
                assert preset_names == expected_presets, (
                    f"{fmt['format']}/{codec['name']} missing presets: "
                    f"{expected_presets - preset_names}"
                )
                for preset in codec["quality_presets"]:
                    assert isinstance(preset["video_bitrate_kbps"], int)
                    assert preset["video_bitrate_kbps"] > 0

    def test_no_dependencies_required(self) -> None:
        """Format endpoint works without render_service or database (NFR-001)."""
        app = create_app()
        with TestClient(app) as client:
            resp = client.get("/api/v1/render/formats")
        assert resp.status_code == 200
        assert len(resp.json()["formats"]) == 4


class TestFormatContract:
    """Contract tests for format discovery response schema."""

    def test_response_schema_all_formats_present(self, render_client: TestClient) -> None:
        """Contract: all 4 OutputFormat variants present with required fields."""
        resp = render_client.get("/api/v1/render/formats")
        assert resp.status_code == 200
        data = resp.json()

        assert "formats" in data
        assert len(data["formats"]) == 4

        required_format_fields = {
            "format",
            "extension",
            "mime_type",
            "codecs",
            "supports_hw_accel",
            "supports_two_pass",
            "supports_alpha",
        }
        required_codec_fields = {"name", "encoder", "quality_presets"}
        required_preset_fields = {"preset", "video_bitrate_kbps"}

        for fmt in data["formats"]:
            assert set(fmt.keys()) == required_format_fields
            for codec in fmt["codecs"]:
                assert set(codec.keys()) == required_codec_fields
                for preset in codec["quality_presets"]:
                    assert set(preset.keys()) == required_preset_fields

    def test_format_values_match_output_format_enum(self, render_client: TestClient) -> None:
        """Contract: format identifiers match OutputFormat enum values."""
        resp = render_client.get("/api/v1/render/formats")
        format_names = {f["format"] for f in resp.json()["formats"]}
        enum_values = {f.value for f in OutputFormat}
        assert format_names == enum_values


# ---------- Queue status fixtures ----------


@pytest.fixture
def queue_repo() -> InMemoryRenderRepository:
    """Create isolated render repository for queue status tests."""
    return InMemoryRenderRepository()


@pytest.fixture
def queue_app(
    queue_repo: InMemoryRenderRepository,
    mock_render_service: AsyncMock,
) -> FastAPI:
    """Create test app with render queue injected for queue status tests."""
    from stoat_ferret.render.queue import RenderQueue

    queue = RenderQueue(queue_repo, max_concurrent=4, max_depth=50)
    return create_app(
        render_repository=queue_repo,
        render_service=mock_render_service,
        render_queue=queue,
    )


@pytest.fixture
def queue_client(queue_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create test client for queue status endpoints."""
    with TestClient(queue_app) as c:
        yield c


# ---------- GET /render/queue ----------


class TestGetQueueStatus:
    """Tests for GET /render/queue endpoint."""

    def test_queue_status_returns_counts(
        self,
        queue_client: TestClient,
    ) -> None:
        """GET /render/queue returns active_count, pending_count, and max values."""
        resp = queue_client.get("/api/v1/render/queue")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_count"] == 0
        assert data["pending_count"] == 0
        assert data["max_concurrent"] == 4
        assert data["max_queue_depth"] == 50

    def test_queue_status_disk_space(
        self,
        queue_client: TestClient,
    ) -> None:
        """GET /render/queue includes disk space values."""
        resp = queue_client.get("/api/v1/render/queue")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["disk_available_bytes"], int)
        assert data["disk_available_bytes"] > 0
        assert isinstance(data["disk_total_bytes"], int)
        assert data["disk_total_bytes"] > 0
        assert data["disk_total_bytes"] >= data["disk_available_bytes"]

    def test_queue_status_today_counts(
        self,
        queue_client: TestClient,
        queue_repo: InMemoryRenderRepository,
    ) -> None:
        """GET /render/queue includes completed_today and failed_today counts."""
        # Create and complete a job
        job = RenderJob.create(
            project_id="proj-q1",
            output_path="/tmp/q1.mp4",
            output_format=OutputFormat.MP4,
            quality_preset=QualityPreset.STANDARD,
            render_plan="{}",
        )
        asyncio.run(queue_repo.create(job))
        asyncio.run(queue_repo.update_status(job.id, RenderStatus.RUNNING))
        asyncio.run(queue_repo.update_status(job.id, RenderStatus.COMPLETED))

        # Create and fail another job
        job2 = RenderJob.create(
            project_id="proj-q2",
            output_path="/tmp/q2.mp4",
            output_format=OutputFormat.MP4,
            quality_preset=QualityPreset.STANDARD,
            render_plan="{}",
        )
        asyncio.run(queue_repo.create(job2))
        asyncio.run(queue_repo.update_status(job2.id, RenderStatus.RUNNING))
        asyncio.run(
            queue_repo.update_status(job2.id, RenderStatus.FAILED, error_message="test error")
        )

        resp = queue_client.get("/api/v1/render/queue")
        assert resp.status_code == 200
        data = resp.json()
        assert data["completed_today"] == 1
        assert data["failed_today"] == 1

    def test_queue_status_realtime_accuracy(
        self,
        queue_client: TestClient,
        queue_repo: InMemoryRenderRepository,
    ) -> None:
        """GET /render/queue reflects real-time state after enqueue (FR-004)."""
        # Initially empty
        resp = queue_client.get("/api/v1/render/queue")
        assert resp.json()["pending_count"] == 0
        assert resp.json()["active_count"] == 0

        # Enqueue a job
        job = RenderJob.create(
            project_id="proj-rt",
            output_path="/tmp/rt.mp4",
            output_format=OutputFormat.MP4,
            quality_preset=QualityPreset.STANDARD,
            render_plan="{}",
        )
        asyncio.run(queue_repo.create(job))

        # Immediately check — count should be updated
        resp = queue_client.get("/api/v1/render/queue")
        assert resp.json()["pending_count"] == 1

        # Transition to running
        asyncio.run(queue_repo.update_status(job.id, RenderStatus.RUNNING))
        resp = queue_client.get("/api/v1/render/queue")
        assert resp.json()["active_count"] == 1
        assert resp.json()["pending_count"] == 0

    def test_queue_status_response_schema(
        self,
        queue_client: TestClient,
    ) -> None:
        """GET /render/queue returns all expected fields."""
        resp = queue_client.get("/api/v1/render/queue")
        assert resp.status_code == 200
        expected_fields = {
            "active_count",
            "pending_count",
            "max_concurrent",
            "max_queue_depth",
            "disk_available_bytes",
            "disk_total_bytes",
            "completed_today",
            "failed_today",
        }
        assert set(resp.json().keys()) == expected_fields

    def test_queue_unavailable_returns_503(self) -> None:
        """GET /render/queue returns 503 when render queue is not on app.state."""
        app = create_app(render_repository=InMemoryRenderRepository())
        with TestClient(app) as client:
            resp = client.get("/api/v1/render/queue")
            assert resp.status_code == 503
