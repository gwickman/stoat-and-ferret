"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
import os
import sqlite3
import subprocess
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import aiosqlite
import structlog
from fastapi import FastAPI
from fastapi.responses import FileResponse
from prometheus_client import make_asgi_app

from stoat_ferret.api.lifespan import record_feature_flags, run_startup_migrations
from stoat_ferret.api.middleware.correlation import CorrelationIdMiddleware
from stoat_ferret.api.middleware.metrics import MetricsMiddleware
from stoat_ferret.api.routers import (
    audio,
    batch,
    compose,
    effects,
    filesystem,
    flags,
    health,
    jobs,
    preview,
    projects,
    proxy,
    render,
    thumbnails,
    timeline,
    version,
    versions,
    videos,
    waveform,
)
from stoat_ferret.api.routers.ws import websocket_endpoint
from stoat_ferret.api.services.proxy_service import (
    PROXY_JOB_TYPE,
    ProxyService,
    make_proxy_handler,
)
from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
from stoat_ferret.api.services.thumbnail import ThumbnailService
from stoat_ferret.api.services.waveform import WaveformService
from stoat_ferret.api.settings import get_settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.async_repository import (
    AsyncSQLiteVideoRepository,
    AsyncVideoRepository,
)
from stoat_ferret.db.audit import AuditLogger
from stoat_ferret.db.batch_repository import AsyncBatchRepository, AsyncSQLiteBatchRepository
from stoat_ferret.db.clip_repository import AsyncClipRepository
from stoat_ferret.db.models import ProxyQuality, ProxyStatus
from stoat_ferret.db.project_repository import AsyncProjectRepository
from stoat_ferret.db.proxy_repository import AsyncProxyRepository, SQLiteProxyRepository
from stoat_ferret.db.schema import create_tables_async
from stoat_ferret.db.thumbnail_strip_repository import SQLiteThumbnailStripRepository
from stoat_ferret.db.timeline_repository import AsyncTimelineRepository
from stoat_ferret.db.version_repository import AsyncVersionRepository
from stoat_ferret.db.waveform_repository import SQLiteWaveformRepository
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.ffmpeg.async_executor import RealAsyncFFmpegExecutor
from stoat_ferret.ffmpeg.executor import FFmpegExecutor, RealFFmpegExecutor
from stoat_ferret.ffmpeg.observable import ObservableFFmpegExecutor
from stoat_ferret.jobs.queue import AsyncioJobQueue
from stoat_ferret.logging import configure_logging
from stoat_ferret.preview.cache import PreviewCache
from stoat_ferret.preview.manager import PreviewManager
from stoat_ferret.render.checkpoints import RenderCheckpointManager
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.render_repository import (
    AsyncRenderRepository,
    AsyncSQLiteRenderRepository,
)
from stoat_ferret.render.service import RenderService

logger = structlog.get_logger(__name__)


