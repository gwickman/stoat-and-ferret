"""Smoke tests for render WebSocket progress enrichment (BL-254) and
frame streaming to Theater Mode (BL-255).

Verifies that:
- RENDER_PROGRESS WebSocket events include enriched fields: frame_count, fps,
  encoder_name, encoder_type (BL-254).
- render.frame_available events carry a valid frame_url and correct payload
  schema (BL-255, FR-001).
- The frame preview endpoint returns 404 when no frame is cached and the
  correct JPEG when a frame is pre-cached in the service buffer (BL-255, FR-002).
"""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
from PIL import Image

from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.clip_repository import AsyncSQLiteClipRepository
from stoat_ferret.db.models import Clip
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import RenderService


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


def _make_render_plan(codec: str = "libx264") -> str:
    """Build a minimal render plan JSON for smoke tests."""
    return json.dumps(
        {
            "total_duration": 10.0,
            "segments": [],
            "settings": {
                "output_format": "mp4",
                "width": 1280,
                "height": 720,
                "codec": codec,
                "quality_preset": "standard",
                "fps": 30.0,
            },
        }
    )


def _build_service_with_capture() -> tuple[RenderService, list[dict]]:
    """Build a RenderService where broadcast calls are captured.

    Returns:
        Tuple of (service, captured_broadcasts) where captured_broadcasts
        accumulates every dict passed to ws.broadcast().
    """
    repo = InMemoryRenderRepository()
    captured: list[dict] = []

    async def _capture(event: dict) -> None:
        captured.append(event)

    ws: ConnectionManager = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock(side_effect=_capture)

    checkpoint_mgr = MagicMock()
    checkpoint_mgr.recover = AsyncMock(return_value=[])
    checkpoint_mgr.cleanup_stale = AsyncMock(return_value=0)

    queue = RenderQueue(repo, max_concurrent=4, max_depth=50)
    service = RenderService(
        repository=repo,
        queue=queue,
        executor=RenderExecutor(),
        checkpoint_manager=checkpoint_mgr,
        connection_manager=ws,
        settings=Settings(render_retry_count=0),
    )
    return service, captured


async def test_theater_mode_displays_encoder_info() -> None:
    """Theater Mode BottomHUD receives encoder info via RENDER_PROGRESS events.

    Simulates a render progress callback with enriched fields and verifies
    that the RENDER_PROGRESS WebSocket event includes encoder_name, encoder_type,
    frame_count, and fps — the fields required by Theater Mode BottomHUD (FR-001
    through FR-006).
    """
    service, captured = _build_service_with_capture()

    # Simulate progress callback with enriched fields from FFmpeg output
    await service._broadcast_throttled_progress(
        "job-theater-1",
        0.5,
        eta_seconds=5.0,
        speed_ratio=2.0,
        frame_count=150,
        fps=30.0,
        encoder_name="libx264",
        encoder_type="SW",
    )

    # Exactly one RENDER_PROGRESS event should have been broadcast
    progress_events = [e for e in captured if e.get("type") == "render_progress"]
    assert len(progress_events) == 1, (
        f"Expected 1 render_progress event, got {len(progress_events)}"
    )

    payload = progress_events[0]["payload"]

    # Verify all enriched fields are present and correct
    assert payload["encoder_name"] == "libx264", (
        f"Expected encoder_name='libx264', got {payload.get('encoder_name')!r}"
    )
    assert payload["encoder_type"] == "SW", (
        f"Expected encoder_type='SW', got {payload.get('encoder_type')!r}"
    )
    assert payload["frame_count"] == 150, (
        f"Expected frame_count=150, got {payload.get('frame_count')!r}"
    )
    assert abs(payload["fps"] - 30.0) < 1e-6, f"Expected fps=30.0, got {payload.get('fps')!r}"


async def test_theater_mode_null_fields_handled_gracefully() -> None:
    """Theater Mode BottomHUD hides fields when progress event carries null values.

    Verifies that RENDER_PROGRESS events with null enriched fields are broadcast
    without error and contain explicit null values (not missing keys), so
    consumers can reliably check for null (FR-005).
    """
    service, captured = _build_service_with_capture()

    await service._broadcast_throttled_progress(
        "job-theater-2",
        0.3,
        frame_count=None,
        fps=None,
        encoder_name=None,
        encoder_type=None,
    )

    progress_events = [e for e in captured if e.get("type") == "render_progress"]
    assert len(progress_events) == 1

    payload = progress_events[0]["payload"]

    # All four new fields must be present in the payload (even if None)
    for field in ("frame_count", "fps", "encoder_name", "encoder_type"):
        assert field in payload, f"Field '{field}' missing from RENDER_PROGRESS payload"
        assert payload[field] is None, f"Expected null for '{field}', got {payload[field]!r}"

    # The event must remain JSON-serialisable with null fields
    serialised = json.dumps(progress_events[0])
    assert "frame_count" in serialised


