"""Waveform API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class WaveformGenerateRequest(BaseModel):
    """Request body for waveform generation.

    The format field selects PNG image or JSON amplitude data output.
    """

    format: Literal["png", "json"] = Field(
        default="png", description="Output format: 'png' for image, 'json' for amplitude data"
    )


class WaveformGenerateResponse(BaseModel):
    """Response returned when waveform generation is queued."""

    waveform_id: str
    status: str


class WaveformMetadataResponse(BaseModel):
    """Metadata for a generated waveform.

    Includes format, duration, channels, and samples_per_second so
    the client knows how to interpret the waveform data.
    """

    waveform_id: str
    video_id: str
    status: str
    format: str
    duration: float
    channels: int
    samples_per_second: int


class WaveformSample(BaseModel):
    """A single amplitude sample from JSON waveform data."""

    Peak_level: str | None = None
    RMS_level: str | None = None
    ch1_Peak_level: str | None = None
    ch1_RMS_level: str | None = None
    ch2_Peak_level: str | None = None
    ch2_RMS_level: str | None = None


class WaveformSamplesResponse(BaseModel):
    """JSON waveform data with amplitude samples array."""

    video_id: str
    channels: int
    samples_per_second: int
    samples: list[WaveformSample]
