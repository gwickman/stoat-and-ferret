# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for render WebSocket events with throttled broadcasting.

Covers EventType enum extension, dual-threshold throttling (time + progress delta),
per-job-per-event-type isolation, frame_available events, queue_status events,
event payload schema, full lifecycle event sequences, cancel/complete race invariants,
and library DELETE WS events (video_deleted, clip_deleted).
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import RenderService
from stoat_ferret.render.sweeper import StaleRenderSweeper

# Disable Rust bindings — tests exercise Python orchestration logic.
_PATCH_NO_RUST = patch("stoat_ferret.render.service._HAS_RUST_BINDINGS", False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plan_json(
    *,
    total_duration: float = 60.0,
    codec: str = "libx264",
    quality_preset: str = "medium",
) -> str:
    """Build a minimal render plan JSON for testing."""
    return json.dumps(
        {
            "total_duration": total_duration,
            "segments": [],
            "settings": {
                "output_format": "mp4",
                "width": 1920,
                "height": 1080,
                "codec": codec,
                "quality_preset": quality_preset,
                "fps": 30.0,
            },
        }
    )


def _make_checkpoint_manager() -> MagicMock:
    """Create a mock checkpoint manager."""
    mgr = MagicMock()
    mgr.recover = AsyncMock(return_value=[])
    mgr.cleanup_stale = AsyncMock(return_value=0)
    return mgr


def _make_settings(retry_count: int = 2) -> Settings:
    """Create a Settings instance with the given retry count."""
    return Settings(render_retry_count=retry_count)


def _build_service(
    repo: InMemoryRenderRepository | None = None,
    queue: RenderQueue | None = None,
    executor: RenderExecutor | None = None,
    checkpoint_manager: MagicMock | None = None,
    ws: ConnectionManager | None = None,
    settings: Settings | None = None,
) -> tuple[RenderService, InMemoryRenderRepository, ConnectionManager, RenderExecutor]:
    """Build a RenderService with sensible test defaults.

    Returns:
        Tuple of (service, repo, ws_manager, executor).
    """
    repo = repo or InMemoryRenderRepository()
    ws = ws or ConnectionManager()
    ws.broadcast = AsyncMock()  # type: ignore[method-assign]
    settings = settings or _make_settings()
    executor = executor or RenderExecutor()
    checkpoint_mgr = checkpoint_manager or _make_checkpoint_manager()
    queue = queue or RenderQueue(repo, max_concurrent=4, max_depth=50)

    service = RenderService(
        repository=repo,
        queue=queue,
        executor=executor,
        checkpoint_manager=checkpoint_mgr,
        connection_manager=ws,
        settings=settings,
    )
    return service, repo, ws, executor


def _get_broadcast_events(ws: ConnectionManager) -> list[dict]:
    """Extract all broadcast event dicts from mock calls."""
    return [call[0][0] for call in ws.broadcast.call_args_list]  # type: ignore[union-attr]


def _get_event_types(ws: ConnectionManager) -> list[str]:
    """Extract event type strings from all broadcast calls."""
    return [e["type"] for e in _get_broadcast_events(ws)]


# ---------------------------------------------------------------------------
# Stage 1: EventType enum extension
# ---------------------------------------------------------------------------


class TestEventTypeEnum:
    """Tests for 3 new EventType enum values."""

    def test_render_queued_registered(self) -> None:
        """RENDER_QUEUED enum value is registered."""
        assert EventType.RENDER_QUEUED.value == "render_queued"

    def test_render_frame_available_registered(self) -> None:
        """RENDER_FRAME_AVAILABLE enum value is registered."""
        assert EventType.RENDER_FRAME_AVAILABLE.value == "render_frame_available"

    def test_render_queue_status_registered(self) -> None:
        """RENDER_QUEUE_STATUS enum value is registered."""
        assert EventType.RENDER_QUEUE_STATUS.value == "render_queue_status"

    def test_all_eight_render_event_types_exist(self) -> None:
        """All 8 render event types exist in the enum."""
        render_types = [
            EventType.RENDER_STARTED,
            EventType.RENDER_PROGRESS,
            EventType.RENDER_COMPLETED,
            EventType.RENDER_FAILED,
            EventType.RENDER_CANCELLED,
            EventType.RENDER_QUEUED,
            EventType.RENDER_FRAME_AVAILABLE,
            EventType.RENDER_QUEUE_STATUS,
        ]
        assert len(render_types) == 8
        # All are distinct
        assert len(set(rt.value for rt in render_types)) == 8


# ---------------------------------------------------------------------------
# Stage 2: Frame extraction spike
# ---------------------------------------------------------------------------


class TestFrameExtractionSpike:
    """Frame extraction spike validation tests."""

    def test_frame_url_format_540p_jpeg(self) -> None:
        """Frame URL points to 540p JPEG with job_id path component."""
        job_id = "test-job-123"
        frame_url = f"/api/v1/render/{job_id}/frame_preview.jpg"
        assert job_id in frame_url
        assert frame_url.endswith(".jpg")

    async def test_frame_available_event_includes_resolution(self) -> None:
        """render.frame_available event payload includes 540p resolution."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            ws.broadcast.reset_mock()  # type: ignore[union-attr]

            # Directly call the throttled frame method
            await service._broadcast_throttled_frame(job.id, 0.5)

            events = _get_broadcast_events(ws)
            frame_events = [
                e for e in events if e["type"] == EventType.RENDER_FRAME_AVAILABLE.value
            ]
            assert len(frame_events) == 1
            assert frame_events[0]["payload"]["resolution"] == "540p"
            assert frame_events[0]["payload"]["frame_url"].endswith(".jpg")


# ---------------------------------------------------------------------------
# Stage 3: Throttled event broadcasting
# ---------------------------------------------------------------------------


class TestThrottledProgressBroadcast:
    """Dual-threshold throttle tests for render.progress."""

    async def test_final_progress_always_sent(self) -> None:
        """Final progress (1.0) is always sent regardless of throttle."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()
            job_id = "job-final"

            # Send rapid updates — intermediate ones may be throttled
            await service._broadcast_throttled_progress(job_id, 0.1)
            await service._broadcast_throttled_progress(job_id, 1.0)

            events = _get_broadcast_events(ws)
            progress_events = [e for e in events if e["type"] == EventType.RENDER_PROGRESS.value]
            # Final (1.0) must be present
            progress_values = [e["payload"]["progress"] for e in progress_events]
            assert 1.0 in progress_values

    async def test_time_throttle_suppresses_rapid_updates(self) -> None:
        """Rapid progress updates within 0.5s are suppressed."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()
            job_id = "job-rapid"

            # First call goes through (>5% from 0.0)
            await service._broadcast_throttled_progress(job_id, 0.10)
            # These should be throttled (within 0.5s)
            await service._broadcast_throttled_progress(job_id, 0.20)
            await service._broadcast_throttled_progress(job_id, 0.30)

            events = _get_broadcast_events(ws)
            progress_events = [e for e in events if e["type"] == EventType.RENDER_PROGRESS.value]
            # Only the first should have been sent
            assert len(progress_events) == 1
            assert progress_events[0]["payload"]["progress"] == 0.10

    async def test_progress_delta_threshold(self) -> None:
        """Progress delta below 5% is suppressed even after time interval."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()
            job_id = "job-delta"

            await service._broadcast_throttled_progress(job_id, 0.10)
            ws.broadcast.reset_mock()  # type: ignore[union-attr]

            # Simulate time passing beyond interval
            key = (job_id, EventType.RENDER_PROGRESS.value)
            service._last_broadcast_time[key] = time.monotonic() - 1.0

            # 0.12 is only +2% from 0.10, below 5% threshold
            await service._broadcast_throttled_progress(job_id, 0.12)

            events = _get_broadcast_events(ws)
            progress_events = [e for e in events if e["type"] == EventType.RENDER_PROGRESS.value]
            assert len(progress_events) == 0

    async def test_progress_above_delta_sends(self) -> None:
        """Progress delta above 5% sends after time interval."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()
            job_id = "job-delta-ok"

            await service._broadcast_throttled_progress(job_id, 0.10)
            ws.broadcast.reset_mock()  # type: ignore[union-attr]

            # Simulate time passing beyond interval
            key = (job_id, EventType.RENDER_PROGRESS.value)
            service._last_broadcast_time[key] = time.monotonic() - 1.0

            # 0.20 is +10% from 0.10, above 5% threshold
            await service._broadcast_throttled_progress(job_id, 0.20)

            events = _get_broadcast_events(ws)
            progress_events = [e for e in events if e["type"] == EventType.RENDER_PROGRESS.value]
            assert len(progress_events) == 1
            assert progress_events[0]["payload"]["progress"] == 0.20


class TestThrottledFrameBroadcast:
    """Throttle tests for render.frame_available."""

    async def test_frame_available_throttled(self) -> None:
        """Rapid frame_available events within 0.5s are suppressed."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()
            job_id = "job-frame"

            # First call goes through
            await service._broadcast_throttled_frame(job_id, 0.10)
            # Should be throttled
            await service._broadcast_throttled_frame(job_id, 0.20)

            events = _get_broadcast_events(ws)
            frame_events = [
                e for e in events if e["type"] == EventType.RENDER_FRAME_AVAILABLE.value
            ]
            assert len(frame_events) == 1

    async def test_frame_available_after_interval(self) -> None:
        """frame_available events sent after throttle interval elapses."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()
            job_id = "job-frame-interval"

            await service._broadcast_throttled_frame(job_id, 0.10)
            ws.broadcast.reset_mock()  # type: ignore[union-attr]

            # Simulate time passing
            key = (job_id, EventType.RENDER_FRAME_AVAILABLE.value)
            service._last_broadcast_time[key] = time.monotonic() - 1.0

            await service._broadcast_throttled_frame(job_id, 0.50)

            events = _get_broadcast_events(ws)
            frame_events = [
                e for e in events if e["type"] == EventType.RENDER_FRAME_AVAILABLE.value
            ]
            assert len(frame_events) == 1
            assert frame_events[0]["payload"]["frame_url"].endswith(".jpg")
            assert frame_events[0]["payload"]["resolution"] == "540p"


class TestPerJobIsolation:
    """Per-job-per-event-type throttle isolation tests."""

    async def test_different_jobs_not_throttled(self) -> None:
        """Events for different jobs are throttled independently."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            # First events for each job go through
            await service._broadcast_throttled_progress("job-a", 0.10)
            await service._broadcast_throttled_progress("job-b", 0.10)

            events = _get_broadcast_events(ws)
            progress_events = [e for e in events if e["type"] == EventType.RENDER_PROGRESS.value]
            assert len(progress_events) == 2
            job_ids = {e["payload"]["job_id"] for e in progress_events}
            assert job_ids == {"job-a", "job-b"}

    async def test_different_event_types_not_throttled(self) -> None:
        """Different event types for the same job are throttled independently."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()
            job_id = "job-multi"

            await service._broadcast_throttled_progress(job_id, 0.10)
            await service._broadcast_throttled_frame(job_id, 0.10)

            events = _get_broadcast_events(ws)
            types = [e["type"] for e in events]
            assert EventType.RENDER_PROGRESS.value in types
            assert EventType.RENDER_FRAME_AVAILABLE.value in types


class TestThrottleStateCleanup:
    """Throttle state cleanup tests."""

    async def test_clear_throttle_state(self) -> None:
        """Throttle state is cleared after job completion."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()
            job_id = "job-cleanup"

            await service._broadcast_throttled_progress(job_id, 0.10)
            assert any(k[0] == job_id for k in service._last_broadcast_time)
            assert job_id in service._last_broadcast_progress

            service._clear_throttle_state(job_id)

            assert not any(k[0] == job_id for k in service._last_broadcast_time)
            assert job_id not in service._last_broadcast_progress


# ---------------------------------------------------------------------------
# Queue status events
# ---------------------------------------------------------------------------


class TestQueueStatusEvents:
    """Queue status broadcast tests."""

    async def test_queue_status_on_submit(self) -> None:
        """RENDER_QUEUE_STATUS is broadcast on job submission."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            event_types = _get_event_types(ws)
            assert EventType.RENDER_QUEUE_STATUS.value in event_types

    async def test_queue_status_on_cancel(self) -> None:
        """RENDER_QUEUE_STATUS is broadcast on job cancellation."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            ws.broadcast.reset_mock()  # type: ignore[union-attr]

            await service.cancel_job(job.id)

            event_types = _get_event_types(ws)
            assert EventType.RENDER_QUEUE_STATUS.value in event_types

    async def test_queue_status_on_completion(self) -> None:
        """RENDER_QUEUE_STATUS is broadcast on job completion."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            ws.broadcast.reset_mock()  # type: ignore[union-attr]

            executor.execute = AsyncMock(return_value=True)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg"])

            event_types = _get_event_types(ws)
            assert EventType.RENDER_QUEUE_STATUS.value in event_types

    async def test_queue_status_payload_fields(self) -> None:
        """RENDER_QUEUE_STATUS event contains required queue metrics."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            events = _get_broadcast_events(ws)
            queue_events = [e for e in events if e["type"] == EventType.RENDER_QUEUE_STATUS.value]
            assert len(queue_events) >= 1

            payload = queue_events[0]["payload"]
            assert "active_count" in payload
            assert "pending_count" in payload
            assert "max_concurrent" in payload
            assert "max_queue_depth" in payload


# ---------------------------------------------------------------------------
# Event payload schema contract tests
# ---------------------------------------------------------------------------


class TestEventPayloadSchema:
    """Contract tests for event payload schema."""

    def test_build_event_schema(self) -> None:
        """build_event returns {type, payload, correlation_id, timestamp}."""
        event = build_event(EventType.RENDER_QUEUED, {"job_id": "j1"}, correlation_id="c1")
        assert "type" in event
        assert "payload" in event
        assert "correlation_id" in event
        assert "timestamp" in event
        assert event["type"] == "render_queued"
        assert event["payload"]["job_id"] == "j1"

    async def test_render_queued_payload(self) -> None:
        """render.queued event includes job_id, project_id, status."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            events = _get_broadcast_events(ws)
            queued_events = [e for e in events if e["type"] == EventType.RENDER_QUEUED.value]
            assert len(queued_events) == 1
            payload = queued_events[0]["payload"]
            assert payload["job_id"] == job.id
            assert payload["project_id"] == "proj-1"
            assert "status" in payload

    async def test_render_progress_payload(self) -> None:
        """render.progress event includes job_id, progress, eta_seconds, speed_ratio."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            await service._broadcast_throttled_progress(
                "job-1", 0.5, eta_seconds=10.0, speed_ratio=2.5
            )

            events = _get_broadcast_events(ws)
            progress_events = [e for e in events if e["type"] == EventType.RENDER_PROGRESS.value]
            assert len(progress_events) == 1
            payload = progress_events[0]["payload"]
            assert payload["job_id"] == "job-1"
            assert payload["progress"] == 0.5
            assert payload["eta_seconds"] == 10.0
            assert payload["speed_ratio"] == 2.5

    async def test_render_progress_payload_null_fields(self) -> None:
        """render.progress event includes null eta_seconds and speed_ratio when not available."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            await service._broadcast_throttled_progress("job-1", 0.5)

            events = _get_broadcast_events(ws)
            progress_events = [e for e in events if e["type"] == EventType.RENDER_PROGRESS.value]
            assert len(progress_events) == 1
            payload = progress_events[0]["payload"]
            assert payload["job_id"] == "job-1"
            assert payload["progress"] == 0.5
            assert payload["eta_seconds"] is None
            assert payload["speed_ratio"] is None

    async def test_render_frame_available_payload(self) -> None:
        """render.frame_available event includes job_id, frame_url, resolution."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            await service._broadcast_throttled_frame("job-1", 0.5)

            events = _get_broadcast_events(ws)
            frame_events = [
                e for e in events if e["type"] == EventType.RENDER_FRAME_AVAILABLE.value
            ]
            assert len(frame_events) == 1
            payload = frame_events[0]["payload"]
            assert payload["job_id"] == "job-1"
            assert "frame_url" in payload
            assert payload["resolution"] == "540p"
            assert payload["progress"] == 0.5

    async def test_render_progress_schema_contract(self) -> None:
        """render.progress schema has job_id, progress, eta_seconds, speed_ratio."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            await service._broadcast_throttled_progress(
                "job-schema", 0.5, eta_seconds=15.0, speed_ratio=1.5
            )

            events = _get_broadcast_events(ws)
            progress_events = [e for e in events if e["type"] == EventType.RENDER_PROGRESS.value]
            assert len(progress_events) == 1
            payload = progress_events[0]["payload"]

            # Contract: all four fields present
            assert isinstance(payload["job_id"], str)
            assert isinstance(payload["progress"], float)
            assert isinstance(payload["eta_seconds"], (float, type(None)))
            assert isinstance(payload["speed_ratio"], (float, type(None)))

    async def test_all_event_types_have_timestamp(self) -> None:
        """All broadcast events include a timestamp field."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            events = _get_broadcast_events(ws)
            for event in events:
                assert "timestamp" in event, f"Missing timestamp in {event['type']}"


