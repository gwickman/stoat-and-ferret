"""Thumbnail strip API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ThumbnailStripGenerateRequest(BaseModel):
    """Request body for thumbnail strip generation.

    All fields are optional; the service uses defaults when omitted.
    """

    interval_seconds: float | None = Field(
        default=None, description="Seconds between frames (default: service default)"
    )
    frame_width: int | None = Field(default=None, gt=0, description="Width of each frame in pixels")
    frame_height: int | None = Field(
        default=None, gt=0, description="Height of each frame in pixels"
    )


class ThumbnailStripGenerateResponse(BaseModel):
    """Response returned when strip generation is queued."""

    strip_id: str
    status: str


class ThumbnailStripMetadataResponse(BaseModel):
    """Metadata for a generated thumbnail strip sprite sheet.

    Includes columns and rows so the client can calculate
    frame coordinates within the sprite sheet.
    """

    strip_id: str
    video_id: str
    status: str
    frame_count: int
    frame_width: int
    frame_height: int
    interval_seconds: float
    columns: int
    rows: int
