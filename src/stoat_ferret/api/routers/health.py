"""Health check endpoints for liveness and readiness probes."""

from __future__ import annotations

import shutil
import subprocess
import time
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/health", tags=["health"])


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

    Checks database connectivity and FFmpeg availability.

    Args:
        request: The FastAPI request object, used to access app state.

    Returns:
        JSON response with status and individual check results.
        Returns 200 if all checks pass, 503 if any check fails.
    """
    checks: dict[str, dict[str, Any]] = {}
    all_healthy = True

    # Database check
    db_check = await _check_database(request)
    checks["database"] = db_check
    if db_check["status"] != "ok":
        all_healthy = False

    # FFmpeg check
    ffmpeg_check = _check_ffmpeg()
    checks["ffmpeg"] = ffmpeg_check
    if ffmpeg_check["status"] != "ok":
        all_healthy = False

    response = {"status": "ok" if all_healthy else "degraded", "checks": checks}
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=response, status_code=status_code)


async def _check_database(request: Request) -> dict[str, Any]:
    """Check database connectivity by executing a simple query.

    Args:
        request: The FastAPI request object to access app.state.db.

    Returns:
        Dictionary with status and latency_ms on success, or status and error on failure.
    """
    try:
        start = time.perf_counter()
        cursor = await request.app.state.db.execute("SELECT 1")
        await cursor.fetchone()
        latency_ms = (time.perf_counter() - start) * 1000
        return {"status": "ok", "latency_ms": round(latency_ms, 2)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_ffmpeg() -> dict[str, Any]:
    """Check FFmpeg availability by running ffmpeg -version.

    Returns:
        Dictionary with status and version on success, or status and error on failure.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        return {"status": "error", "error": "ffmpeg not found in PATH"}

    try:
        result = subprocess.run(
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