def _get_git_sha() -> str:
    """Get the current git SHA for the deployment.startup event.

    Checks the GIT_SHA environment variable first (set during Docker build),
    then falls back to running git rev-parse in development environments.

    Returns:
        Short git SHA string, or "unknown" if unavailable.
    """
    git_sha = os.environ.get("GIT_SHA", "")
    if git_sha:
        return git_sha
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


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
    app.state._settings = settings
    configure_logging(
        level=getattr(logging, settings.log_level),
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count,
    )

    # Create ConnectionManager if not injected
    if not getattr(app.state, "ws_manager", None):
        app.state.ws_manager = ConnectionManager()

    # Initialize startup gate (False until all subsystems ready)
    app.state._startup_ready = False
    app.state._startup_timestamp = None

    # Skip DB and worker setup when dependencies are injected (test mode)
    if getattr(app.state, "_deps_injected", False):
        # In DI/test mode, mark startup complete so health checks work normally
        app.state._startup_ready = True
        app.state._startup_timestamp = datetime.utcnow().isoformat()
        yield
        return

    # Apply any pending Alembic migrations with pre-migration backup and
    # audit logging (BL-266) before opening the long-lived connection.
    await run_startup_migrations(app=app, settings=settings)

    # Startup: open database connection
    app.state.db = await aiosqlite.connect(settings.database_path_resolved)
    app.state.db.row_factory = aiosqlite.Row

    # Ensure schema exists (idempotent, uses IF NOT EXISTS)
    await create_tables_async(app.state.db)

    # Record feature flag state to feature_flag_log (BL-268) after schema
    # creation so the table definitely exists for the insert.
    record_feature_flags(settings=settings, db_path=str(settings.database_path_resolved))

    # Open a separate sync connection for audit logging
    sync_conn = sqlite3.connect(str(settings.database_path_resolved))
    sync_conn.execute("PRAGMA journal_mode=WAL")
    audit_logger = AuditLogger(conn=sync_conn)
    app.state.audit_logger = audit_logger

    # Create batch repository backed by the same database
    app.state.batch_repository = AsyncSQLiteBatchRepository(app.state.db)

    # Create proxy repository backed by the same database
    app.state.proxy_repository = SQLiteProxyRepository(app.state.db)

    # Create thumbnail strip and waveform repositories
    app.state.thumbnail_strip_repository = SQLiteThumbnailStripRepository(app.state.db)
    app.state.waveform_repository = SQLiteWaveformRepository(app.state.db)

    # Startup: create services, job queue, register handlers, and start worker
    job_queue = AsyncioJobQueue()
    repo = AsyncSQLiteVideoRepository(app.state.db, audit_logger=audit_logger)
    app.state.ffmpeg_executor = ObservableFFmpegExecutor(RealFFmpegExecutor())
    async_executor = RealAsyncFFmpegExecutor()
    thumbnail_service = ThumbnailService(
        executor=app.state.ffmpeg_executor,
        thumbnail_dir=settings.thumbnail_dir,
        async_executor=async_executor,
        ws_manager=app.state.ws_manager,
        strip_repository=app.state.thumbnail_strip_repository,
    )
    app.state.thumbnail_service = thumbnail_service

    # Create waveform service
    app.state.waveform_service = WaveformService(
        async_executor=async_executor,
        waveform_dir=settings.waveform_dir,
        ws_manager=app.state.ws_manager,
        waveform_repository=app.state.waveform_repository,
    )

    # Create proxy service before scan handler so it can be injected
    proxy_service = ProxyService(
        proxy_repository=app.state.proxy_repository,
        async_executor=RealAsyncFFmpegExecutor(),
        ws_manager=app.state.ws_manager,
        job_queue=job_queue,
        proxy_dir=settings.proxy_output_dir,
        max_storage_bytes=settings.proxy_max_storage_bytes,
        cleanup_threshold=settings.proxy_cleanup_threshold,
    )
    app.state.proxy_service = proxy_service

    # Create render services
    render_repo = AsyncSQLiteRenderRepository(app.state.db)
    app.state.render_repository = render_repo
    render_queue = RenderQueue(
        render_repo,
        max_concurrent=settings.render_max_concurrent,
        max_depth=settings.render_max_queue_depth,
    )
    app.state.render_queue = render_queue
    render_executor = RenderExecutor(
        timeout_seconds=settings.render_timeout_seconds,
        cancel_grace_seconds=settings.render_cancel_grace_seconds,
    )
    app.state.render_executor = render_executor
    checkpoint_manager = RenderCheckpointManager(app.state.db)
    app.state.checkpoint_manager = checkpoint_manager
    render_service = RenderService(
        repository=render_repo,
        queue=render_queue,
        executor=render_executor,
        checkpoint_manager=checkpoint_manager,
        connection_manager=app.state.ws_manager,
        settings=settings,
    )
    app.state.render_service = render_service
    await render_service.recover()

    # Create preview manager
    from stoat_ferret.db.preview_repository import SQLitePreviewRepository
    from stoat_ferret.preview.hls_generator import HLSGenerator

    preview_repo = SQLitePreviewRepository(app.state.db)
    hls_generator = HLSGenerator(
        async_executor=RealAsyncFFmpegExecutor(),
        output_base_dir=settings.preview_output_dir,
    )
    app.state.preview_manager = PreviewManager(
        repository=preview_repo,
        generator=hls_generator,
        ws_manager=app.state.ws_manager,
    )
    app.state.preview_cache = PreviewCache()

    job_queue.register_handler(
        SCAN_JOB_TYPE,
        make_scan_handler(
            repo,
            thumbnail_service,
            app.state.ws_manager,
            queue=job_queue,
            proxy_service=proxy_service,
        ),
    )
    job_queue.register_handler(
        PROXY_JOB_TYPE,
        make_proxy_handler(proxy_service),
        timeout=1800.0,
    )

    app.state.job_queue = job_queue
    worker_task = asyncio.create_task(job_queue.process_jobs())
    logger.info("job_worker_started")

    # Collect version info for startup event
    from stoat_ferret_core import health_check

    core_version_str = health_check()
    try:
        cursor = await app.state.db.execute("SELECT sqlite_version()")
        row = await cursor.fetchone()
        db_version_str: str = row[0] if row else "unknown"
    except Exception:
        db_version_str = "unknown"

    # Mark startup complete and emit structured log event
    app.state._startup_ready = True
    app.state._startup_timestamp = datetime.utcnow().isoformat()
    logger.info(
        "deployment.startup",
        app_version=app.version,
        core_version=core_version_str,
        git_sha=_get_git_sha(),
        database_version=db_version_str,
    )

    yield

    # Shutdown: graceful render shutdown sequence (BL-227)
    # Order: set flag → cancel via stdin 'q' → wait grace → SIGKILL → clean temp
    rs: RenderService | None = getattr(app.state, "render_service", None)
    re: RenderExecutor | None = getattr(app.state, "render_executor", None)
    if rs is not None and re is not None:
        # Step 1: Reject new requests
        rs.initiate_shutdown()

        # Step 2: Cancel active renders via stdin 'q'
        cancelled_ids = await re.cancel_all()

        if cancelled_ids:
            # Step 3: Wait grace period for processes to finalize
            grace = settings.render_cancel_grace_seconds
            logger.info(
                "render_shutdown.waiting_grace",
                grace_seconds=grace,
                active_count=len(cancelled_ids),
            )
            await asyncio.sleep(grace)

            # Step 4: Kill remaining processes
            killed_ids = await re.kill_remaining()
            if killed_ids:
                logger.warning(
                    "render_shutdown.killed_remaining",
                    killed_count=len(killed_ids),
                )

        # Step 5: Clean up temp files for all tracked jobs
        cleaned_ids = re.cleanup_all_temp_files()
        if cleaned_ids:
            logger.info("render_shutdown.temp_files_cleaned", count=len(cleaned_ids))

        logger.info("render_services_shutdown")

    # Shutdown: cancel preview sessions first
    preview_manager: PreviewManager | None = getattr(app.state, "preview_manager", None)
    if preview_manager is not None:
        await preview_manager.cancel_all()

    preview_cache: PreviewCache | None = getattr(app.state, "preview_cache", None)
    if preview_cache is not None:
        await preview_cache.stop_cleanup_task()

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
    timeline_repository: AsyncTimelineRepository | None = None,
    version_repository: AsyncVersionRepository | None = None,
    batch_repository: AsyncBatchRepository | None = None,
    proxy_repository: AsyncProxyRepository | None = None,
    render_repository: AsyncRenderRepository | None = None,
    render_queue: RenderQueue | None = None,
    render_service: RenderService | None = None,
    job_queue: AsyncioJobQueue | None = None,
    ws_manager: ConnectionManager | None = None,
    effect_registry: EffectRegistry | None = None,
    ffmpeg_executor: FFmpegExecutor | None = None,
    audit_logger: AuditLogger | None = None,
    preview_manager: PreviewManager | None = None,
    preview_cache: PreviewCache | None = None,
    thumbnail_service: ThumbnailService | None = None,
    waveform_service: WaveformService | None = None,
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
        timeline_repository: Optional timeline repository for dependency injection.
        version_repository: Optional version repository for dependency injection.
        batch_repository: Optional batch repository for dependency injection.
        proxy_repository: Optional proxy repository for dependency injection.
        render_repository: Optional render repository for dependency injection.
        render_queue: Optional render queue for dependency injection.
        render_service: Optional render service for dependency injection.
        job_queue: Optional job queue for dependency injection.
        ws_manager: Optional WebSocket connection manager for dependency injection.
        effect_registry: Optional effect registry for dependency injection.
        ffmpeg_executor: Optional FFmpeg executor for dependency injection.
        audit_logger: Optional audit logger for dependency injection.
        preview_manager: Optional preview manager for dependency injection.
        preview_cache: Optional preview cache for dependency injection.
        thumbnail_service: Optional thumbnail service for dependency injection.
        waveform_service: Optional waveform service for dependency injection.
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

    # Initialize startup gate so it is always present on app.state
    app.state._startup_ready = False
    app.state._startup_timestamp = None

    # Store injected dependencies on app.state
    has_injected = any(
        dep is not None
        for dep in (
            video_repository,
            project_repository,
            clip_repository,
            render_repository,
            job_queue,
        )
    )
    if has_injected:
        app.state._deps_injected = True
        app.state.video_repository = video_repository
        app.state.project_repository = project_repository
        app.state.clip_repository = clip_repository
        app.state.timeline_repository = timeline_repository
        app.state.version_repository = version_repository
        app.state.batch_repository = batch_repository
        app.state.proxy_repository = proxy_repository
        app.state.render_repository = render_repository
        app.state.job_queue = job_queue

    if render_queue is not None:
        app.state.render_queue = render_queue

    if render_service is not None:
        app.state.render_service = render_service

    if audit_logger is not None:
        app.state.audit_logger = audit_logger

    if ws_manager is not None:
        app.state.ws_manager = ws_manager

    if effect_registry is not None:
        app.state.effect_registry = effect_registry

    if ffmpeg_executor is not None:
        app.state.ffmpeg_executor = ffmpeg_executor

    if preview_manager is not None:
        app.state.preview_manager = preview_manager

    if preview_cache is not None:
        app.state.preview_cache = preview_cache

    if thumbnail_service is not None:
        app.state.thumbnail_service = thumbnail_service

    if waveform_service is not None:
        app.state.waveform_service = waveform_service

    app.include_router(health.router)
    app.include_router(version.router)
    app.include_router(flags.router)
    app.include_router(videos.router)
    app.include_router(projects.router)
    app.include_router(jobs.router)
    app.include_router(effects.router)
    app.include_router(compose.router)
    app.include_router(audio.router)
    app.include_router(filesystem.router)
    app.include_router(timeline.router)
    app.include_router(batch.router)
    app.include_router(preview.router)
    app.include_router(proxy.router)
    app.include_router(render.router)
    app.include_router(thumbnails.router)
    app.include_router(versions.router)
    app.include_router(waveform.router)
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

    # Inject standalone enum schemas into OpenAPI spec so they flow through
    # to TypeScript codegen before proxy API endpoints exist (BL-176).
    _original_openapi = app.openapi

    def _custom_openapi() -> dict:  # type: ignore[type-arg]
        schema = _original_openapi()
        schemas = schema.setdefault("components", {}).setdefault("schemas", {})
        schemas.setdefault(
            "ProxyStatus",
            {
                "enum": [e.value for e in ProxyStatus],
                "title": "ProxyStatus",
                "type": "string",
                "description": inspect.cleandoc(ProxyStatus.__doc__ or ""),
            },
        )
        schemas.setdefault(
            "ProxyQuality",
            {
                "enum": [e.value for e in ProxyQuality],
                "title": "ProxyQuality",
                "type": "string",
                "description": inspect.cleandoc(ProxyQuality.__doc__ or ""),
            },
        )
        return schema

    app.openapi = _custom_openapi  # type: ignore[method-assign]

    return app
