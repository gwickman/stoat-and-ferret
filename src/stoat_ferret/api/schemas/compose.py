"""Compose API response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class LayoutPresetResponse(BaseModel):
    """Response schema for a single layout preset.

    Contains the preset metadata including name, description,
    AI hint, and input count requirements.
    """

    name: str
    description: str
    ai_hint: str
    min_inputs: int
    max_inputs: int


class LayoutPresetListResponse(BaseModel):
    """Response schema for the layout preset list endpoint."""

    presets: list[LayoutPresetResponse]
    total: int
