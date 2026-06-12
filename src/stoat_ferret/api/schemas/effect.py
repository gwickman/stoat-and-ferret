"""Effect API response schemas."""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator


class AutomationKeyframe(BaseModel):
    """A single keyframe in an automation envelope.

    Attributes:
        t: Time position in seconds.
        value: Parameter value at this keyframe.
        curve: Interpolation curve kind between this and the next keyframe.
    """

    model_config = ConfigDict(from_attributes=True)

    t: float
    value: float
    curve: Literal["hold", "linear", "exponential", "ease_in_out"] = "linear"


class AutomationEnvelope(BaseModel):
    """A time-varying automation envelope for a numeric effect parameter.

    Attributes:
        default: Fallback scalar value when automation is not active.
        keyframes: Ordered list of keyframes with strictly increasing times.
    """

    model_config = ConfigDict(from_attributes=True)

    default: float
    keyframes: list[AutomationKeyframe]

    @model_validator(mode="before")
    @classmethod
    def validate_keyframes(cls, v: Any) -> Any:
        """Validate keyframe list before field construction."""
        if isinstance(v, dict) and "keyframes" in v:
            kfs = v.get("keyframes", [])
            if not kfs:
                raise ValueError("at least one keyframe required")
            for i in range(1, len(kfs)):
                t_prev = kfs[i - 1]["t"] if isinstance(kfs[i - 1], dict) else kfs[i - 1].t
                t_curr = kfs[i]["t"] if isinstance(kfs[i], dict) else kfs[i].t
                if t_curr <= t_prev:
                    raise ValueError(
                        f"keyframe times must be strictly increasing: "
                        f"t[{i - 1}]={t_prev} >= t[{i}]={t_curr}"
                    )
        return v


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
    and a natural-language invocation example. ``automatable_parameters``
    lists parameter names that accept automation envelopes (e.g. keyframe
    sequences), enabling agents to discover which parameters support
    time-varying control.
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
    automatable_parameters: list[str]


class EffectListResponse(BaseModel):
    """Response schema for the effect list endpoint."""

    effects: list[EffectResponse]
    total: int


class WindowSpec(BaseModel):
    """Optional time window for range-gating an effect to a sub-clip interval.

    When provided, the effect is active only between ``start_s`` and ``end_s``
    seconds relative to clip time, compiled to an FFmpeg
    ``enable='between(t,a,b)'`` clause.

    Attributes:
        start_s: Window start time in seconds (>= 0, finite).
        end_s: Window end time in seconds (> start_s, finite).
    """

    model_config = ConfigDict(from_attributes=True)

    start_s: float
    end_s: float

    @model_validator(mode="after")
    def check_window_values(self) -> WindowSpec:
        """Validate that start_s and end_s are finite and properly ordered."""
        if math.isnan(self.start_s) or math.isinf(self.start_s) or self.start_s < 0:
            raise ValueError("start_s must be a non-negative finite number")
        if math.isnan(self.end_s) or math.isinf(self.end_s):
            raise ValueError("end_s must be a finite number")
        if self.end_s <= self.start_s:
            raise ValueError("end_s must be greater than start_s")
        return self


class EffectApplyRequest(BaseModel):
    """Request schema for applying an effect to a clip."""

    effect_type: str
    parameters: dict[str, Any]
    window: WindowSpec | None = None


class EffectApplyResponse(BaseModel):
    """Response schema for a successfully applied effect."""

    effect_type: str
    parameters: dict[str, Any]
    filter_string: str
    filter_preview: str | None = None


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

    effect_type: str
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
