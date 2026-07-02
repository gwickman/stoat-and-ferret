# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Timeline API schemas."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TrackCreate(BaseModel):
    """Create track request."""

    model_config = ConfigDict(extra="forbid")

    track_type: str = Field(..., pattern=r"^(video|audio|text)$")
    label: str = Field(..., min_length=1)
    z_index: int | None = None
    muted: bool = False
    locked: bool = False
    kind: Literal["music", "voice", "binaural", "sfx", "generic"] | None = Field(
        default=None,
        description="Audio sub-type; NULL for video/text tracks",
    )
    volume_envelope: str | None = Field(
        default=None,
        description="Volume expression string; NULL = unity gain",
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        # le=10.0: 10x unity gain is the practical ceiling for amix weights;
        # ge=0.0 alone does not exclude inf (IEEE 754: inf >= 0.0 is True).
        le=10.0,
        description="amix weighting factor",
    )

    @field_validator("weight")
    @classmethod
    def weight_must_be_finite(cls, v: float) -> float:
        """Reject non-finite float values for weight.

        Pattern: same as src/stoat_ferret/api/schemas/effect.py:129-137.
        """
        if not math.isfinite(v):
            raise ValueError("weight must be a finite number")
        return v

    @field_validator("volume_envelope")
    @classmethod
    def volume_envelope_must_not_be_nonfinite_literal(cls, v: str | None) -> str | None:
        """Reject standalone non-finite literal tokens in volume_envelope."""
        if v is None:
            return v
        _NONFINITE_LITERALS = {"nan", "inf", "+inf", "-inf", "infinity", "-nan"}
        if v.strip().lower() in _NONFINITE_LITERALS:
            raise ValueError("volume_envelope must not be a non-finite literal token")
        return v


class TrackResponse(BaseModel):
    """Track response with clips."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    track_type: str
    label: str
    z_index: int
    muted: bool
    locked: bool
    kind: str | None = None
    volume_envelope: str | None = None
    weight: float = 1.0
    clips: list[TimelineClipResponse] = []


class TimelineClipCreate(BaseModel):
    """Assign clip to timeline track."""

    model_config = ConfigDict(extra="forbid")

    clip_id: str
    track_id: str
    timeline_start: float = Field(..., ge=0)
    timeline_end: float = Field(..., gt=0)


class TimelineClipUpdate(BaseModel):
    """Update clip timeline position."""

    model_config = ConfigDict(extra="forbid")

    timeline_start: float | None = Field(default=None, ge=0)
    timeline_end: float | None = Field(default=None, gt=0)
    track_id: str | None = None


class TimelineClipResponse(BaseModel):
    """Timeline clip response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    source_video_id: str | None
    clip_type: str = "file"
    track_id: str | None
    timeline_start: float | None
    timeline_end: float | None
    in_point: int
    out_point: int


class TransitionCreate(BaseModel):
    """Create transition between adjacent clips."""

    clip_a_id: str
    clip_b_id: str
    transition_type: str = Field(..., min_length=1)
    duration: float = Field(..., gt=0)


class AdjustedClipPosition(BaseModel):
    """Clip position after transition offset adjustment."""

    input_index: int
    timeline_start: float
    timeline_end: float


class TransitionResponse(BaseModel):
    """Transition response with computed offsets."""

    id: str
    transition_type: str
    duration: float
    filter_string: str
    timeline_offset: float
    clips: list[AdjustedClipPosition]


class TimelineResponse(BaseModel):
    """Full timeline response."""

    project_id: str
    tracks: list[TrackResponse]
    duration: float
    version: int
