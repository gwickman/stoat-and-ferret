"""System state snapshot endpoint (BL-275).

Exposes ``GET /api/v1/system/state`` — a single-pass aggregate of the
in-memory job queue and WebSocket connection manager. The endpoint is
read-only, issues no database queries (INV-SNAP-1), and preserves the
path expected by the synthetic monitoring probe (INV-SNAP-2).
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Request

from stoat_ferret.api.middleware.metrics import stoat_system_state_duration_seconds
from stoat_ferret.api.schemas.system_state import JobSummary, SystemState

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/system", tags=["system"])


def _compute_uptime_seconds(app_state: object) -> float:
    """Return seconds elapsed since the startup gate opened.

    Uses ``app.state._startup_timestamp`` (an ISO8601 string set by the
    lifespan once all subsystems are ready). Returns ``0.0`` before the
    startup gate opens so the response schema (``uptime_seconds: float``)
    stays populated even during boot races.
    """
    startup_ts = getattr(app_state, "_startup_timestamp", None)
    if not startup_ts:
        return 0.0
    try:
        started = datetime.fromisoformat(startup_ts)
    except (TypeError, ValueError):
        return 0.0
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return max(0.0, (now - started).total_seconds())


@router.get("/state", response_model=SystemState)
async def get_system_state(request: Request) -> SystemState:
    """Return aggregate in-memory system state.

    Performs a single-pass scan over the job queue and WebSocket
    connection manager (INV-SNAP-1). No database I/O. Missing or
    transiently-broken subsystems are reported as empty collections
    rather than raising (NFR-003): the snapshot is best-effort.

    Args:
        request: FastAPI request, used to reach ``app.state``.

    Returns:
        ``SystemState`` describing active jobs, open WebSocket
        connections, and process uptime.
    """
    with stoat_system_state_duration_seconds.time():
        return await _build_system_state(request)


async def _build_system_state(request: Request) -> SystemState:
    """Inner helper kept separate so the histogram timer wraps it cleanly."""
    app_state = request.app.state

    active_jobs: list[JobSummary] = []
    job_queue = getattr(app_state, "job_queue", None)
    if job_queue is not None:
        try:
            for snap in job_queue.list_jobs():
                active_jobs.append(
                    JobSummary(
                        job_id=snap.job_id,
                        job_type=snap.job_type,
                        status=snap.status.value,
                        progress=snap.progress,
                        submitted_at=snap.submitted_at,
                    )
                )
        except Exception as exc:
            # NFR-003: graceful partial state — log and return empty
            # jobs list rather than surfacing a 500 when the queue is
            # momentarily unavailable.
            logger.warning("system_state.job_queue_unavailable", error=str(exc))

    active_connections = 0
    ws_manager = getattr(app_state, "ws_manager", None)
    if ws_manager is not None:
        try:
            active_connections = int(ws_manager.active_connections)
        except Exception as exc:
            logger.warning("system_state.ws_manager_unavailable", error=str(exc))

    return SystemState(
        timestamp=datetime.now(timezone.utc),
        active_jobs=active_jobs,
        active_connections=active_connections,
        uptime_seconds=_compute_uptime_seconds(app_state),
    )
