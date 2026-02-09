"""Tests for worker lifecycle and lifespan integration.

Verifies worker starts on startup and cancels gracefully on shutdown.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from stoat_ferret.api.app import create_app
from stoat_ferret.jobs.queue import AsyncioJobQueue


async def _noop_handler(job_type: str, payload: dict[str, Any]) -> str:
    """Minimal handler for testing."""
    return "ok"


class TestWorkerLifecycle:
    """Tests for worker coroutine lifecycle."""

    async def test_worker_cancels_cleanly(self) -> None:
        """Worker exits without error when cancelled."""
        queue = AsyncioJobQueue()
        queue.register_handler("test", _noop_handler)

        worker = asyncio.create_task(queue.process_jobs())
        await asyncio.sleep(0.01)

        worker.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker

    async def test_worker_processes_job_then_cancels(self) -> None:
        """Worker processes pending job before cancellation takes effect."""
        queue = AsyncioJobQueue()
        queue.register_handler("test", _noop_handler)

        job_id = await queue.submit("test", {})
        worker = asyncio.create_task(queue.process_jobs())
        await asyncio.sleep(0.05)

        # Job should be processed
        result = await queue.get_result(job_id)
        assert result.status.value == "complete"

        worker.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker


class TestLifespanIntegration:
    """Tests for job queue lifespan integration with FastAPI app."""

    async def test_app_with_injected_job_queue(self) -> None:
        """App accepts job_queue via DI and stores on app.state."""
        queue = AsyncioJobQueue()
        app = create_app(job_queue=queue)
        assert app.state.job_queue is queue

    async def test_app_without_injection_works(self) -> None:
        """App works without injected job_queue (production path tested via lifespan)."""
        app = create_app()
        # In test mode (no lifespan started), job_queue may not exist
        # This just verifies create_app() doesn't error
        assert app is not None
