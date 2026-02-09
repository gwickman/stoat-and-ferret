"""Job API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class JobSubmitResponse(BaseModel):
    """Response returned when a job is submitted.

    Contains the unique job ID for polling status.
    """

    job_id: str


class JobStatusResponse(BaseModel):
    """Response for job status queries.

    Contains the current status, optional progress, result when complete,
    and error message on failure.
    """

    job_id: str
    status: str
    progress: float | None = None
    result: Any = None
    error: str | None = None
