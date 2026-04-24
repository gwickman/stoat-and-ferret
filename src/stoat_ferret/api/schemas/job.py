"""Job API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobSubmitResponse(BaseModel):
    """Response returned when a job is submitted.

    Contains the unique job ID for polling status.
    """

    job_id: str = Field(
        description="Unique identifier for the submitted job. Use this id "
        "with ``GET /api/v1/jobs/{job_id}``, "
        "``GET /api/v1/jobs/{job_id}/wait``, or ``POST "
        "/api/v1/jobs/{job_id}/cancel``."
    )


class JobStatusResponse(BaseModel):
    """Response for job status queries.

    Contains the current status, optional progress, result when complete,
    and error message on failure.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "job_id": "job_a1b2c3d4",
                    "status": "complete",
                    "progress": 1.0,
                    "result": {"output_path": "data/renders/clip_01.mp4"},
                    "error": None,
                }
            ]
        },
    )

    job_id: str = Field(description="Unique identifier for the job.")
    status: str = Field(
        description=(
            "Current job status. One of ``pending``, ``running``, ``complete``, "
            "``failed``, ``timeout``, ``cancelled``. Valid transitions: "
            "``pending -> running -> (complete | failed | timeout | cancelled)``. "
            "Terminal states are ``complete``, ``failed``, ``timeout``, and "
            "``cancelled`` — once reached, the status never changes. See the "
            "``JobStatus`` schema for the enumerated values."
        ),
    )
    progress: float | None = Field(
        default=None,
        description="Progress value in ``[0.0, 1.0]`` reported by the handler "
        "while ``status == 'running'``; ``null`` otherwise.",
    )
    result: Any = Field(
        default=None,
        description="Handler return value when ``status == 'complete'``; "
        "``null`` for non-terminal states and for failure/timeout/cancelled.",
    )
    error: str | None = Field(
        default=None,
        description="Error message when ``status`` is ``failed`` or "
        "``timeout``; ``null`` otherwise.",
    )
