"""Batch render API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BatchJobConfig(BaseModel):
    """Configuration for a single job in a batch render request.

    Defines the project, output path, and quality preset for one render job.
    """

    project_id: str = Field(..., description="Project ID to render")
    output_path: str = Field(..., description="Output file path for rendered video")
    quality: str = Field(default="medium", description="Render quality preset")


class BatchRequest(BaseModel):
    """Request to submit a batch of render jobs.

    Contains a list of job configurations. The list must have at least one job.
    Maximum job count is enforced by the endpoint against Settings.batch_max_jobs.
    """

    jobs: list[BatchJobConfig] = Field(
        ..., min_length=1, description="List of render job configurations"
    )


class BatchResponse(BaseModel):
    """Response returned when a batch render is submitted.

    Contains the batch identifier, number of jobs queued, and status.
    """

    batch_id: str
    jobs_queued: int
    status: str


class BatchJobStatusResponse(BaseModel):
    """Status of an individual job within a batch.

    Tracks per-job state including progress and error information.
    """

    job_id: str
    project_id: str
    status: str
    progress: float = 0.0
    error: str | None = None


class BatchProgressResponse(BaseModel):
    """Aggregated progress response for a batch render.

    Uses Rust calculate_batch_progress() for progress aggregation.
    Includes per-job status details.
    """

    batch_id: str
    overall_progress: float
    completed_jobs: int
    failed_jobs: int
    total_jobs: int
    jobs: list[BatchJobStatusResponse]
