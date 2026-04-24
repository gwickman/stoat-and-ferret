"""System state snapshot API schemas (BL-275)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobSummary(BaseModel):
    """Minimal per-job summary included in the system state snapshot.

    Contains only the fields an external agent needs to orient on a
    running workload without a follow-up ``GET /api/v1/jobs/{id}`` call.
    Full job detail (result payload, error message) is intentionally
    omitted — snapshot is a lightweight fleet view.
    """

    model_config = ConfigDict(from_attributes=True)

    job_id: str = Field(description="Unique identifier for the job.")
    job_type: str = Field(
        description="Registered job-type label (e.g. ``scan``, ``render``).",
    )
    status: str = Field(
        description="Current job status (``pending``/``running``/``complete``/"
        "``failed``/``timeout``/``cancelled``).",
    )
    progress: float | None = Field(
        default=None,
        description="Progress value in ``[0.0, 1.0]`` when reported by the "
        "handler; ``null`` otherwise.",
    )
    submitted_at: datetime = Field(
        description="UTC timestamp (timezone-aware) when the job was submitted.",
    )


class SystemState(BaseModel):
    """Aggregate in-memory system state returned by ``/api/v1/system/state``.

    Produced by a single-pass scan over the in-process job queue and
    WebSocket connection manager (INV-SNAP-1). The handler never issues
    database round-trips.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "timestamp": "2026-04-24T17:05:00Z",
                    "active_jobs": [
                        {
                            "job_id": "job_a1b2c3d4",
                            "job_type": "render",
                            "status": "running",
                            "progress": 0.42,
                            "submitted_at": "2026-04-24T17:04:10Z",
                        }
                    ],
                    "active_connections": 3,
                    "uptime_seconds": 1820.5,
                }
            ]
        },
    )

    timestamp: datetime = Field(
        description="UTC timestamp (timezone-aware) at which the snapshot was captured.",
    )
    active_jobs: list[JobSummary] = Field(
        description="Jobs currently tracked by the in-memory job queue, in submission order.",
    )
    active_connections: int = Field(
        description="Number of currently open WebSocket connections.",
        ge=0,
    )
    uptime_seconds: float = Field(
        description="Seconds elapsed since the application startup gate "
        "opened. ``0.0`` before startup completes.",
        ge=0.0,
    )