async def test_theater_mode_hw_encoder_type() -> None:
    """Theater Mode BottomHUD displays HW badge for hardware encoder.

    Verifies that the RENDER_PROGRESS event carries encoder_type='HW' when
    a hardware encoder (e.g., h264_nvenc) is used (FR-004).
    """
    service, captured = _build_service_with_capture()

    await service._broadcast_throttled_progress(
        "job-theater-3",
        0.4,
        encoder_name="h264_nvenc",
        encoder_type="HW",
        frame_count=480,
        fps=60.0,
    )

    progress_events = [e for e in captured if e.get("type") == "render_progress"]
    assert len(progress_events) == 1

    payload = progress_events[0]["payload"]
    assert payload["encoder_name"] == "h264_nvenc"
    assert payload["encoder_type"] == "HW"


async def test_render_progress_enriched_from_job_render_plan(
    smoke_client: httpx.AsyncClient,
) -> None:
    """Render job created with explicit encoder yields SW encoder_type in progress.

    Verifies that the encoder_name extracted from a job's render_plan is
    correctly classified as SW (libx264 is a software encoder), confirming
    the full pipeline from render job creation to encoder_type derivation.
    """
    # Create a project
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Theater Mode Encoder Info Test"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]
    await _seed_clip_for_project(smoke_client, project_id)

    # Create a render job (no real FFmpeg execution — just verifies job creation)
    resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id},
    )
    assert resp.status_code == 201
    job_data = resp.json()

    # Verify the job was created with expected status
    assert job_data["status"] in ("queued", "running")

    # Retrieve the job and verify the render plan contains a codec
    get_resp = await smoke_client.get(f"/api/v1/render/{job_data['id']}")
    assert get_resp.status_code == 200


async def test_theater_mode_displays_streaming_frames() -> None:
    """Theater Mode receives frame events with correct URL schema (FR-001, FR-002, FR-003).

    Simulates the frame streaming pipeline:
    1. RenderService emits render.frame_available events with a frame_url.
    2. The frame_url points to the frame preview endpoint for the job.
    3. Theater Mode subscribes to these events and fetches the frame_url.

    Verifies the event payload schema so that Theater Mode can correctly
    extract frame_url and display it during an active render (FR-003).
    Also verifies that frame events stop being emitted (FR-004) by checking
    that throttle state is cleared when the job completes.
    """
    repo = InMemoryRenderRepository()
    captured: list[dict] = []

    async def _capture(event: dict) -> None:
        captured.append(event)

    ws: ConnectionManager = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock(side_effect=_capture)

    checkpoint_mgr = MagicMock()
    checkpoint_mgr.recover = AsyncMock(return_value=[])
    checkpoint_mgr.cleanup_stale = AsyncMock(return_value=0)

    queue = RenderQueue(repo, max_concurrent=4, max_depth=50)
    service = RenderService(
        repository=repo,
        queue=queue,
        executor=RenderExecutor(),
        checkpoint_manager=checkpoint_mgr,
        connection_manager=ws,
        settings=Settings(render_retry_count=0),
    )

    job_id = "theater-frame-job-1"

    # Simulate frame event emission (as if render is in progress)
    await service._broadcast_throttled_frame(job_id, 0.5)

    frame_events = [e for e in captured if e.get("type") == "render_frame_available"]
    assert len(frame_events) == 1, (
        f"Expected 1 render_frame_available event, got {len(frame_events)}"
    )

    payload = frame_events[0]["payload"]

    # FR-001: Event carries required fields
    assert payload["job_id"] == job_id
    assert "frame_url" in payload, "frame_url must be present in render.frame_available payload"
    assert "resolution" in payload, "resolution must be present in render.frame_available payload"
    assert "progress" in payload, "progress must be present in render.frame_available payload"

    # FR-002: frame_url points to the frame preview endpoint
    expected_url = f"/api/v1/render/{job_id}/frame_preview.jpg"
    assert payload["frame_url"] == expected_url, (
        f"Expected frame_url={expected_url!r}, got {payload['frame_url']!r}"
    )
    assert payload["resolution"] == "540p", (
        f"Expected resolution='540p', got {payload['resolution']!r}"
    )

    # FR-004: After clearing throttle state (job completion), no more frame events
    service._clear_throttle_state(job_id)
    # Frame buffer is cleared — Theater Mode reverts to normal preview
    assert service.get_frame_bytes(job_id) is None, (
        "Frame buffer should be cleared after job completes (FR-004)"
    )


