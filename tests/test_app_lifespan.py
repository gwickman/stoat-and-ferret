"""Integration tests for app lifespan: render worker registration and shutdown.

Runs the full FastAPI lifespan with an isolated temp SQLite database to verify
that RenderWorkerLoop is registered on app.state during startup and cancelled
cleanly on shutdown.
"""

from __future__ import annotations

import asyncio
import os
import time
from unittest.mock import AsyncMock, MagicMock

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.api.settings import get_settings
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.service import RenderService
from stoat_ferret.render.worker import RenderWorkerLoop


def _setup_isolated_env(tmp_path, suffix: str = "") -> tuple[str | None, str | None]:
    """Configure env vars for an isolated lifespan test.

    Returns (orig_db, orig_thumb) for restoration after the test.
    """
    db_path = str(tmp_path / f"lifespan_test{suffix}.db")
    orig_db = os.environ.get("STOAT_DATABASE_PATH")
    orig_thumb = os.environ.get("STOAT_THUMBNAIL_DIR")
    os.environ["STOAT_DATABASE_PATH"] = db_path
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")
    get_settings.cache_clear()
    return orig_db, orig_thumb


def _restore_env(orig_db: str | None, orig_thumb: str | None) -> None:
    """Restore env vars after an isolated lifespan test."""
    if orig_db is None:
        os.environ.pop("STOAT_DATABASE_PATH", None)
    else:
        os.environ["STOAT_DATABASE_PATH"] = orig_db
    if orig_thumb is None:
        os.environ.pop("STOAT_THUMBNAIL_DIR", None)
    else:
        os.environ["STOAT_THUMBNAIL_DIR"] = orig_thumb
    get_settings.cache_clear()


async def test_render_worker_task_registered(tmp_path) -> None:
    """AC-2.3: render_worker_task stored on app.state as a live asyncio.Task."""
    orig_db, orig_thumb = _setup_isolated_env(tmp_path, "_registered")
    try:
        app = create_app()
        async with lifespan(app):
            assert hasattr(app.state, "render_worker_task"), (
                "render_worker_task not found on app.state after startup"
            )
            task = app.state.render_worker_task
            assert isinstance(task, asyncio.Task)
            assert not task.done(), "render_worker_task should be running during app lifetime"
    finally:
        _restore_env(orig_db, orig_thumb)


async def test_render_worker_task_cancelled_on_shutdown(tmp_path) -> None:
    """AC-3.1/3.2/3.3: render_worker_task is cancelled cleanly when lifespan exits."""
    orig_db, orig_thumb = _setup_isolated_env(tmp_path, "_shutdown")
    render_task_ref: asyncio.Task | None = None
    try:
        app = create_app()
        async with lifespan(app):
            render_task_ref = app.state.render_worker_task
        # Lifespan shutdown ran; verify cancellation
        assert render_task_ref is not None
        assert render_task_ref.done(), "render_worker_task should be done after shutdown"
        assert render_task_ref.cancelled(), "render_worker_task should be cancelled, not failed"
    finally:
        _restore_env(orig_db, orig_thumb)


def test_render_worker_instantiation_performance() -> None:
    """NFR-001: RenderWorkerLoop constructor completes in <100ms."""
    start = time.monotonic()
    _ = RenderWorkerLoop(
        service=MagicMock(spec=RenderService),
        queue=MagicMock(spec=RenderQueue),
        clip_repository=AsyncMock(),
        video_repository=AsyncMock(),
    )
    elapsed_ms = (time.monotonic() - start) * 1000
    assert elapsed_ms < 100, f"Worker construction took {elapsed_ms:.1f}ms (limit: 100ms)"