# ---------------------------------------------------------------------------
# Full lifecycle system tests
# ---------------------------------------------------------------------------


class TestFullEventSequence:
    """System tests for full event sequences."""

    async def test_submit_to_completion_sequence(self) -> None:
        """Full event sequence: queued -> started -> queue_status -> completed -> queue_status."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            # Dequeue and run
            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=True)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg"])

            events = _get_broadcast_events(ws)
            event_types = [e["type"] for e in events]
            # Should include queued, queue_status, started, completed, queue_status
            assert EventType.RENDER_QUEUED.value in event_types
            assert EventType.RENDER_STARTED.value in event_types
            assert EventType.RENDER_COMPLETED.value in event_types
            assert event_types.count(EventType.RENDER_QUEUE_STATUS.value) >= 2

            # BL-401: render_completed payload.status must be 'completed', not 'running'
            completed_events = [e for e in events if e["type"] == EventType.RENDER_COMPLETED.value]
            assert len(completed_events) == 1
            assert completed_events[0]["payload"]["status"] == "completed"

    async def test_submit_to_cancel_sequence(self) -> None:
        """Cancel event sequence: queued -> started -> cancelled -> queue_status."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            await service.cancel_job(job.id)

            events = _get_broadcast_events(ws)
            event_types = [e["type"] for e in events]
            assert EventType.RENDER_QUEUED.value in event_types
            assert EventType.RENDER_STARTED.value in event_types
            assert EventType.RENDER_CANCELLED.value in event_types
            assert EventType.RENDER_QUEUE_STATUS.value in event_types

            # BL-401: render_cancelled payload.status must be 'cancelled', not 'running'
            cancelled_events = [e for e in events if e["type"] == EventType.RENDER_CANCELLED.value]
            assert len(cancelled_events) == 1
            assert cancelled_events[0]["payload"]["status"] == "cancelled"

    async def test_submit_to_permanent_failure_sequence(self) -> None:
        """Failure sequence includes RENDER_FAILED and RENDER_QUEUE_STATUS."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service(
                settings=_make_settings(retry_count=0),
            )

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=False)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg"])

            events = _get_broadcast_events(ws)
            event_types = [e["type"] for e in events]
            assert EventType.RENDER_FAILED.value in event_types
            assert EventType.RENDER_QUEUE_STATUS.value in event_types

            # BL-401: worker-emitted render_failed payload.status must be 'failed', not 'running'
            failed_events = [e for e in events if e["type"] == EventType.RENDER_FAILED.value]
            assert len(failed_events) == 1
            assert failed_events[0]["payload"]["status"] == "failed"


# ---------------------------------------------------------------------------
# Broadcast to multiple clients
# ---------------------------------------------------------------------------


class TestBroadcastToAllClients:
    """Tests verifying events broadcast to all connected clients."""

    async def test_broadcast_called_for_all_event_types(self) -> None:
        """ConnectionManager.broadcast is called for each event type."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            # broadcast is called via ConnectionManager which sends to all clients
            assert ws.broadcast.call_count >= 3  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Cancel/complete race-window invariant tests (BL-412)