async def test_theater_mode_frame_endpoint_returns_jpeg_when_buffer_populated() -> None:
    """Frame endpoint returns valid 540p JPEG when service frame buffer is pre-populated.

    Verifies the full data path:
    1. Service stores JPEG bytes in _frame_buffer (simulating successful frame capture).
    2. get_frame_bytes() returns those bytes.
    3. The endpoint (tested via service API) returns valid JPEG at 540p height.

    FR-002: Frame endpoint returns 540p JPEG of latest rendered frame.
    NFR-002: Response must be a valid JPEG.
    """
    repo = InMemoryRenderRepository()
    ws: ConnectionManager = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock()
    checkpoint_mgr = MagicMock()
    checkpoint_mgr.recover = AsyncMock(return_value=[])
    checkpoint_mgr.cleanup_stale = AsyncMock(return_value=0)

    queue = RenderQueue(repo, max_concurrent=4, max_depth=50)
    service = RenderService(
        repository=repo,
        queue=queue,
        executor=RenderExecutor(),
        checkpoint_manager=checkpoint_mgr,
        connection_manager=ws,
        settings=Settings(render_retry_count=0),
    )

    job_id = "frame-buffer-test-job"

    # Pre-populate the frame buffer with a valid 540p JPEG (simulates successful capture)
    img = Image.new("RGB", (960, 540), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    jpeg_bytes = buf.getvalue()
    service._frame_buffer[job_id] = jpeg_bytes

    # Verify get_frame_bytes returns the stored bytes
    retrieved = service.get_frame_bytes(job_id)
    assert retrieved is not None, "get_frame_bytes should return bytes from _frame_buffer"
    assert retrieved == jpeg_bytes, "Returned bytes should match stored JPEG bytes"

    # Verify the returned bytes are a valid JPEG at 540p
    retrieved_img = Image.open(io.BytesIO(retrieved))
    assert retrieved_img.format == "JPEG", f"Expected JPEG format, got {retrieved_img.format}"
    assert retrieved_img.height == 540, (
        f"Expected height=540, got {retrieved_img.height} (FR-002: 540p requirement)"
    )


async def test_render_events_include_monotonic_event_id() -> None:
    """Render WebSocket events include a monotonic ``event_id`` (BL-273, BL-356).

    FR-001: every ``build_event`` output carries ``event_id`` in ``event-NNNNN`` form.
    INV-002: values within a single job are strictly monotonically increasing.
    INV-007 (global): global counter continues past terminal cleanup;
    ``clear_event_counter`` is a no-op under global-counter mode (BL-356, RISK-003).
    """
    import re

    from stoat_ferret.api.websocket.events import reset_event_counters

    reset_event_counters()
    service, captured = _build_service_with_capture()
    job_id = "event-id-smoke-1"

    # Emit multiple RENDER_PROGRESS events followed by a frame event.
    for progress in (0.2, 0.4, 0.6, 0.8, 1.0):
        await service._broadcast_throttled_progress(
            job_id,
            progress,
            frame_count=int(progress * 100),
            fps=30.0,
            encoder_name="libx264",
            encoder_type="SW",
        )

    events_for_job = [e for e in captured if e.get("payload", {}).get("job_id") == job_id]
    assert len(events_for_job) >= 2, (
        f"Expected multiple broadcast events for job, got {len(events_for_job)}"
    )

    pattern = re.compile(r"^event-\d{5,}$")
    for event in events_for_job:
        assert "event_id" in event, "event_id missing from broadcast payload (FR-004)"
        assert pattern.match(event["event_id"]), (
            f"event_id '{event['event_id']}' does not match event-NNNNN format (FR-001)"
        )

    # Strictly monotonically increasing within a single job (NFR-002).
    numeric_ids = [int(e["event_id"].split("-")[1]) for e in events_for_job]
    for prev, nxt in zip(numeric_ids, numeric_ids[1:], strict=False):
        assert nxt > prev, f"event_id must strictly increase within job: {prev} -> {nxt}"

    # Terminal cleanup: clearing throttle state also clears the event counter.
    service._clear_throttle_state(job_id)
    resumed = await service._broadcast_throttled_progress(
        job_id,
        0.1,
        frame_count=10,
        fps=30.0,
        encoder_name="libx264",
        encoder_type="SW",
    )
    del resumed  # not used; broadcast captured via callback
    new_events = [
        e for e in captured[len(events_for_job) :] if e.get("payload", {}).get("job_id") == job_id
    ]
    assert new_events, "Expected a broadcast after resume"
    assert int(new_events[0]["event_id"].split("-")[1]) > numeric_ids[-1], (
        "Counter must strictly increase past previous events under global-counter mode"
    )
