"""Compose API request and response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


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


class PositionModel(BaseModel):
    """A normalized layout position (0.0-1.0 range).

    All coordinate fields represent fractions of the output dimensions.
    Validation is performed by the endpoint handler to return domain-specific
    error codes (INVALID_LAYOUT_POSITION).
    """

    x: float = Field(..., description="Normalized x coordinate")
    y: float = Field(..., description="Normalized y coordinate")
    width: float = Field(..., description="Normalized width")
    height: float = Field(..., description="Normalized height")


class LayoutRequest(BaseModel):
    """Request schema for applying a layout.

    Provide either a preset name or a custom positions array, not both.
    If preset is provided, positions are generated from the preset.
    If positions are provided, they are used directly.
    """

    preset: str | None = Field(
        default=None, description="Layout preset name (e.g. 'PipTopLeft', 'Grid2x2')"
    )
    positions: list[PositionModel] | None = Field(
        default=None, description="Custom positions array with normalized coordinates"
    )
    input_count: int = Field(default=2, ge=1, description="Number of inputs for the layout")
    output_width: int = Field(default=1920, ge=1, description="Output width in pixels")
    output_height: int = Field(default=1080, ge=1, description="Output height in pixels")


class LayoutResponsePosition(BaseModel):
    """A positioned element in the layout response."""

    x: float
    y: float
    width: float
    height: float
    z_index: int


class LayoutResponse(BaseModel):
    """Response schema for layout application.

    Contains the resolved positions and a filter preview string.
    """

    positions: list[LayoutResponsePosition]
    filter_preview: str