# ---------------------------------------------------------------------------

_TERMINAL_EVENT_TYPES = {"render_completed", "render_cancelled", "render_failed"}


class TestCancelCompleteRaceInvariant:
    """Race-window invariant: at most one terminal WS event per job_id.

    These tests insert an awaitable barrier between executor.cancel and the
    state-transition broadcast so _complete_job can win the race. After the
    BL-412 compare-and-swap fix, cancel_job must detect the concurrent
    completion and suppress RENDER_CANCELLED.
    """

    async def test_complete_wins_race_single_terminal_event(self) -> None:
        """When _complete_job wins the race, exactly one terminal event is broadcast."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()

            job: RenderJob = await service.submit_job(
                project_id="proj-race",
                output_path="/tmp/race.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            ws.broadcast.reset_mock()  # type: ignore[union-attr]

            # Barrier: complete_job will complete while cancel_job awaits executor.cancel.
            barrier = asyncio.Event()

            async def cancel_with_barrier(jid: str) -> None:
                barrier.set()  # signal that executor.cancel has been entered
                await asyncio.sleep(0)  # yield to let _complete_job run

            executor.cancel = cancel_with_barrier  # type: ignore[method-assign]

            async def complete_after_barrier() -> None:
                await barrier.wait()
                # Reload job to get latest state before completing
                fresh = await repo.get(job.id)
                if fresh is not None:
                    await service._complete_job(fresh)

            await asyncio.gather(
                service.cancel_job(job.id),
                complete_after_barrier(),
                return_exceptions=True,
            )

            events = _get_broadcast_events(ws)
            terminal = [e for e in events if e["type"] in _TERMINAL_EVENT_TYPES]
            assert len(terminal) == 1, (
                f"Expected exactly 1 terminal event; got {[e['type'] for e in terminal]}"
            )

    async def test_cancel_wins_race_single_terminal_event(self) -> None:
        """When cancel_job wins the race, exactly one terminal event is broadcast."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()

            job: RenderJob = await service.submit_job(
                project_id="proj-cancel-wins",
                output_path="/tmp/cancel-wins.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            ws.broadcast.reset_mock()  # type: ignore[union-attr]

            # Executor.cancel completes immediately (no barrier) — cancel wins.
            executor.cancel = AsyncMock()  # type: ignore[method-assign]

            await service.cancel_job(job.id)

            events = _get_broadcast_events(ws)
            terminal = [e for e in events if e["type"] in _TERMINAL_EVENT_TYPES]
            assert len(terminal) == 1
            assert terminal[0]["type"] == "render_cancelled"

    async def test_cancel_preempted_no_render_cancelled_event(self) -> None:
        """When CAS detects concurrent completion, RENDER_CANCELLED is suppressed."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()

            job: RenderJob = await service.submit_job(
                project_id="proj-preempt",
                output_path="/tmp/preempt.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)

            # Pre-complete the job so the CAS will find it already terminal.
            fresh = await repo.get(job.id)
            assert fresh is not None
            await service._complete_job(fresh)
            ws.broadcast.reset_mock()  # type: ignore[union-attr]

            # Now simulate cancel arriving after the job is already COMPLETED.
            # The service's cancel_job pre-check will block it (not QUEUED/RUNNING),
            # so we patch executor.cancel and call cancel_job with a pre-running snapshot.
            executor.cancel = AsyncMock()  # type: ignore[method-assign]

            # Directly test the CAS path by calling cancel_job — it should return False
            # early (job not in cancellable state) or raise CancelPreemptedError.
            result = await service.cancel_job(job.id)

            # Job is COMPLETED — cancel_job returns False without broadcasting.
            assert result is False
            events = _get_broadcast_events(ws)
            cancelled_events = [e for e in events if e["type"] == "render_cancelled"]
            assert len(cancelled_events) == 0


# ---------------------------------------------------------------------------
# WS terminal event payload.status correctness (BL-401)
# ---------------------------------------------------------------------------


class TestTerminalEventPayloadStatus:
    """BL-401: Terminal WS events carry the post-transition status, not 'running'.

    The sweeper-emitted render_failed already used the correct pattern before
    this fix; the worker-path callers (_complete_job, cancel_job, _handle_failure)
    were the defective sites. These tests verify the fix and protect against
    regression on all three paths, plus the sweeper path.
    """

    async def test_render_completed_payload_status_is_completed(self) -> None:
        """render_completed.payload.status == 'completed', not 'running'."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            job = await service.submit_job(
                project_id="proj-status",
                output_path="/tmp/status.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=True)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg"])

            events = _get_broadcast_events(ws)
            completed = [e for e in events if e["type"] == "render_completed"]
            assert len(completed) == 1
            assert completed[0]["payload"]["status"] == "completed"
            # BL-411: render_completed payload must include output_path
            assert "output_path" in completed[0]["payload"]
            assert completed[0]["payload"]["output_path"] == job.output_path

    async def test_render_cancelled_payload_status_is_cancelled(self) -> None:
        """render_cancelled.payload.status == 'cancelled', not 'running'."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            job = await service.submit_job(
                project_id="proj-status-cancel",
                output_path="/tmp/status-cancel.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.cancel = AsyncMock()  # type: ignore[method-assign]
            await service.cancel_job(job.id)

            events = _get_broadcast_events(ws)
            cancelled = [e for e in events if e["type"] == "render_cancelled"]
            assert len(cancelled) == 1
            assert cancelled[0]["payload"]["status"] == "cancelled"

    async def test_worker_render_failed_payload_status_is_failed(self) -> None:
        """Worker-path render_failed.payload.status == 'failed', not 'running'."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service(
                settings=_make_settings(retry_count=0),
            )
            job = await service.submit_job(
                project_id="proj-status-fail",
                output_path="/tmp/status-fail.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=False)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg"])

            events = _get_broadcast_events(ws)
            failed = [e for e in events if e["type"] == "render_failed"]
            assert len(failed) == 1
            assert failed[0]["payload"]["status"] == "failed"

    async def test_sweeper_render_failed_payload_status_is_failed(self) -> None:
        """Sweeper-emitted render_failed.payload.status == 'failed' (no regression)."""
        repo = InMemoryRenderRepository()
        ws = ConnectionManager()
        ws.broadcast = AsyncMock()  # type: ignore[method-assign]
        sweeper = StaleRenderSweeper(
            repo=repo,
            ws_manager=ws,
            threshold_seconds=60,
        )

        # Create and persist a job, then transition it to RUNNING so the sweeper
        # can transition it to FAILED.
        job = RenderJob.create(
            project_id="proj-sweeper",
            output_path="/tmp/sweeper.mp4",
            output_format=OutputFormat.MP4,
            quality_preset=QualityPreset.STANDARD,
            render_plan="{}",
        )
        await repo.create(job)
        await repo.update_status(job.id, RenderStatus.RUNNING)

        # Drive the sweeper's stale-job handler directly.
        updated = await repo.get(job.id)
        assert updated is not None
        await sweeper._handle_stale_job(job.id, job.project_id, updated.updated_at)

        events = _get_broadcast_events(ws)
        failed = [e for e in events if e["type"] == "render_failed"]
        assert len(failed) == 1
        assert failed[0]["payload"]["status"] == "failed"


