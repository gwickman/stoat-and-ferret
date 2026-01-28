"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI
from prometheus_client import make_asgi_app

from stoat_ferret.api.middleware.correlation import CorrelationIdMiddleware
from stoat_ferret.api.middleware.metrics import MetricsMiddleware
from stoat_ferret.api.routers import health, videos
from stoat_ferret.api.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan resources.

    Opens database connection on startup and closes on shutdown.
    The connection is stored in app.state.db for access by routes.

    Args:
        app: The FastAPI application instance.

    Yields:
        None after startup completes.
    """
    settings = get_settings()

    # Startup: open database connection
    app.state.db = await aiosqlite.connect(settings.database_path_resolved)
    app.state.db.row_factory = aiosqlite.Row

    yield

    # Shutdown: close database connection
    await app.state.db.close()


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance with lifespan management.
    """
    app = FastAPI(
        title="stoat-and-ferret",
        description="AI-driven video editor API",
        version="0.3.0",
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(videos.router)

    # Add middleware (order matters - first added = outermost)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    # Mount Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app
