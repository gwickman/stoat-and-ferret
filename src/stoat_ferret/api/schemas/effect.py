"""Effect API response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ParameterSchemaResponse(BaseModel):
    """Structured parameter metadata for a single effect parameter.

    Emitted as an element of ``EffectResponse.parameters``. Mirrors the
    Rust ``ParameterSchema`` PyO3 type so AI agents can discover valid
    parameter types, bounds, enum domains, and natural-language hints.
    """

    name: str
    param_type: str
    default_value: int | float | str | bool | None = None
    min_value: float | None = None
    max_value: float | None = None
    enum_values: list[str] | None = None
    description: str
    ai_hint: str


class EffectResponse(BaseModel):
    """Response schema for a single effect.

    Contains the effect metadata, parameter schema, AI hints,
    and a filter preview string. The ``parameters`` list is a structured
    decomposition of ``parameter_schema`` intended for AI agent discovery;
    ``ai_summary`` and ``example_prompt`` give agents a one-line description
    and a natural-language invocation example.
    """

    effect_type: str
    name: str
    description: str
    parameter_schema: dict[str, Any]
    ai_hints: dict[str, str]
    filter_preview: str
    parameters: list[ParameterSchemaResponse]
    ai_summary: str
    example_prompt: str


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


class EffectPreviewRequest(BaseModel):
    """Request schema for previewing an effect's filter string."""

    effect_type: str
    parameters: dict[str, Any]


class EffectPreviewResponse(BaseModel):
    """Response schema for an effect filter string preview."""

    effect_type: str
    filter_string: str


class EffectUpdateRequest(BaseModel):
    """Request schema for updating an effect at a specific index."""

    parameters: dict[str, Any]


class EffectDeleteResponse(BaseModel):
    """Response schema for a deleted effect."""

    index: int
    deleted_effect_type: str


class EffectThumbnailRequest(BaseModel):
    """Request schema for generating an effect preview thumbnail."""

    effect_name: str
    video_path: str
    parameters: dict[str, Any]


class TransitionRequest(BaseModel):
    """Request schema for applying a transition between two clips."""

    source_clip_id: str
    target_clip_id: str
    transition_type: str
    parameters: dict[str, Any]


class EffectTransitionResponse(BaseModel):
    """Response schema for a successfully applied transition."""

    id: str
    source_clip_id: str
    target_clip_id: str
    transition_type: str
    parameters: dict[str, Any]
    filter_string: str
