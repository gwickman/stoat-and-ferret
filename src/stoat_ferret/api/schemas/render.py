"""Request and response schemas for render endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateRenderRequest(BaseModel):
    """Request to start a new render job."""

    project_id: str = Field(..., description="Project UUID to render")
    output_format: str = Field(default="mp4", description="Output container format")
    quality_preset: str = Field(default="standard", description="Quality preset")
    render_plan: str = Field(default="{}", description="Serialized render plan JSON")


class RenderJobResponse(BaseModel):
    """Response representing a single render job."""

    id: str
    project_id: str
    status: str
    output_path: str
    output_format: str
    quality_preset: str
    progress: float
    error_message: str | None = None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class RenderListResponse(BaseModel):
    """Paginated list of render jobs."""

    items: list[RenderJobResponse]
    total: int
    limit: int
    offset: int


class QueueStatusResponse(BaseModel):
    """Render queue status information."""

    active_count: int
    queue_depth: int
    max_concurrent: int
    max_depth: int


class EncoderInfoResponse(BaseModel):
    """Response representing a single detected encoder."""

    name: str
    codec: str
    is_hardware: bool
    encoder_type: str
    description: str
    detected_at: datetime


class EncoderListResponse(BaseModel):
    """List of detected encoders."""

    encoders: list[EncoderInfoResponse]
    cached: bool
