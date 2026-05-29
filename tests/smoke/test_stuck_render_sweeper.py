"""Smoke tests for StaleRenderSweeper background task (BL-389).

Verifies that:
- A running job whose updated_at is older than threshold is transitioned to failed.
- A recently updated running job is not affected.
- The sweeper emits a RENDER_FAILED WebSocket event on successful transition.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Any

from stoat_ferret.api.websocket.events import EventType
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.sweeper import StaleRenderSweeper


class _MockWSManager:
    """Minimal WebSocket manager stub that records broadcast calls."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def broadcast(self, event: dict[str, Any]) -> None:
        self.events.append(event)


def _make_job() -> RenderJob:
    return RenderJob.create(
        project_id="test-project-id",
        output_path="data/renders/test.mp4",
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan='{"total_duration": 10.0, "segments": [], "settings": {}}',
    )


async def test_sweeper_transitions_stale_running_job_to_failed() -> None:
    """A running job older than threshold is transitioned to failed within one sweep."""
    repo = InMemoryRenderRepository()
    ws = _MockWSManager()

    job = _make_job()
    await repo.create(job)
    await repo.update_status(job.id, RenderStatus.RUNNING)

    # Backdate updated_at so the job is older than threshold + margin
    threshold = 300
    repo._jobs[job.id].updated_at = datetime.now(timezone.utc) - timedelta(seconds=threshold + 60)

    sweeper = StaleRenderSweeper(
        repo=repo,
        ws_manager=ws,  # type: ignore[arg-type]
        threshold_seconds=threshold,
        sweep_interval=1,
    )

    task = asyncio.create_task(sweeper.run())
    await asyncio.sleep(2)
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

    updated = await repo.get(job.id)
    assert updated is not None
    assert updated.status == RenderStatus.FAILED
    assert updated.error_message is not None
    assert "stale" in updated.error_message.lower()

    failed_events = [e for e in ws.events if e.get("type") == EventType.RENDER_FAILED.value]
    assert len(failed_events) == 1
    assert failed_events[0]["payload"]["job_id"] == job.id


async def test_sweeper_does_not_affect_recent_running_jobs() -> None:
    """A running job updated recently is not transitioned by the sweeper."""
    repo = InMemoryRenderRepository()
    ws = _MockWSManager()

    job = _make_job()
    await repo.create(job)
    await repo.update_status(job.id, RenderStatus.RUNNING)
    # updated_at is now — not stale relative to threshold=300s

    sweeper = StaleRenderSweeper(
        repo=repo,
        ws_manager=ws,  # type: ignore[arg-type]
        threshold_seconds=300,
        sweep_interval=1,
    )

    task = asyncio.create_task(sweeper.run())
    await asyncio.sleep(2)
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

    updated = await repo.get(job.id)
    assert updated is not None
    assert updated.status == RenderStatus.RUNNING

    failed_events = [e for e in ws.events if e.get("type") == EventType.RENDER_FAILED.value]
    assert len(failed_events) == 0


async def test_sweeper_skips_already_terminal_jobs() -> None:
    """If a job was concurrently transitioned, the sweeper logs INFO and skips it."""
    repo = InMemoryRenderRepository()
    ws = _MockWSManager()

    job = _make_job()
    await repo.create(job)
    await repo.update_status(job.id, RenderStatus.RUNNING)
    # Backdate to appear stale
    threshold = 300
    repo._jobs[job.id].updated_at = datetime.now(timezone.utc) - timedelta(seconds=threshold + 60)
    # Simulate concurrent path already transitioning the job
    repo._jobs[job.id].status = RenderStatus.CANCELLED

    sweeper = StaleRenderSweeper(
        repo=repo,
        ws_manager=ws,  # type: ignore[arg-type]
        threshold_seconds=threshold,
        sweep_interval=1,
    )

    # Should complete without raising
    task = asyncio.create_task(sweeper.run())
    await asyncio.sleep(2)
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

    # Job remains in its concurrently-set terminal state
    updated = await repo.get(job.id)
    assert updated is not None
    assert updated.status == RenderStatus.CANCELLED
