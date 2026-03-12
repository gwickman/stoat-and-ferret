"""Layout preset discovery endpoint."""

from __future__ import annotations

import structlog
from fastapi import APIRouter

from stoat_ferret.api.schemas.compose import (
    LayoutPresetListResponse,
    LayoutPresetResponse,
)
from stoat_ferret_core import LayoutPreset

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
