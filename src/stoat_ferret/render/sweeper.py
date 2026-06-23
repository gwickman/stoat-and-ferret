# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Stale render job sweeper background task.

Detects render jobs stuck in status='running' beyond the configured threshold
and transitions them to status='failed', reducing MTTR from hours to seconds.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import structlog

from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.render.models import RenderStatus
from stoat_ferret.render.render_repository import AsyncRenderRepository

logger = structlog.get_logger(__name__)


class StaleRenderSweeper:
    """Background task that recovers stale running render jobs.

    Polls render_jobs on a configurable interval for jobs in status='running'
    whose updated_at is older than threshold_seconds. Transitions each stale
    job to status='failed' and emits dual events: a WebSocket RENDER_FAILED
    event for clients and a render.job_stale structured log for monitoring.

    Args:
        repo: Async render repository for querying and updating jobs.
        ws_manager: WebSocket connection manager for broadcasting events.
        threshold_seconds: Age in seconds beyond which a running job is stale.
        sweep_interval: Seconds between sweep passes (default 60).
    """

    def __init__(
        self,
        *,
        repo: AsyncRenderRepository,
        ws_manager: ConnectionManager,
        threshold_seconds: int,
        sweep_interval: int = 60,
    ) -> None:
        self._repo = repo
        self._ws = ws_manager
        self._threshold_seconds = threshold_seconds
        self._sweep_interval = sweep_interval

    async def run(self) -> None:
        """Main sweeper loop — runs until cancelled via asyncio.CancelledError."""
        while True:
            await asyncio.sleep(self._sweep_interval)
            older_than = datetime.now(timezone.utc) - timedelta(seconds=self._threshold_seconds)
            try:
                stale_jobs = await self._repo.list_stale_running(older_than)
            except Exception:
                logger.warning("render.sweeper_error", exc_info=True)
                continue

            for job in stale_jobs:
                await self._handle_stale_job(job.id, job.project_id, job.updated_at)

    async def _handle_stale_job(self, job_id: str, project_id: str, stale_since: datetime) -> None:
        """Attempt to transition one stale job to failed and emit events."""
        error_message = (
            f"Render job terminated by stale-running sweeper: "
            f"no activity for {self._threshold_seconds}s"
        )
        try:
            await self._repo.update_status(
                job_id,
                RenderStatus.FAILED,
                error_message=error_message,
            )
        except ValueError:
            # Concurrent path already transitioned this job — not an error.
            logger.info("render.sweeper_concurrent_skip", job_id=job_id)
            return
        except Exception:
            logger.warning("render.sweeper_job_error", job_id=job_id, exc_info=True)
            return

        logger.info(
            "render.job_stale",
            job_id=job_id,
            threshold_seconds=self._threshold_seconds,
            stale_since=stale_since.isoformat(),
        )
        try:
            await self._ws.broadcast(
                build_event(
                    EventType.RENDER_FAILED,
                    {
                        "job_id": job_id,
                        "project_id": project_id,
                        "status": RenderStatus.FAILED.value,
                    },
                    job_id=job_id,
                )
            )
        except Exception:
            logger.warning("render.sweeper_broadcast_error", job_id=job_id, exc_info=True)
