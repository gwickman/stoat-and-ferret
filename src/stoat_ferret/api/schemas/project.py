"""Project API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    """Create project request."""

    name: str = Field(..., min_length=1)
    output_width: int = Field(default=1920, ge=1)
    output_height: int = Field(default=1080, ge=1)
    output_fps: int = Field(default=30, ge=1, le=120)


class ProjectResponse(BaseModel):
    """Project response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    output_width: int
    output_height: int
    output_fps: int
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Project list response."""

    projects: list[ProjectResponse]
    total: int
