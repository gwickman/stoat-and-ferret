# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Project API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    """Create project request."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    output_width: int = Field(default=1920, ge=1)
    output_height: int = Field(default=1080, ge=1)
    output_fps: int = Field(default=30, ge=1, le=120)
    sample_rate: Literal[44100, 48000, 96000] = 48000
    bit_depth: Literal[16, 24, 32] = 24


class ProjectUpdate(BaseModel):
    """Update project request (partial)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1)
    output_width: int | None = Field(default=None, ge=1)
    output_height: int | None = Field(default=None, ge=1)
    output_fps: int | None = Field(default=None, ge=1, le=120)
    sample_rate: Literal[44100, 48000, 96000] | None = None
    bit_depth: Literal[16, 24, 32] | None = None


class ProjectResponse(BaseModel):
    """Project response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    output_width: int
    output_height: int
    output_fps: int
    sample_rate: int
    bit_depth: int
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Project list response."""

    projects: list[ProjectResponse]
    total: int
