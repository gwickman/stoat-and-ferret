"""Clip API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClipCreate(BaseModel):
    """Create clip request."""

    source_video_id: str
    in_point: int = Field(..., ge=0)
    out_point: int = Field(..., ge=0)
    timeline_position: int = Field(..., ge=0)


class ClipUpdate(BaseModel):
    """Update clip request."""

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
    effects: list[dict[str, Any]] | None = None
    created_at: datetime
    updated_at: datetime


class ClipListResponse(BaseModel):
    """Clip list response."""

    clips: list[ClipResponse]
    total: int
