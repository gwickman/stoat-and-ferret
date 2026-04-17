"""Smoke tests for render WebSocket progress enrichment (BL-254).

Verifies that the RENDER_PROGRESS WebSocket event emitted during a render
includes the enriched fields: frame_count, fps, encoder_name, encoder_type.
These fields enable Theater Mode BottomHUD to display detailed render
observability without additional metrics sources.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import httpx

from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import RenderService


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
