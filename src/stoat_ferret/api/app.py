"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sqlite3
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
import structlog
from fastapi import FastAPI
from fastapi.responses import FileResponse
from prometheus_client import make_asgi_app

from stoat_ferret.api.middleware.correlation import CorrelationIdMiddleware
from stoat_ferret.api.middleware.metrics import MetricsMiddleware
from stoat_ferret.api.routers import effects, filesystem, health, jobs, projects, videos
from stoat_ferret.api.routers.ws import websocket_endpoint
from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
from stoat_ferret.api.services.thumbnail import ThumbnailService
from stoat_ferret.api.settings import get_settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.async_repository import (
    AsyncSQLiteVideoRepository,
    AsyncVideoRepository,
)
from stoat_ferret.db.audit import AuditLogger
from stoat_ferret.db.clip_repository import AsyncClipRepository
from stoat_ferret.db.project_repository import AsyncProjectRepository
from stoat_ferret.db.schema import create_tables_async
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.ffmpeg.executor import FFmpegExecutor, RealFFmpegExecutor
from stoat_ferret.ffmpeg.observable import ObservableFFmpegExecutor
from stoat_ferret.jobs.queue import AsyncioJobQueue
from stoat_ferret.logging import configure_logging

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
    # Configure structured logging before anything else
    settings = get_settings()
    configure_logging(
        level=getattr(logging, settings.log_level),
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count,
    )

    # Create ConnectionManager if not injected
    if not getattr(app.state, "ws_manager", None):
        app.state.ws_manager = ConnectionManager()

    # Skip DB and worker setup when dependencies are injected (test mode)
    if getattr(app.state, "_deps_injected", False):
        yield
        return

    # Startup: open database connection
    app.state.db = await aiosqlite.connect(settings.database_path_resolved)
    app.state.db.row_factory = aiosqlite.Row

    # Ensure schema exists (idempotent, uses IF NOT EXISTS)
    await create_tables_async(app.state.db)

    # Open a separate sync connection for audit logging
    sync_conn = sqlite3.connect(str(settings.database_path_resolved))
    sync_conn.execute("PRAGMA journal_mode=WAL")
    audit_logger = AuditLogger(conn=sync_conn)
    app.state.audit_logger = audit_logger

    # Startup: create services, job queue, register handlers, and start worker
    job_queue = AsyncioJobQueue()
    repo = AsyncSQLiteVideoRepository(app.state.db, audit_logger=audit_logger)
    app.state.ffmpeg_executor = ObservableFFmpegExecutor(RealFFmpegExecutor())
    thumbnail_service = ThumbnailService(
        executor=app.state.ffmpeg_executor,
        thumbnail_dir=settings.thumbnail_dir,
    )
    job_queue.register_handler(
        SCAN_JOB_TYPE,
        make_scan_handler(repo, thumbnail_service, app.state.ws_manager, queue=job_queue),
    )
    app.state.job_queue = job_queue
    worker_task = asyncio.create_task(job_queue.process_jobs())
    logger.info("job_worker_started")

    yield

    # Shutdown: cancel worker and close database
    worker_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await worker_task
    logger.info("job_worker_stopped")

    sync_conn.close()
    await app.state.db.close()


def create_app(
    *,
    video_repository: AsyncVideoRepository | None = None,
    project_repository: AsyncProjectRepository | None = None,
    clip_repository: AsyncClipRepository | None = None,
    job_queue: AsyncioJobQueue | None = None,
    ws_manager: ConnectionManager | None = None,
    effect_registry: EffectRegistry | None = None,
    ffmpeg_executor: FFmpegExecutor | None = None,
    audit_logger: AuditLogger | None = None,
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
        ws_manager: Optional WebSocket connection manager for dependency injection.
        effect_registry: Optional effect registry for dependency injection.
        ffmpeg_executor: Optional FFmpeg executor for dependency injection.
        audit_logger: Optional audit logger for dependency injection.
        gui_static_path: Optional path to built frontend assets directory.

    Returns:
        Configured FastAPI application instance with lifespan management.
    """
    settings = get_settings()
    app = FastAPI(
        title="stoat-and-ferret",
        description="AI-driven video editor API",
        version="0.3.0",
        lifespan=lifespan,
        debug=settings.debug,
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

    if audit_logger is not None:
        app.state.audit_logger = audit_logger

    if ws_manager is not None:
        app.state.ws_manager = ws_manager

    if effect_registry is not None:
        app.state.effect_registry = effect_registry

    if ffmpeg_executor is not None:
        app.state.ffmpeg_executor = ffmpeg_executor

    app.include_router(health.router)
    app.include_router(videos.router)
    app.include_router(projects.router)
    app.include_router(jobs.router)
    app.include_router(effects.router)
    app.include_router(filesystem.router)
    app.add_websocket_route("/ws", websocket_endpoint)

    # Add middleware (order matters - first added = outermost)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    # Mount Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Mount frontend SPA routes (after all API routers)
    # Use settings default when gui_static_path is not explicitly provided
    effective_gui_path = gui_static_path
    if effective_gui_path is None and not has_injected:
        effective_gui_path = settings.gui_static_path
    if effective_gui_path is not None:
        gui_dir = Path(effective_gui_path)
        if gui_dir.is_dir():
            index_html = gui_dir / "index.html"

            @app.get("/gui")
            async def gui_root() -> FileResponse:
                """Serve index.html for the bare /gui path."""
                return FileResponse(index_html)

            @app.get("/gui/{path:path}")
            async def gui_catch_all(path: str) -> FileResponse:
                """Serve static files or fall back to index.html for SPA routing."""
                file_path = gui_dir / path
                if file_path.is_file():
                    return FileResponse(file_path)
                return FileResponse(index_html)

    return app
