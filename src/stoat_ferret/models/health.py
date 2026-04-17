"""Health status response models for liveness and readiness probes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class HealthStatus(BaseModel):
    """Readiness probe response model.

    Represents the complete health status of the application, including
    startup gate state, subsystem check results, version information,
    and operational metrics.
    """

    model_config = ConfigDict(from_attributes=True)

    ready: bool
    status: str
    app_version: str
    database_version: str | None = None
    core_version: str | None = None
    ws_buffer_utilization: float = 0.0
    uptime_seconds: float | None = None
    checks: dict[str, Any] = {}
