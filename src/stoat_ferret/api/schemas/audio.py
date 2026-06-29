# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Audio mix API request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


# ---------------------------------------------------------------------------
# Multi-track audio schemas (BL-517)
# ---------------------------------------------------------------------------


class TrackAudioFields(BaseModel):
    """Audio-specific fields for a timeline track (multi-track mixer, BL-517).

    Mixed into TrackCreate and TrackResponse via inheritance. NULL kind is
    valid for video and text tracks; non-NULL kind indicates an audio sub-type.
    volume_envelope is an expression string rendered as volume='...':eval=frame.
    weight is the amix weighting factor (>= 0.0).
    """

    kind: Literal["music", "voice", "binaural", "sfx", "generic"] | None = Field(
        default=None,
        description="Audio sub-type; NULL for video/text tracks",
    )
    volume_envelope: str | None = Field(
        default=None,
        description="Volume expression (e.g. 'if(lt(t,1),t,1)'); NULL = unity gain",
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        description="amix weighting factor (>= 0.0)",
    )


class DuckingPairCreate(BaseModel):
    """Create a ducking pair configuration (BL-517).

    ducked_track_id and sidechain_track_id must differ; enforced by
    model_validator at the Pydantic layer (and again at DB via CHECK constraint).
    """

    model_config = ConfigDict(extra="forbid")

    ducked_track_id: str = Field(..., description="Track whose gain is reduced")
    sidechain_track_id: str = Field(
        ..., description="Trigger track, passed through clean into amix"
    )
    threshold: float = Field(
        default=0.02,
        ge=0.00097563,
        le=1.0,
        description="sidechaincompress threshold (0.00097563–1.0)",
    )
    ratio: float = Field(
        default=8.0,
        ge=1.0,
        le=20.0,
        description="Compression ratio (1–20)",
    )
    attack_ms: float = Field(
        default=20.0,
        ge=0.01,
        le=2000.0,
        description="Attack time in milliseconds (0.01–2000)",
    )
    release_ms: float = Field(
        default=300.0,
        ge=0.01,
        le=9000.0,
        description="Release time in milliseconds (0.01–9000)",
    )
    apply_pre_volume: bool = Field(
        default=False,
        description="Whether volume envelope wraps before (True) or after (False) compressor",
    )

    @model_validator(mode="before")
    @classmethod
    def check_track_ids_differ(cls, values: Any) -> Any:
        """Enforce ducked_track_id != sidechain_track_id."""
        if isinstance(values, dict) and values.get("ducked_track_id") == values.get(
            "sidechain_track_id"
        ):
            raise ValueError("ducked_track_id and sidechain_track_id must be different")
        return values


class DuckingPairUpdate(BaseModel):
    """Update mutable ducking pair parameters.

    ducked_track_id and sidechain_track_id are immutable after creation and
    are excluded; passing them returns HTTP 422 (extra='forbid').
    """

    model_config = ConfigDict(extra="forbid")

    threshold: float | None = Field(default=None, ge=0.00097563, le=1.0)
    ratio: float | None = Field(default=None, ge=1.0, le=20.0)
    attack_ms: float | None = Field(default=None, ge=0.01, le=2000.0)
    release_ms: float | None = Field(default=None, ge=0.01, le=9000.0)
    apply_pre_volume: bool | None = None


class DuckingPairResponse(BaseModel):
    """Response schema for a ducking pair configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    ducked_track_id: str
    sidechain_track_id: str
    threshold: float
    ratio: float
    attack_ms: float
    release_ms: float
    apply_pre_volume: bool
    created_at: datetime
    updated_at: datetime
