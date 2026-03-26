"""Health check endpoints for liveness and readiness probes."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import time
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from stoat_ferret.db.models import ProxyStatus

router = APIRouter(prefix="/health", tags=["health"])

# Cache usage threshold for degraded status (90%)
_CACHE_DEGRADED_THRESHOLD = 90.0


@router.get("/live")
async def liveness() -> dict[str, str]:
    """Liveness probe - indicates the server is running.

    This endpoint always returns 200 if the server is able to respond.
    It performs no dependency checks.

    Returns:
        Simple status object indicating the server is alive.
    """
    return {"status": "ok"}


@router.get("/ready")
async def readiness(request: Request) -> JSONResponse:
    """Readiness probe - indicates all dependencies are healthy.

    Checks database, FFmpeg, preview, and proxy subsystem status.
    Preview and proxy issues result in "degraded" (not "unhealthy") overall
    status. Only database and FFmpeg failures cause 503.

    Args:
        request: The FastAPI request object, used to access app state.

    Returns:
        JSON response with status and individual check results.
        Returns 200 if all checks pass, 503 if a critical check fails.
    """
    checks: dict[str, dict[str, Any]] = {}
    critical_healthy = True
    any_degraded = False

    # Database check (critical)
    db_check = await _check_database(request)
    checks["database"] = db_check
    if db_check["status"] != "ok":
        critical_healthy = False

    # FFmpeg check (critical)
    ffmpeg_check = await _check_ffmpeg()
    checks["ffmpeg"] = ffmpeg_check
    if ffmpeg_check["status"] != "ok":
        critical_healthy = False

    # Preview check (non-critical — degraded only)
    preview_check = await _check_preview(request)
    checks["preview"] = preview_check
    if preview_check["status"] != "ok":
        any_degraded = True

    # Proxy check (non-critical — degraded only)
    proxy_check = await _check_proxy(request)
    checks["proxy"] = proxy_check
    if proxy_check["status"] != "ok":
        any_degraded = True

    if not critical_healthy:
        overall = "degraded"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif any_degraded:
        overall = "degraded"
        status_code = status.HTTP_200_OK
    else:
        overall = "ok"
        status_code = status.HTTP_200_OK

    response = {"status": overall, "checks": checks}
    return JSONResponse(content=response, status_code=status_code)


async def _check_database(request: Request) -> dict[str, Any]:
    """Check database connectivity by executing a simple query.

    Args:
        request: The FastAPI request object to access app.state.db.

    Returns:
        Dictionary with status and latency_ms on success, or status and error on failure.
    """
    db = getattr(request.app.state, "db", None)
    if db is None:
        return {"status": "ok", "latency_ms": 0.0}
    try:
        start = time.perf_counter()
        cursor = await db.execute("SELECT 1")
        await cursor.fetchone()
        latency_ms = (time.perf_counter() - start) * 1000
        return {"status": "ok", "latency_ms": round(latency_ms, 2)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _check_ffmpeg() -> dict[str, Any]:
    """Check FFmpeg availability by running ffmpeg -version.

    Returns:
        Dictionary with status and version on success, or status and error on failure.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        return {"status": "error", "error": "ffmpeg not found in PATH"}

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Parse version from first line, e.g., "ffmpeg version 6.0 ..."
        version_line = result.stdout.split("\n")[0]
        parts = version_line.split()
        version = parts[2] if len(parts) > 2 else "unknown"
        return {"status": "ok", "version": version}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _check_preview(request: Request) -> dict[str, Any]:
    """Check preview subsystem health.

    Reports active session count and cache usage. Status is "degraded"
    when cache usage exceeds 90%.

    Args:
        request: The FastAPI request object to access app.state.

    Returns:
        Dictionary with status, active_sessions, cache_usage_percent,
        and cache_healthy fields.
    """
    preview_cache = getattr(request.app.state, "preview_cache", None)
    if preview_cache is None:
        return {
            "status": "ok",
            "active_sessions": 0,
            "cache_usage_percent": 0.0,
            "cache_healthy": True,
        }

    try:
        cache_status = await preview_cache.status()
        cache_healthy = cache_status.usage_percent <= _CACHE_DEGRADED_THRESHOLD
        check_status = "ok" if cache_healthy else "degraded"

        return {
            "status": check_status,
            "active_sessions": len(cache_status.active_sessions),
            "cache_usage_percent": cache_status.usage_percent,
            "cache_healthy": cache_healthy,
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


async def _check_proxy(request: Request) -> dict[str, Any]:
    """Check proxy subsystem health.

    Reports whether the proxy directory is writable and the count of
    pending proxy generation jobs.

    Args:
        request: The FastAPI request object to access app.state.

    Returns:
        Dictionary with status, proxy_dir_writable, and pending_proxies fields.
    """
    proxy_service = getattr(request.app.state, "proxy_service", None)
    proxy_repo = getattr(request.app.state, "proxy_repository", None)

    if proxy_service is None:
        return {
            "status": "ok",
            "proxy_dir_writable": True,
            "pending_proxies": 0,
        }

    try:
        proxy_dir = proxy_service._proxy_dir
        dir_writable = os.path.isdir(proxy_dir) and os.access(proxy_dir, os.W_OK)

        pending_count = 0
        if proxy_repo is not None:
            pending = await proxy_repo.count_by_status(ProxyStatus.PENDING)
            generating = await proxy_repo.count_by_status(ProxyStatus.GENERATING)
            pending_count = pending + generating

        check_status = "ok" if dir_writable else "degraded"
        return {
            "status": check_status,
            "proxy_dir_writable": dir_writable,
            "pending_proxies": pending_count,
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e)}
