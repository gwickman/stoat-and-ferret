# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""TTS cue API request and response schemas (BL-516)."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TtsBackend = Literal["piper_local", "openrouter_kokoro", "openrouter_commercial"]
TtsStatus = Literal["pending", "synthesising", "ready", "failed"]


def _compute_cache_key(text: str, voice: str, backend: str) -> str:
    """Compute SHA-256 cache key from text, voice, and backend."""
    payload = f"{text}::{voice}::{backend}"
    return hashlib.sha256(payload.encode()).hexdigest()


class TtsCueCreate(BaseModel):
    """Request schema for creating a TTS cue."""

    project_id: UUID = Field(..., description="Project UUID")
    track_id: str = Field(
        ..., description="Voice track ID (must reference a track with kind=voice)"
    )
    start_s: Annotated[float, Field(ge=0.0, description="Timeline placement in seconds")]
    text: str = Field(..., min_length=1, description="Text to synthesise")
    voice: str = Field(..., min_length=1, description="Voice identifier")
    backend: TtsBackend = Field(default="piper_local", description="TTS backend")
    gain_db: float = Field(
        default=0.0,
        ge=-60.0,
        le=6.0,
        description="Gain in dB (-60.0 to 6.0)",
    )
    pan: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Pan (-1.0 left to 1.0 right)",
    )

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """Validate text is non-empty after stripping."""
        if not v.strip():
            raise ValueError("text must not be empty or whitespace")
        return v

    @field_validator("voice")
    @classmethod
    def voice_not_empty(cls, v: str) -> str:
        """Validate voice is non-empty after stripping."""
        if not v.strip():
            raise ValueError("voice must not be empty or whitespace")
        return v


class TtsCueUpdate(BaseModel):
    """Request schema for updating a TTS cue (all fields optional)."""

    track_id: str | None = Field(
        default=None,
        description="Voice track ID; must reference a track with kind=voice",
    )
    start_s: float | None = Field(default=None, ge=0.0, description="Timeline placement in seconds")
    text: str | None = Field(default=None, min_length=1, description="Text to synthesise")
    voice: str | None = Field(default=None, min_length=1, description="Voice identifier")
    backend: TtsBackend | None = Field(default=None, description="TTS backend")
    gain_db: float | None = Field(
        default=None,
        ge=-60.0,
        le=6.0,
        description="Gain in dB (-60.0 to 6.0)",
    )
    pan: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Pan (-1.0 left to 1.0 right)",
    )

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str | None) -> str | None:
        """Validate text is non-empty after stripping (when provided)."""
        if v is not None and not v.strip():
            raise ValueError("text must not be empty or whitespace")
        return v

    @field_validator("voice")
    @classmethod
    def voice_not_empty(cls, v: str | None) -> str | None:
        """Validate voice is non-empty after stripping (when provided)."""
        if v is not None and not v.strip():
            raise ValueError("voice must not be empty or whitespace")
        return v

    @model_validator(mode="after")
    def at_least_one_field(self) -> TtsCueUpdate:
        """Require at least one field to be provided."""
        if all(
            v is None
            for v in [
                self.track_id,
                self.start_s,
                self.text,
                self.voice,
                self.backend,
                self.gain_db,
                self.pan,
            ]
        ):
            raise ValueError("at least one field must be provided for update")
        return self


class TtsCueResponse(BaseModel):
    """Response schema for a TTS cue."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    track_id: str
    start_s: float
    text: str
    voice: str
    backend: TtsBackend
    gain_db: float
    pan: float
    cache_key: str
    audio_path: str | None = None
    status: TtsStatus
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class TtsCueListResponse(BaseModel):
    """Response schema for a list of TTS cues."""

    items: list[TtsCueResponse]
    total: int


class VoiceInfo(BaseModel):
    """Information about an available TTS voice."""

    voice_id: str
    backend: TtsBackend
    language: str | None = None
    description: str | None = None


class VoicesResponse(BaseModel):
    """Response schema for available TTS voices."""

    voices: list[VoiceInfo]
