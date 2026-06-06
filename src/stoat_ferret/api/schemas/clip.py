"""Clip API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClipCreate(BaseModel):
    """Create clip request."""

    model_config = ConfigDict(extra="forbid")

    source_video_id: str
    in_point: int = Field(..., ge=0)
    out_point: int = Field(..., ge=0)
    timeline_position: int = Field(..., ge=0)


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
    source_video_id: str
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


class ClipListResponse(BaseModel):
    """Clip list response."""

    clips: list[ClipResponse]
    total: int
