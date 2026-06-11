"""Clip API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ClipCreate(BaseModel):
    """Create clip request.

    Supports both file clips (source_video_id required) and generator clips
    (generator_params required, source_video_id must be null).
    """

    model_config = ConfigDict(extra="forbid")

    clip_type: Literal["file", "generator"] = "file"
    source_video_id: str | None = None
    generator_params: dict[str, Any] | None = None
    in_point: int = Field(..., ge=0)
    out_point: int = Field(..., ge=0)
    timeline_position: int = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_clip_type_fields(self) -> ClipCreate:
        """Enforce cross-field validation based on clip_type."""
        if self.clip_type == "file":
            if self.source_video_id is None:
                raise ValueError("source_video_id is required for file clips")
            if self.generator_params is not None:
                raise ValueError("generator_params must be null for file clips")
        elif self.clip_type == "generator":
            if self.generator_params is None:
                raise ValueError("generator_params is required for generator clips")
            if self.source_video_id is not None:
                raise ValueError("source_video_id must be null for generator clips")
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
    clip_type: str
    generator_params: dict[str, Any] | None = None
    in_point: int
    out_point: int
    timeline_position: int
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
