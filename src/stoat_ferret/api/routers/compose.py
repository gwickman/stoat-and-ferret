"""Layout preset discovery and application endpoints."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status

from stoat_ferret.api.schemas.compose import (
    LayoutPresetListResponse,
    LayoutPresetResponse,
    LayoutRequest,
    LayoutResponse,
    LayoutResponsePosition,
    PositionModel,
)
from stoat_ferret_core import LayoutPosition, LayoutPreset, build_overlay_filter

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["compose"])

#: Metadata for each Rust LayoutPreset variant.
#: Uses a list of tuples because PyO3 enum variants are not hashable.
_PRESET_METADATA: list[tuple[LayoutPreset, dict[str, str | int]]] = [
    (
        LayoutPreset.PipTopLeft,
        {
            "description": "Picture-in-picture with overlay in the top-left corner",
            "ai_hint": "Use for commentary or reaction overlays positioned top-left",
            "min_inputs": 2,
            "max_inputs": 2,
        },
    ),
    (
        LayoutPreset.PipTopRight,
        {
            "description": "Picture-in-picture with overlay in the top-right corner",
            "ai_hint": "Use for commentary or reaction overlays positioned top-right",
            "min_inputs": 2,
            "max_inputs": 2,
        },
    ),
    (
        LayoutPreset.PipBottomLeft,
        {
            "description": "Picture-in-picture with overlay in the bottom-left corner",
            "ai_hint": "Use for webcam overlays or speaker insets positioned bottom-left",
            "min_inputs": 2,
            "max_inputs": 2,
        },
    ),
    (
        LayoutPreset.PipBottomRight,
        {
            "description": "Picture-in-picture with overlay in the bottom-right corner",
            "ai_hint": "Use for webcam overlays or speaker insets positioned bottom-right",
            "min_inputs": 2,
            "max_inputs": 2,
        },
    ),
    (
        LayoutPreset.SideBySide,
        {
            "description": "Two inputs displayed side by side, each taking half the width",
            "ai_hint": "Use for comparison views, interviews, or before/after layouts",
            "min_inputs": 2,
            "max_inputs": 2,
        },
    ),
    (
        LayoutPreset.TopBottom,
        {
            "description": "Two inputs stacked vertically, each taking half the height",
            "ai_hint": "Use for vertical comparisons or top/bottom split layouts",
            "min_inputs": 2,
            "max_inputs": 2,
        },
    ),
    (
        LayoutPreset.Grid2x2,
        {
            "description": "Four inputs arranged in a 2x2 grid",
            "ai_hint": "Use for multi-camera views, panel discussions, or quad layouts",
            "min_inputs": 4,
            "max_inputs": 4,
        },
    ),
]


def _build_preset_list() -> list[LayoutPresetResponse]:
    """Build the preset response list from the Rust LayoutPreset enum.

    Returns:
        List of LayoutPresetResponse objects for all known presets.
    """
    presets = []
    for variant, meta in _PRESET_METADATA:
        # Derive the name from the Rust enum variant's repr
        # LayoutPreset.PipTopLeft -> "PipTopLeft"
        name = repr(variant).split(".")[-1]
        presets.append(
            LayoutPresetResponse(
                name=name,
                description=str(meta["description"]),
                ai_hint=str(meta["ai_hint"]),
                min_inputs=int(meta["min_inputs"]),
                max_inputs=int(meta["max_inputs"]),
            )
        )
    return presets


@router.get("/compose/presets", response_model=LayoutPresetListResponse)
async def list_presets() -> LayoutPresetListResponse:
    """List all available layout presets with metadata.

    Returns all predefined layout configurations (PIP, split-screen, grid)
    with descriptions, AI hints, and input count requirements.

    Returns:
        List of all layout presets with their metadata.
    """
    presets = _build_preset_list()
    return LayoutPresetListResponse(presets=presets, total=len(presets))


#: Map preset name to (LayoutPreset variant, min_inputs).
_PRESET_BY_NAME: dict[str, tuple[LayoutPreset, int]] = {
    repr(variant).split(".")[-1]: (variant, int(meta["min_inputs"]))
    for variant, meta in _PRESET_METADATA
}


@router.post("/projects/{project_id}/compose/layout", response_model=LayoutResponse)
async def apply_layout(
    project_id: str,
    request: LayoutRequest,
) -> LayoutResponse:
    """Apply a layout preset or custom positions and preview the filter chain.

    Accepts a preset name or custom positions array, validates inputs,
    and returns positioned elements with an FFmpeg filter preview string.

    Args:
        project_id: The project ID (reserved for future use).
        request: Layout request with preset name or custom positions.

    Returns:
        Layout positions and filter preview string.

    Raises:
        HTTPException: 422 if positions are invalid or inputs insufficient.
    """
    if request.preset is not None:
        positions = _resolve_preset(request.preset, request.input_count)
    elif request.positions is not None:
        positions = _resolve_custom(request.positions)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INVALID_REQUEST",
                "message": "Either 'preset' or 'positions' must be provided",
            },
        )

    # Build filter preview by combining overlay filters for each position
    filters = [
        build_overlay_filter(pos, request.output_width, request.output_height, 0.0, 10.0)
        for pos in positions
    ]
    filter_preview = ";".join(filters)

    response_positions = [
        LayoutResponsePosition(
            x=pos.x, y=pos.y, width=pos.width, height=pos.height, z_index=pos.z_index
        )
        for pos in positions
    ]

    logger.info(
        "layout_applied",
        project_id=project_id,
        preset=request.preset,
        position_count=len(positions),
    )

    return LayoutResponse(positions=response_positions, filter_preview=filter_preview)


def _resolve_preset(preset_name: str, input_count: int) -> list[LayoutPosition]:
    """Resolve a preset name to layout positions.

    Args:
        preset_name: Name of the layout preset.
        input_count: Number of inputs for the layout.

    Returns:
        List of LayoutPosition objects.

    Raises:
        HTTPException: 422 if preset unknown or insufficient inputs.
    """
    entry = _PRESET_BY_NAME.get(preset_name)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INVALID_REQUEST",
                "message": f"Unknown preset: {preset_name}",
            },
        )

    variant, min_inputs = entry
    if input_count < min_inputs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INSUFFICIENT_INPUTS",
                "message": (
                    f"Preset '{preset_name}' requires at least {min_inputs} inputs, "
                    f"got {input_count}"
                ),
            },
        )

    return variant.positions(input_count)


def _resolve_custom(
    positions: list[PositionModel],
) -> list[LayoutPosition]:
    """Resolve custom positions to LayoutPosition objects.

    Args:
        positions: List of PositionModel objects with normalized coordinates.

    Returns:
        List of validated LayoutPosition objects.

    Raises:
        HTTPException: 422 if any coordinate is out of range.
    """
    from stoat_ferret_core._core import LayoutError

    result: list[LayoutPosition] = []
    for i, pos in enumerate(positions):
        lp = LayoutPosition(pos.x, pos.y, pos.width, pos.height, i)
        try:
            lp.validate()
        except LayoutError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "INVALID_LAYOUT_POSITION",
                    "message": f"Position {i}: {exc}",
                },
            ) from exc
        result.append(lp)
    return result
