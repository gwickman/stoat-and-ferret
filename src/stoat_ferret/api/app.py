"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI
from prometheus_client import make_asgi_app

from stoat_ferret.api.middleware.correlation import CorrelationIdMiddleware
from stoat_ferret.api.middleware.metrics import MetricsMiddleware
from stoat_ferret.api.routers import health, projects, videos
from stoat_ferret.api.settings import get_settings
from stoat_ferret.db.async_repository import AsyncVideoRepository
from stoat_ferret.db.clip_repository import AsyncClipRepository
from stoat_ferret.db.project_repository import AsyncProjectRepository


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan resources.

    Opens database connection on startup and closes on shutdown.
    The connection is stored in app.state.db for access by routes.
    Skips database setup when repositories have been injected via create_app().

    Args:
        app: The FastAPI application instance.

    Yields:
        None after startup completes.
    """
    # Skip DB setup when all repositories are already injected (test mode)
    if getattr(app.state, "_deps_injected", False):
        yield
        return

    settings = get_settings()

    # Startup: open database connection
    app.state.db = await aiosqlite.connect(settings.database_path_resolved)
    app.state.db.row_factory = aiosqlite.Row

    yield

    # Shutdown: close database connection
    await app.state.db.close()


def create_app(
    *,
    video_repository: AsyncVideoRepository | None = None,
    project_repository: AsyncProjectRepository | None = None,
    clip_repository: AsyncClipRepository | None = None,
) -> FastAPI:
    """Create and configure FastAPI application.

    When repository parameters are provided, they are stored on app.state
    and used by dependency functions instead of production defaults.
    When all are None, production behavior is preserved.

    Args:
        video_repository: Optional video repository for dependency injection.
        project_repository: Optional project repository for dependency injection.
        clip_repository: Optional clip repository for dependency injection.

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
        dep is not None for dep in (video_repository, project_repository, clip_repository)
    )
    if has_injected:
        app.state._deps_injected = True
        app.state.video_repository = video_repository
        app.state.project_repository = project_repository
        app.state.clip_repository = clip_repository

    app.include_router(health.router)
    app.include_router(videos.router)
    app.include_router(projects.router)

    # Add middleware (order matters - first added = outermost)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    # Mount Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app
