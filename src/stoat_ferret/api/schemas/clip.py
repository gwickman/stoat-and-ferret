# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Clip API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ClipCreate(BaseModel):
    """Create clip request.

    Supports file clips (source_video_id required), generator clips
    (generator_params required, source_video_id must be null), and image
    clips (source_asset_id required, timeline_end required).
    """

    model_config = ConfigDict(extra="forbid")

    clip_type: Literal["file", "generator", "image"] = "file"
    source_video_id: str | None = None
    source_asset_id: str | None = None
    generator_params: dict[str, Any] | None = None
    in_point: int = Field(..., ge=0)
    out_point: int = Field(..., ge=0)
    timeline_position: int = Field(..., ge=0)
    timeline_start: float | None = None
    timeline_end: float | None = None

    def _validate_file_clip(self) -> None:
        """Validate file-clip specific constraints."""
        if self.source_video_id is None:
            raise ValueError("source_video_id is required for file clips")
        if self.generator_params is not None:
            raise ValueError("generator_params must be null for file clips")
        if self.source_asset_id is not None:
            raise ValueError("source_asset_id must be null for file clips")

    def _validate_generator_clip(self) -> None:
        """Validate generator-clip specific constraints."""
        if self.generator_params is None:
            raise ValueError("generator_params is required for generator clips")
        if self.source_video_id is not None:
            raise ValueError("source_video_id must be null for generator clips")
        if self.source_asset_id is not None:
            raise ValueError("source_asset_id must be null for generator clips")

    def _validate_image_clip(self) -> None:
        """Validate image-clip specific constraints."""
        if self.source_asset_id is None:
            raise ValueError("source_asset_id is required for image clips")
        if self.source_video_id is not None:
            raise ValueError("source_video_id must be null for image clips")
        if self.timeline_end is None:
            raise ValueError("timeline_end is required for image clips")
        timeline_start = self.timeline_start if self.timeline_start is not None else 0.0
        if self.timeline_end <= timeline_start:
            raise ValueError("timeline_end must be greater than timeline_start for image clips")

    @model_validator(mode="after")
    def validate_clip_type_fields(self) -> ClipCreate:
        """Enforce cross-field validation based on clip_type."""
        if self.clip_type == "file":
            self._validate_file_clip()
        elif self.clip_type == "generator":
            self._validate_generator_clip()
        elif self.clip_type == "image":
            self._validate_image_clip()
        return self


class ClipUpdate(BaseModel):
    """Update clip request."""

    model_config = ConfigDict(extra="forbid")

    in_point: int | None = Field(default=None, ge=0)
    out_point: int | None = Field(default=None, ge=0)
    timeline_position: int | None = Field(default=None, ge=0)


class ClipResponse(BaseModel):
    """Clip response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    source_video_id: str | None
    source_asset_id: str | None = None
    clip_type: str
    generator_params: dict[str, Any] | None = None
    in_point: int
    out_point: int
    timeline_position: int
    timeline_start: float | None = None
    timeline_end: float | None = None
    effects: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @field_validator("effects", mode="before")
    @classmethod
    def coerce_none_to_empty_list(cls, v: Any) -> list[dict[str, Any]]:
        """Convert None effects to empty list for consistent API response."""
        return v if v is not None else []

    @field_validator("clip_type", mode="before")
    @classmethod
    def default_clip_type(cls, v: Any) -> str:
        """Default to 'file' for clips without an explicit clip_type."""
        return v if v is not None else "file"


class ClipEffectsResponse(BaseModel):
    """Clip applied-effects list response."""

    effects: list[dict[str, Any]] = Field(default_factory=list)


class ClipListResponse(BaseModel):
    """Clip list response."""

    clips: list[ClipResponse]
    total: int


class ClipSplitRequest(BaseModel):
    """Split clip request — split_frame must be strictly between in_point and out_point."""

    model_config = ConfigDict(extra="forbid")

    split_frame: int


class ClipSplitResponse(BaseModel):
    """Split clip response containing the two resulting clips."""

    clip_a: ClipResponse
    clip_b: ClipResponse
