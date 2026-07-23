# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for RenderService submit_job lock acquisition.

Verifies that submit_job acquires _submit_lock before mutating state
in noop mode, serializing concurrent noop submissions (BL-388).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.render.checkpoints import RenderCheckpointManager
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.models import OutputFormat, QualityPreset
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import RenderService


def _make_noop_service(render_repo: InMemoryRenderRepository) -> RenderService:
    """Create a RenderService in noop mode with mocked peripherals."""
    ws = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock()

    checkpoint_mgr = MagicMock(spec=RenderCheckpointManager)
    checkpoint_mgr.cleanup_stale = AsyncMock(return_value=0)

    return RenderService(
        repository=render_repo,
        queue=RenderQueue(render_repo),
        executor=MagicMock(spec=RenderExecutor),
        checkpoint_manager=checkpoint_mgr,
        connection_manager=ws,
        settings=Settings(render_mode="noop"),
    )


_NOOP_PLAN = '{"total_duration": 5.0, "settings": {"quality_preset": "medium"}}'


class TestSubmitJobLockAcquisition:
    """Verify _submit_lock is acquired before state mutation in noop mode."""

    def test_submit_lock_attribute_exists(self) -> None:
        """RenderService has _submit_lock attribute of type asyncio.Lock."""
        service = _make_noop_service(InMemoryRenderRepository())
        assert hasattr(service, "_submit_lock")
        assert isinstance(service._submit_lock, asyncio.Lock)

    async def test_submit_lock_acquired_during_noop_submission(self) -> None:
        """_submit_lock is held while noop state mutation executes."""
        repo = InMemoryRenderRepository()
        service = _make_noop_service(repo)

        lock_was_locked_during_create: list[bool] = []

        original_create = repo.create

        async def spy_create(job):  # type: ignore[no-untyped-def]
            lock_was_locked_during_create.append(service._submit_lock.locked())
            return await original_create(job)

        repo.create = spy_create  # type: ignore[method-assign]

        await service.submit_job(
            project_id="proj-1",
            output_path="/tmp/out.mp4",
            output_format=OutputFormat.MP4,
            quality_preset=QualityPreset.STANDARD,
            render_plan_json=_NOOP_PLAN,
        )

        assert lock_was_locked_during_create == [True], (
            "Lock must be held when repo.create() is called"
        )

    async def test_submit_lock_released_after_noop_submission(self) -> None:
        """_submit_lock is released after noop submission completes."""
        repo = InMemoryRenderRepository()
        service = _make_noop_service(repo)

        await service.submit_job(
            project_id="proj-1",
            output_path="/tmp/out.mp4",
            output_format=OutputFormat.MP4,
            quality_preset=QualityPreset.STANDARD,
            render_plan_json=_NOOP_PLAN,
        )

        assert not service._submit_lock.locked(), "Lock must be released after submission"
