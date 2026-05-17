"""Request and response schemas for render endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateRenderRequest(BaseModel):
    """Request to start a new render job."""

    project_id: uuid.UUID = Field(..., description="Project UUID to render")
    output_format: str = Field(default="mp4", description="Output container format")
    quality_preset: str = Field(
        default="standard",
        description="Quality preset",
        json_schema_extra={"enum": ["draft", "standard", "high"]},
    )
    encoder: str | None = Field(
        default=None,
        description="Video encoder name (e.g. libx264, libvpx-vp9). "
        "When omitted the format default is used.",
    )
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
    """Render queue status with capacity, disk space, and throughput metrics."""

    active_count: int = Field(..., description="Number of currently running render jobs")
    pending_count: int = Field(..., description="Number of queued jobs waiting to run")
    max_concurrent: int = Field(..., description="Maximum simultaneous running jobs")
    max_queue_depth: int = Field(..., description="Maximum queued jobs before rejection")
    disk_available_bytes: int = Field(
        ..., description="Available disk space in the render output directory"
    )
    disk_total_bytes: int = Field(..., description="Total disk space on the render output volume")
    completed_today: int = Field(..., description="Jobs completed since midnight UTC")
    failed_today: int = Field(..., description="Jobs failed since midnight UTC")


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


class QualityPresetInfo(BaseModel):
    """Bitrate settings for a single quality preset."""

    preset: str = Field(..., description="Quality preset name (draft, standard, high)")
    video_bitrate_kbps: int = Field(..., description="Target video bitrate in kilobits per second")


class CodecInfo(BaseModel):
    """Codec available within an output format, with quality presets."""

    name: str = Field(..., description="Codec identifier (e.g. h264, vp9)")
    encoder: str = Field(
        ..., description="FFmpeg encoder name for this codec (e.g. libx264, libvpx-vp9)"
    )
    quality_presets: list[QualityPresetInfo] = Field(
        ..., description="Bitrate mappings for each quality level"
    )


class FormatInfo(BaseModel):
    """Output format metadata with capability flags and codec details."""

    format: str = Field(..., description="Format identifier (mp4, webm, mov, mkv)")
    extension: str = Field(..., description="File extension including dot (e.g. .mp4)")
    mime_type: str = Field(..., description="MIME type for the container format")
    codecs: list[CodecInfo] = Field(..., description="Codecs supported by this container format")
    supports_hw_accel: bool = Field(
        ..., description="Whether hardware-accelerated encoding is available"
    )
    supports_two_pass: bool = Field(..., description="Whether two-pass encoding is supported")
    supports_alpha: bool = Field(
        ..., description="Whether the format supports alpha channel transparency"
    )


class FormatListResponse(BaseModel):
    """All available output formats with codec and quality preset details."""

    formats: list[FormatInfo] = Field(..., description="Available output formats for rendering")


class RenderPreviewRequest(BaseModel):
    """Request for FFmpeg command preview given render settings."""

    output_format: str = Field(
        ..., description="Output container format (mp4, webm, mkv, mov, avi)"
    )
    quality_preset: str = Field(..., description="Quality preset (draft, standard, high)")
    encoder: str = Field(..., description="Video encoder name (e.g. libx264, libx265, libvpx-vp9)")


class RenderPreviewResponse(BaseModel):
    """Response containing a preview FFmpeg command string."""

    command: str = Field(..., description="Complete FFmpeg command string")
