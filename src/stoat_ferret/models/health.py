"""Health status response models for liveness and readiness probes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class HealthStatus(BaseModel):
    """Readiness probe response model.

    Represents the complete health status of the application, including
    startup gate state, subsystem check results, version information,
    and operational metrics.

    ``sqlite_version`` holds the SQLite runtime version string (e.g.,
    ``"3.50.4"``) reported by ``SELECT sqlite_version()``. It was renamed
    from ``database_version`` in BL-267 to avoid a semantic collision with
    the new ``/api/v1/version`` endpoint, where ``database_version`` refers
    to the alembic revision hash of the schema.
    """

    model_config = ConfigDict(from_attributes=True)

    ready: bool
    status: str
    app_version: str
    sqlite_version: str | None = None
    core_version: str | None = None
    ws_buffer_utilization: float = 0.0
    uptime_seconds: float | None = None
    checks: dict[str, Any] = {}
