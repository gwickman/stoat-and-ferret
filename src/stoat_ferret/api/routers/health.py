"""Health check endpoints for liveness and readiness probes."""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from stoat_ferret.api.settings import get_settings
from stoat_ferret.db.models import ProxyStatus
from stoat_ferret.models.health import HealthStatus
from stoat_ferret_core import health_check as _rust_health_check

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

    Checks startup gate and subsystem status (database, FFmpeg, Rust core,
    filesystem). Preview, proxy, and render issues result in "degraded" (not
    "unhealthy") overall status. Only the critical checks cause HTTP 503.

    Returns HTTP 503 with ready=false until the startup gate is open and all
    critical checks pass. Returns HTTP 200 with ready=true when ready.

    Args:
        request: The FastAPI request object, used to access app state.

    Returns:
        JSON response with ready, status, version info, operational metrics,
        and individual check results.
        Returns 200 if startup complete and all critical checks pass,
        503 if startup is in progress or a critical check fails.
    """
    # Startup gate: return 503 immediately if startup not yet complete
    if not getattr(request.app.state, "_startup_ready", False):
        return JSONResponse(
            content={
                "ready": False,
                "status": "starting",
                "app_version": str(request.app.version),
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    checks: dict[str, dict[str, Any]] = {}
    critical_healthy = True
    any_degraded = False

    # Database check (critical)
    try:
        db_check = await asyncio.wait_for(_check_database(request), timeout=5.0)
    except asyncio.TimeoutError:
        db_check = {"status": "error", "error": "check timed out"}
        critical_healthy = False
    checks["database"] = db_check
    if db_check["status"] != "ok":
        critical_healthy = False

    # FFmpeg check (critical)
    try:
        ffmpeg_check = await asyncio.wait_for(_check_ffmpeg(), timeout=5.0)
    except asyncio.TimeoutError:
        ffmpeg_check = {"status": "error", "error": "check timed out"}
        critical_healthy = False
    checks["ffmpeg"] = ffmpeg_check
    if ffmpeg_check["status"] != "ok":
        critical_healthy = False

    # Rust core check (critical)
    try:
        rust_check = await asyncio.wait_for(_check_rust_core(), timeout=5.0)
    except asyncio.TimeoutError:
        rust_check = {"status": "error", "error": "check timed out"}
        critical_healthy = False
    checks["rust_core"] = rust_check
    if rust_check["status"] != "ok":
        critical_healthy = False

    # Filesystem check (critical)
    try:
        fs_check = await asyncio.wait_for(_check_filesystem(), timeout=5.0)
    except asyncio.TimeoutError:
        fs_check = {"status": "error", "error": "check timed out"}
        critical_healthy = False
    checks["filesystem"] = fs_check
    if fs_check["status"] != "ok":
        critical_healthy = False

    # Preview check (non-critical — degraded only)
    try:
        preview_check = await asyncio.wait_for(_check_preview(request), timeout=5.0)
    except asyncio.TimeoutError:
        preview_check = {"status": "degraded", "error": "check timed out"}
        any_degraded = True
    checks["preview"] = preview_check
    if preview_check["status"] != "ok":
        any_degraded = True

    # Proxy check (non-critical — degraded only)
    try:
        proxy_check = await asyncio.wait_for(_check_proxy(request), timeout=5.0)
    except asyncio.TimeoutError:
        proxy_check = {"status": "degraded", "error": "check timed out"}
        any_degraded = True
    checks["proxy"] = proxy_check
    if proxy_check["status"] != "ok":
        any_degraded = True

    # Render check (non-critical — degraded only, per LRN-136)
    try:
        render_check = await asyncio.wait_for(_check_render(request), timeout=5.0)
    except asyncio.TimeoutError:
        render_check = {"status": "degraded", "error": "check timed out"}
        any_degraded = True
    checks["render"] = render_check
    if render_check["status"] != "ok":
        any_degraded = True

    is_ready = critical_healthy

    if not critical_healthy:
        overall = "degraded"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif any_degraded:
        overall = "degraded"
        status_code = status.HTTP_200_OK
    else:
        overall = "ok"
        status_code = status.HTTP_200_OK

    # Extract version info from check results.
    # sqlite_version is the SQLite runtime version (e.g., "3.50.4") — distinct
    # from the alembic revision hash returned by /api/v1/version.database_version.
    sqlite_version: str | None = db_check.get("version")
    core_version: str | None = rust_check.get("version")

    # Compute uptime since startup completed
    startup_ts = getattr(request.app.state, "_startup_timestamp", None)
    uptime: float | None = None
    if startup_ts is not None:
        uptime = (datetime.now(timezone.utc) - datetime.fromisoformat(startup_ts)).total_seconds()

    # Compute WebSocket buffer utilization (active connections / assumed max 100)
    ws_manager = getattr(request.app.state, "ws_manager", None)
    ws_util = 0.0
    if ws_manager is not None:
        ws_util = min(float(ws_manager.active_connections), 100.0)

    response_body = HealthStatus(
        ready=is_ready,
        status=overall,
        app_version=str(request.app.version),
        sqlite_version=sqlite_version,
        core_version=core_version,
        ws_buffer_utilization=ws_util,
        uptime_seconds=uptime,
        checks=checks,
    )
    return JSONResponse(content=response_body.model_dump(), status_code=status_code)


async def _check_database(request: Request) -> dict[str, Any]:
    """Check database connectivity and retrieve the SQLite version.

    Args:
        request: The FastAPI request object to access app.state.db.

    Returns:
        Dictionary with status, latency_ms, and version on success,
        or status and error on failure.
    """
    db = getattr(request.app.state, "db", None)
    if db is None:
        return {"status": "ok", "latency_ms": 0.0, "version": None}
    try:
        start = time.perf_counter()
        cursor = await db.execute("SELECT sqlite_version()")
        row = await cursor.fetchone()
        latency_ms = (time.perf_counter() - start) * 1000
        version: str | None = row[0] if row else None
        return {"status": "ok", "latency_ms": round(latency_ms, 2), "version": version}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _check_rust_core() -> dict[str, Any]:
    """Check Rust core availability by calling health_check().

    Returns:
        Dictionary with status and version on success, or status and error on failure.
    """
    try:
        version = await asyncio.to_thread(_rust_health_check)
        return {"status": "ok", "version": version}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _check_filesystem() -> dict[str, Any]:
    """Check filesystem write access in the data directory.

    Attempts to create and delete a temporary file in the directory containing
    the database, verifying the filesystem is writable.

    Returns:
        Dictionary with status "ok" on success, or status and error on failure.
    """
    settings = get_settings()
    data_dir = Path(settings.database_path).parent
    test_file = data_dir / ".healthcheck_write_test"

    def _do_check() -> None:
        test_file.write_text("ok")
        with contextlib.suppress(OSError):
            test_file.unlink()

    try:
        await asyncio.to_thread(_do_check)
        return {"status": "ok"}
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


async def _check_render(request: Request) -> dict[str, Any]:
    """Check render subsystem health.

    Reports active job count, queue depth, disk usage, and encoder
    availability. Status is "unavailable" when FFmpeg is missing,
    "degraded" when disk usage exceeds threshold or queue is near
    capacity, and "ok" otherwise.

    This is a non-critical component: degradation does not cause HTTP 503.

    Args:
        request: The FastAPI request object to access app.state.

    Returns:
        Dictionary with status, active_jobs, queue_depth,
        disk_usage_percent, and encoder_available fields.
    """
    render_queue = getattr(request.app.state, "render_queue", None)

    # Check encoder availability via PATH lookup (no subprocess)
    encoder_available = shutil.which("ffmpeg") is not None

    if render_queue is None:
        return {
            "status": "ok" if encoder_available else "unavailable",
            "active_jobs": 0,
            "queue_depth": 0,
            "disk_usage_percent": 0.0,
            "encoder_available": encoder_available,
        }

    try:
        active_jobs = await render_queue.get_active_count()
        queue_depth = await render_queue.get_queue_depth()

        settings = get_settings()

        # Disk usage for render output directory
        output_dir = Path(settings.render_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(output_dir)
        disk_usage_percent = (usage.used / usage.total * 100) if usage.total > 0 else 0.0

        # Determine status
        if not encoder_available:
            check_status = "unavailable"
        else:
            disk_ratio = usage.used / usage.total if usage.total > 0 else 0.0
            max_depth = render_queue._max_depth
            queue_ratio = queue_depth / max_depth if max_depth > 0 else 0.0
            if disk_ratio > settings.render_disk_degraded_threshold or queue_ratio > 0.8:
                check_status = "degraded"
            else:
                check_status = "ok"

        return {
            "status": check_status,
            "active_jobs": active_jobs,
            "queue_depth": queue_depth,
            "disk_usage_percent": round(disk_usage_percent, 1),
            "encoder_available": encoder_available,
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e)}