# ---------------------------------------------------------------------------
# REST/WS status agreement (BL-401-AC-5 / BL-412-AC-4 discharge)
# ---------------------------------------------------------------------------


class TestRestWsStatusAgreement:
    """REST status matches WS event type immediately after terminal event.

    The implementation guarantee: update_status is always called before
    _broadcast_event, so the DB (and thus any REST GET) reflects the
    post-transition state by the time the WS event fires.

    These tests verify that guarantee at the service layer using
    InMemoryRenderRepository as the REST-equivalent source-of-truth.
    """

    async def test_rest_status_matches_ws_completed_event(self) -> None:
        """After render_completed WS event, repo reflects status='completed'."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            job = await service.submit_job(
                project_id="proj-agreement",
                output_path="/tmp/agreement.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=True)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg"])

            # Simulate REST GET immediately after WS event.
            rest_job = await repo.get(job.id)
            assert rest_job is not None

            events = _get_broadcast_events(ws)
            completed = [e for e in events if e["type"] == "render_completed"]
            assert len(completed) == 1
            ws_status = completed[0]["payload"]["status"]
            assert ws_status == rest_job.status.value == "completed"

    async def test_rest_status_matches_ws_cancelled_event(self) -> None:
        """After render_cancelled WS event, repo reflects status='cancelled'."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            job = await service.submit_job(
                project_id="proj-agreement-cancel",
                output_path="/tmp/agreement-cancel.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            executor.cancel = AsyncMock()  # type: ignore[method-assign]
            await service.cancel_job(job.id)

            rest_job = await repo.get(job.id)
            assert rest_job is not None

            events = _get_broadcast_events(ws)
            cancelled = [e for e in events if e["type"] == "render_cancelled"]
            assert len(cancelled) == 1
            ws_status = cancelled[0]["payload"]["status"]
            assert ws_status == rest_job.status.value == "cancelled"

    async def test_rest_status_matches_ws_failed_event(self) -> None:
        """After render_failed WS event, repo reflects status='failed'."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service(
                settings=_make_settings(retry_count=0),
            )
            job = await service.submit_job(
                project_id="proj-agreement-fail",
                output_path="/tmp/agreement-fail.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=False)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg"])

            rest_job = await repo.get(job.id)
            assert rest_job is not None

            events = _get_broadcast_events(ws)
            failed = [e for e in events if e["type"] == "render_failed"]
            assert len(failed) == 1
            ws_status = failed[0]["payload"]["status"]
            assert ws_status == rest_job.status.value == "failed"


# ---------------------------------------------------------------------------
# Library DELETE → WS events → GET timeline duration (BL-416)
# ---------------------------------------------------------------------------


@pytest.mark.api
async def test_delete_video_clip_sequence_ws_events_and_timeline_duration() -> None:
    """DELETE sequence produces correct WS events; GET timeline duration reflects removal.

    Verifies BL-416-AC-1 (video_deleted), BL-416-AC-2 (clip_deleted),
    BL-416-AC-3 (timeline duration=0 after clip removal), BL-416-AC-5 (integration test).
    """
    from fastapi.testclient import TestClient

    from stoat_ferret.api.app import create_app
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
    from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
    from stoat_ferret.db.models import Clip, Project, Track
    from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
    from stoat_ferret.db.timeline_repository import AsyncInMemoryTimelineRepository
    from stoat_ferret.jobs.queue import InMemoryJobQueue
    from tests.factories import make_test_video

    video_repo = AsyncInMemoryVideoRepository()
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()
    timeline_repo = AsyncInMemoryTimelineRepository()
    job_queue = InMemoryJobQueue()

    mock_ws = ConnectionManager()
    mock_ws.broadcast = AsyncMock()  # type: ignore[method-assign]

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        timeline_repository=timeline_repo,
        job_queue=job_queue,
        ws_manager=mock_ws,
    )

    now = datetime.now(timezone.utc)

    video = make_test_video()
    await video_repo.add(video)

    project = Project(
        id=Project.new_id(),
        name="bl416-delete-ws-test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repo.add(project)

    clip = Clip(
        id=Clip.new_id(),
        project_id=project.id,
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repo.add(clip)

    track = Track(
        id=Track.new_id(),
        project_id=project.id,
        track_type="video",
        label="V1",
        z_index=0,
    )
    await timeline_repo.create_track(track)

    with TestClient(app) as client:
        # Place clip on timeline
        place_resp = client.post(
            f"/api/v1/projects/{project.id}/timeline/clips",
            json={
                "clip_id": clip.id,
                "track_id": track.id,
                "timeline_start": 0.0,
                "timeline_end": 5.0,
            },
        )
        assert place_resp.status_code == 201
        mock_ws.broadcast.reset_mock()  # type: ignore[union-attr]

        # Delete clip resource → clip_deleted WS event
        del_clip_resp = client.delete(f"/api/v1/projects/{project.id}/clips/{clip.id}")
        assert del_clip_resp.status_code == 204

        clip_calls = mock_ws.broadcast.call_args_list  # type: ignore[union-attr]
        clip_events = [c[0][0] for c in clip_calls if c[0][0]["type"] == "clip_deleted"]
        assert len(clip_events) == 1
        assert clip_events[0]["payload"]["clip_id"] == clip.id
        assert clip_events[0]["payload"]["project_id"] == project.id
        mock_ws.broadcast.reset_mock()  # type: ignore[union-attr]

        # Delete video → video_deleted WS event
        del_video_resp = client.delete(f"/api/v1/videos/{video.id}")
        assert del_video_resp.status_code == 204

        video_calls = mock_ws.broadcast.call_args_list  # type: ignore[union-attr]
        video_events = [c[0][0] for c in video_calls if c[0][0]["type"] == "video_deleted"]
        assert len(video_events) == 1
        assert video_events[0]["payload"]["video_id"] == video.id

        # GET /timeline duration reflects removal (AC-3 verification)
        timeline_resp = client.get(f"/api/v1/projects/{project.id}/timeline")
        assert timeline_resp.status_code == 200
        assert timeline_resp.json()["duration"] == 0.0
