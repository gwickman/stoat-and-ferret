"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
import structlog
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app

from stoat_ferret.api.middleware.correlation import CorrelationIdMiddleware
from stoat_ferret.api.middleware.metrics import MetricsMiddleware
from stoat_ferret.api.routers import health, jobs, projects, videos
from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
from stoat_ferret.api.settings import get_settings
from stoat_ferret.db.async_repository import (
    AsyncSQLiteVideoRepository,
    AsyncVideoRepository,
)
from stoat_ferret.db.clip_repository import AsyncClipRepository
from stoat_ferret.db.project_repository import AsyncProjectRepository
from stoat_ferret.jobs.queue import AsyncioJobQueue

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan resources.

    Opens database connection on startup and closes on shutdown.
    The connection is stored in app.state.db for access by routes.
    Starts and stops the job queue worker.
    Skips database setup when repositories have been injected via create_app().

    Args:
        app: The FastAPI application instance.

    Yields:
        None after startup completes.
    """
    # Skip DB and worker setup when dependencies are injected (test mode)
    if getattr(app.state, "_deps_injected", False):
        yield
        return

    settings = get_settings()

    # Startup: open database connection
    app.state.db = await aiosqlite.connect(settings.database_path_resolved)
    app.state.db.row_factory = aiosqlite.Row

    # Startup: create job queue, register handlers, and start worker
    job_queue = AsyncioJobQueue()
    repo = AsyncSQLiteVideoRepository(app.state.db)
    job_queue.register_handler(SCAN_JOB_TYPE, make_scan_handler(repo))
    app.state.job_queue = job_queue
    worker_task = asyncio.create_task(job_queue.process_jobs())
    logger.info("job_worker_started")

    yield

    # Shutdown: cancel worker and close database
    worker_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await worker_task
    logger.info("job_worker_stopped")

    await app.state.db.close()


def create_app(
    *,
    video_repository: AsyncVideoRepository | None = None,
    project_repository: AsyncProjectRepository | None = None,
    clip_repository: AsyncClipRepository | None = None,
    job_queue: AsyncioJobQueue | None = None,
    gui_static_path: str | Path | None = None,
) -> FastAPI:
    """Create and configure FastAPI application.

    When repository parameters are provided, they are stored on app.state
    and used by dependency functions instead of production defaults.
    When all are None, production behavior is preserved.

    Args:
        video_repository: Optional video repository for dependency injection.
        project_repository: Optional project repository for dependency injection.
        clip_repository: Optional clip repository for dependency injection.
        job_queue: Optional job queue for dependency injection.
        gui_static_path: Optional path to built frontend assets directory.

    Returns:
        Configured FastAPI application instance with lifespan management.
    """
    app = FastAPI(
        title="stoat-and-ferret",
        description="AI-driven video editor API",
        version="0.3.0",
        lifespan=lifespan,
    )

    # Store injected dependencies on app.state
    has_injected = any(
        dep is not None
        for dep in (video_repository, project_repository, clip_repository, job_queue)
    )
    if has_injected:
        app.state._deps_injected = True
        app.state.video_repository = video_repository
        app.state.project_repository = project_repository
        app.state.clip_repository = clip_repository
        app.state.job_queue = job_queue

    app.include_router(health.router)
    app.include_router(videos.router)
    app.include_router(projects.router)
    app.include_router(jobs.router)

    # Add middleware (order matters - first added = outermost)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    # Mount Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Mount frontend static files (after all API routers)
    if gui_static_path is not None:
        gui_dir = Path(gui_static_path)
        if gui_dir.is_dir():
            app.mount("/gui", StaticFiles(directory=gui_dir, html=True), name="gui")

    return app
