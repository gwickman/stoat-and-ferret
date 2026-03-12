"""Audio mix API request and response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TrackConfig(BaseModel):
    """Per-track audio configuration.

    Volume validation is performed by the endpoint handler to return
    domain-specific error codes (INVALID_AUDIO_VOLUME).
    """

    volume: float = Field(default=1.0, description="Volume multiplier (0.0-2.0)")
    fade_in: float = Field(default=0.0, ge=0.0, description="Fade-in duration in seconds")
    fade_out: float = Field(default=0.0, ge=0.0, description="Fade-out duration in seconds")


class AudioMixRequest(BaseModel):
    """Request schema for audio mix configuration.

    Volume and track count validation is performed by the endpoint handler
    to return domain-specific error codes.
    """

    tracks: list[TrackConfig] = Field(
        ..., description="Per-track audio configurations (2-8 tracks)"
    )
    master_volume: float = Field(default=1.0, description="Master volume multiplier (0.0-2.0)")
    normalize: bool = Field(default=True, description="Whether to normalize the mixed output")


class AudioMixResponse(BaseModel):
    """Response schema for audio mix configuration."""

    filter_preview: str
    tracks_configured: int
