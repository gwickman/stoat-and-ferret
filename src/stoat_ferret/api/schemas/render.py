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


class QualityPresetInfo(BaseModel):
    """Bitrate settings for a single quality preset."""

    preset: str = Field(..., description="Quality preset name (draft, standard, high)")
    video_bitrate_kbps: int = Field(..., description="Target video bitrate in kilobits per second")


class CodecInfo(BaseModel):
    """Codec available within an output format, with quality presets."""

    name: str = Field(..., description="Codec identifier (e.g. h264, vp9)")
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
