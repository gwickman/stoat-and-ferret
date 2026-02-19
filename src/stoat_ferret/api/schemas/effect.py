"""Effect API response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class EffectResponse(BaseModel):
    """Response schema for a single effect.

    Contains the effect metadata, parameter schema, AI hints,
    and a filter preview string.
    """

    effect_type: str
    name: str
    description: str
    parameter_schema: dict[str, Any]
    ai_hints: dict[str, str]
    filter_preview: str


class EffectListResponse(BaseModel):
    """Response schema for the effect list endpoint."""

    effects: list[EffectResponse]
    total: int


class EffectApplyRequest(BaseModel):
    """Request schema for applying an effect to a clip."""

    effect_type: str
    parameters: dict[str, Any]


class EffectApplyResponse(BaseModel):
    """Response schema for a successfully applied effect."""

    effect_type: str
    parameters: dict[str, Any]
    filter_string: str
