"""Application version endpoint."""

from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, Request

from stoat_ferret_core import health_check as _rust_health_check

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["version"])


@router.get("/version")
async def get_version(request: Request) -> dict[str, str]:
    """Return application version and Rust core status.

    Reads app_version from the FastAPI application version string and
    core_status from the Rust core health_check() function. No database
    queries — this endpoint is intentionally lightweight.

    Args:
        request: The FastAPI request object to access app.version.

    Returns:
        Dictionary with app_version and core_status string fields.
    """
    app_version = str(request.app.version)
    try:
        core_status = await asyncio.to_thread(_rust_health_check)
    except Exception:
        core_status = "error"

    logger.info("version.requested", app_version=app_version)
    return {
        "app_version": app_version,
        "core_status": core_status,
    }
