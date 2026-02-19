"""Effect definitions and built-in effect registrations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from stoat_ferret_core import DrawtextBuilder, SpeedControl

if TYPE_CHECKING:
    from stoat_ferret.effects.registry import EffectRegistry


@dataclass(frozen=True)
class EffectDefinition:
    """Definition of an available effect with schema, hints, and preview.

    Attributes:
        name: Human-readable effect name.
        description: Description of what the effect does.
        parameter_schema: JSON Schema dict describing the effect parameters.
        ai_hints: Map of parameter name to AI hint string.
        preview_fn: Callable that returns an FFmpeg filter string preview
                     using default parameters.
    """

    name: str
    description: str
    parameter_schema: dict[str, object]
    ai_hints: dict[str, str]
    preview_fn: Callable[[], str] = field(repr=False)


def _text_overlay_preview() -> str:
    """Generate a filter preview for text overlay with default parameters."""
    f = (
        DrawtextBuilder("Sample Text")
        .fontsize(48)
        .fontcolor("white")
        .position("bottom_center", margin=20)
        .build()
    )
    return str(f)


def _speed_control_preview() -> str:
    """Generate a filter preview for speed control with default parameters."""
    sc = SpeedControl(2.0)
    video_filter = sc.setpts_filter()
    audio_filters = sc.atempo_filters()
    parts = [str(video_filter)]
    parts.extend(str(af) for af in audio_filters)
    return "; ".join(parts)


TEXT_OVERLAY = EffectDefinition(
    name="Text Overlay",
    description="Add text overlays to video with customizable font, position, and styling.",
    parameter_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The text to display"},
            "fontsize": {
                "type": "integer",
                "default": 48,
                "description": "Font size in pixels",
            },
            "fontcolor": {
                "type": "string",
                "default": "white",
                "description": "Font color name or hex value",
            },
            "position": {
                "type": "string",
                "enum": [
                    "center",
                    "bottom_center",
                    "top_left",
                    "top_right",
                    "bottom_left",
                    "bottom_right",
                ],
                "default": "bottom_center",
                "description": "Position preset for text placement",
            },
            "margin": {
                "type": "integer",
                "default": 10,
                "description": "Margin in pixels from edge",
            },
            "font": {
                "type": "string",
                "description": "Font name via fontconfig lookup",
            },
        },
        "required": ["text"],
    },
    ai_hints={
        "text": "The text content to overlay on the video",
        "fontsize": "Font size in pixels, typical range 12-72",
        "fontcolor": "Color name (white, yellow) or hex (#FF0000), append @0.5 for transparency",
        "position": "Where to place the text on screen",
        "margin": "Distance from screen edge in pixels, typical range 5-50",
        "font": "Fontconfig font name (e.g., 'monospace', 'Sans', 'Serif')",
    },
    preview_fn=_text_overlay_preview,
)

SPEED_CONTROL = EffectDefinition(
    name="Speed Control",
    description="Adjust video and audio playback speed with automatic tempo chaining.",
    parameter_schema={
        "type": "object",
        "properties": {
            "factor": {
                "type": "number",
                "minimum": 0.25,
                "maximum": 4.0,
                "default": 2.0,
                "description": "Speed multiplier",
            },
            "drop_audio": {
                "type": "boolean",
                "default": False,
                "description": "Drop audio instead of speed-adjusting it",
            },
        },
        "required": ["factor"],
    },
    ai_hints={
        "factor": (
            "Speed multiplier: 0.25-4.0. Values <1 slow down, >1 speed up. 2.0 = double speed"
        ),
        "drop_audio": "Set true for timelapse effects where audio is not needed",
    },
    preview_fn=_speed_control_preview,
)


def create_default_registry() -> EffectRegistry:
    """Create a registry with built-in effects registered.

    Returns:
        EffectRegistry with text_overlay and speed_control registered.
    """
    from stoat_ferret.effects.registry import EffectRegistry

    registry = EffectRegistry()
    registry.register("text_overlay", TEXT_OVERLAY)
    registry.register("speed_control", SPEED_CONTROL)
    return registry
