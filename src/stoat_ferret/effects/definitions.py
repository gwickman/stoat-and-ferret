"""Effect definitions and built-in effect registrations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from stoat_ferret_core import (
    AcrossfadeBuilder,
    AfadeBuilder,
    AmixBuilder,
    DrawtextBuilder,
    DuckingPattern,
    FadeBuilder,
    SpeedControl,
    TransitionType,
    VolumeBuilder,
    XfadeBuilder,
)

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
        build_fn: Callable that receives parameter dict and returns FFmpeg filter string.
    """

    name: str
    description: str
    parameter_schema: dict[str, object]
    ai_hints: dict[str, str]
    preview_fn: Callable[[], str] = field(repr=False)
    build_fn: Callable[[dict[str, Any]], str] = field(repr=False)


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


def _build_text_overlay(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for text overlay effect.

    Args:
        parameters: Effect parameters with required 'text' key.

    Returns:
        FFmpeg drawtext filter string.
    """
    text = parameters.get("text", "")
    builder = DrawtextBuilder(text)

    if "fontsize" in parameters:
        builder = builder.fontsize(parameters["fontsize"])
    if "fontcolor" in parameters:
        builder = builder.fontcolor(parameters["fontcolor"])
    if "position" in parameters:
        margin = parameters.get("margin", 10)
        builder = builder.position(parameters["position"], margin=margin)
    if "font" in parameters:
        builder = builder.font(parameters["font"])

    f = builder.build()
    return str(f)


def _speed_control_preview() -> str:
    """Generate a filter preview for speed control with default parameters."""
    sc = SpeedControl(2.0)
    video_filter = sc.setpts_filter()
    audio_filters = sc.atempo_filters()
    parts = [str(video_filter)]
    parts.extend(str(af) for af in audio_filters)
    return "; ".join(parts)


def _build_speed_control(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for speed control effect.

    Args:
        parameters: Effect parameters with required 'factor' key.

    Returns:
        FFmpeg setpts/atempo filter string.
    """
    factor = parameters.get("factor", 2.0)
    sc = SpeedControl(factor)
    if parameters.get("drop_audio", False):
        sc = sc.drop_audio(True)
    video_filter = sc.setpts_filter()
    audio_filters = sc.atempo_filters()
    parts = [str(video_filter)]
    parts.extend(str(af) for af in audio_filters)
    return "; ".join(parts)


def _build_audio_mix(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for audio mix effect.

    Args:
        parameters: Effect parameters with required 'inputs' key.

    Returns:
        FFmpeg amix filter string.
    """
    inputs = parameters.get("inputs", 2)
    builder = AmixBuilder(inputs)
    if "duration_mode" in parameters:
        builder = builder.duration_mode(parameters["duration_mode"])
    if "weights" in parameters:
        builder = builder.weights(parameters["weights"])
    if "normalize" in parameters:
        builder = builder.normalize(parameters["normalize"])
    f = builder.build()
    return str(f)


def _audio_mix_preview() -> str:
    """Generate a filter preview for audio mix with default parameters."""
    return str(AmixBuilder(2).build())


def _build_volume(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for volume effect.

    Args:
        parameters: Effect parameters with required 'volume' key.

    Returns:
        FFmpeg volume filter string.
    """
    volume = parameters.get("volume", 1.0)
    if isinstance(volume, str) and volume.endswith("dB"):
        builder = VolumeBuilder.from_db(volume)
    else:
        builder = VolumeBuilder(float(volume))
    if "precision" in parameters:
        builder = builder.precision(parameters["precision"])
    f = builder.build()
    return str(f)


def _volume_preview() -> str:
    """Generate a filter preview for volume with default parameters."""
    return str(VolumeBuilder(1.5).build())


def _build_audio_fade(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for audio fade effect.

    Args:
        parameters: Effect parameters with required 'fade_type' and 'duration' keys.

    Returns:
        FFmpeg afade filter string.
    """
    fade_type = parameters.get("fade_type", "in")
    duration = parameters.get("duration", 1.0)
    builder = AfadeBuilder(fade_type, duration)
    if "start_time" in parameters:
        builder = builder.start_time(parameters["start_time"])
    if "curve" in parameters:
        builder = builder.curve(parameters["curve"])
    f = builder.build()
    return str(f)


def _audio_fade_preview() -> str:
    """Generate a filter preview for audio fade with default parameters."""
    return str(AfadeBuilder("in", 1.0).build())


def _build_audio_ducking(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for audio ducking effect.

    Args:
        parameters: Effect parameters for ducking configuration.

    Returns:
        FFmpeg sidechaincompress filter graph string.
    """
    builder = DuckingPattern()
    if "threshold" in parameters:
        builder = builder.threshold(parameters["threshold"])
    if "ratio" in parameters:
        builder = builder.ratio(parameters["ratio"])
    if "attack" in parameters:
        builder = builder.attack(parameters["attack"])
    if "release" in parameters:
        builder = builder.release(parameters["release"])
    fg = builder.build()
    return str(fg)


def _audio_ducking_preview() -> str:
    """Generate a filter preview for audio ducking with default parameters."""
    return str(DuckingPattern().build())


def _build_video_fade(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for video fade effect.

    Args:
        parameters: Effect parameters with required 'fade_type' and 'duration' keys.

    Returns:
        FFmpeg fade filter string.
    """
    fade_type = parameters.get("fade_type", "in")
    duration = parameters.get("duration", 1.0)
    builder = FadeBuilder(fade_type, duration)
    if "start_time" in parameters:
        builder = builder.start_time(parameters["start_time"])
    if "color" in parameters:
        builder = builder.color(parameters["color"])
    if "alpha" in parameters:
        builder = builder.alpha(parameters["alpha"])
    f = builder.build()
    return str(f)


def _video_fade_preview() -> str:
    """Generate a filter preview for video fade with default parameters."""
    return str(FadeBuilder("in", 1.0).build())


def _build_xfade(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for xfade crossfade effect.

    Args:
        parameters: Effect parameters with required 'transition', 'duration', 'offset' keys.

    Returns:
        FFmpeg xfade filter string.
    """
    transition_name = parameters.get("transition", "fade")
    transition = TransitionType.from_str(transition_name)
    duration = parameters.get("duration", 1.0)
    offset = parameters.get("offset", 0.0)
    f = XfadeBuilder(transition, duration, offset).build()
    return str(f)


def _xfade_preview() -> str:
    """Generate a filter preview for xfade with default parameters."""
    return str(XfadeBuilder(TransitionType.Fade, 1.0, 0.0).build())


def _build_acrossfade(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for acrossfade audio crossfade effect.

    Args:
        parameters: Effect parameters with required 'duration' key.

    Returns:
        FFmpeg acrossfade filter string.
    """
    duration = parameters.get("duration", 1.0)
    builder = AcrossfadeBuilder(duration)
    if "curve1" in parameters:
        builder = builder.curve1(parameters["curve1"])
    if "curve2" in parameters:
        builder = builder.curve2(parameters["curve2"])
    if "overlap" in parameters:
        builder = builder.overlap(parameters["overlap"])
    f = builder.build()
    return str(f)


def _acrossfade_preview() -> str:
    """Generate a filter preview for acrossfade with default parameters."""
    return str(AcrossfadeBuilder(1.0).build())


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
    build_fn=_build_text_overlay,
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
    build_fn=_build_speed_control,
)

AUDIO_MIX = EffectDefinition(
    name="Audio Mix",
    description="Mix multiple audio input streams into a single output.",
    parameter_schema={
        "type": "object",
        "properties": {
            "inputs": {
                "type": "integer",
                "minimum": 2,
                "maximum": 32,
                "default": 2,
                "description": "Number of audio inputs to mix",
            },
            "duration_mode": {
                "type": "string",
                "enum": ["longest", "shortest", "first"],
                "default": "longest",
                "description": "How to determine output duration",
            },
            "weights": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Per-input volume weights",
            },
            "normalize": {
                "type": "boolean",
                "default": True,
                "description": "Whether to normalize the output",
            },
        },
        "required": ["inputs"],
    },
    ai_hints={
        "inputs": "Number of audio streams to mix (2-32)",
        "duration_mode": "Output length: longest input, shortest input, or first input",
        "weights": "Volume weight per input, e.g. [1.0, 0.5] for 2 inputs",
        "normalize": "Normalize output volume to prevent clipping",
    },
    preview_fn=_audio_mix_preview,
    build_fn=_build_audio_mix,
)

VOLUME = EffectDefinition(
    name="Volume",
    description="Adjust audio volume with linear or dB control.",
    parameter_schema={
        "type": "object",
        "properties": {
            "volume": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 10.0,
                "default": 1.0,
                "description": "Volume multiplier (0.0-10.0)",
            },
            "precision": {
                "type": "string",
                "enum": ["fixed", "float", "double"],
                "default": "float",
                "description": "Precision mode for volume calculation",
            },
        },
        "required": ["volume"],
    },
    ai_hints={
        "volume": "Volume multiplier: 0.0=silent, 1.0=original, 2.0=double. Range 0.0-10.0",
        "precision": "Calculation precision: fixed, float, or double",
    },
    preview_fn=_volume_preview,
    build_fn=_build_volume,
)

AUDIO_FADE = EffectDefinition(
    name="Audio Fade",
    description="Apply fade in or fade out to audio with configurable duration and curve.",
    parameter_schema={
        "type": "object",
        "properties": {
            "fade_type": {
                "type": "string",
                "enum": ["in", "out"],
                "description": "Fade direction",
            },
            "duration": {
                "type": "number",
                "minimum": 0.01,
                "default": 1.0,
                "description": "Fade duration in seconds",
            },
            "start_time": {
                "type": "number",
                "minimum": 0.0,
                "default": 0.0,
                "description": "Start time in seconds",
            },
            "curve": {
                "type": "string",
                "enum": [
                    "tri",
                    "qsin",
                    "hsin",
                    "esin",
                    "log",
                    "ipar",
                    "qua",
                    "cub",
                    "squ",
                    "cbr",
                    "par",
                ],
                "default": "tri",
                "description": "Fade curve type",
            },
        },
        "required": ["fade_type", "duration"],
    },
    ai_hints={
        "fade_type": "Direction: 'in' fades from silence, 'out' fades to silence",
        "duration": "Fade duration in seconds, typical range 0.5-3.0",
        "start_time": "When the fade starts in seconds from the beginning",
        "curve": "Fade curve shape: tri (linear), qsin (quarter sine), log, etc.",
    },
    preview_fn=_audio_fade_preview,
    build_fn=_build_audio_fade,
)

AUDIO_DUCKING = EffectDefinition(
    name="Audio Ducking",
    description="Lower music volume during speech using sidechain compression.",
    parameter_schema={
        "type": "object",
        "properties": {
            "threshold": {
                "type": "number",
                "minimum": 0.00097563,
                "maximum": 1.0,
                "default": 0.125,
                "description": "Detection threshold for speech",
            },
            "ratio": {
                "type": "number",
                "minimum": 1.0,
                "maximum": 20.0,
                "default": 2.0,
                "description": "Compression ratio",
            },
            "attack": {
                "type": "number",
                "minimum": 0.01,
                "maximum": 2000.0,
                "default": 20.0,
                "description": "Attack time in milliseconds",
            },
            "release": {
                "type": "number",
                "minimum": 0.01,
                "maximum": 9000.0,
                "default": 250.0,
                "description": "Release time in milliseconds",
            },
        },
    },
    ai_hints={
        "threshold": "Speech detection threshold: lower = more sensitive. Default 0.125",
        "ratio": "How much to reduce music: 2=half volume, higher=more reduction. Range 1-20",
        "attack": "How quickly ducking engages in ms. 20ms is responsive, 100ms is smooth",
        "release": "How quickly volume recovers in ms. 250ms is natural, 500ms is slow",
    },
    preview_fn=_audio_ducking_preview,
    build_fn=_build_audio_ducking,
)

VIDEO_FADE = EffectDefinition(
    name="Video Fade",
    description="Apply fade in or fade out to video with configurable color and duration.",
    parameter_schema={
        "type": "object",
        "properties": {
            "fade_type": {
                "type": "string",
                "enum": ["in", "out"],
                "description": "Fade direction",
            },
            "duration": {
                "type": "number",
                "minimum": 0.01,
                "default": 1.0,
                "description": "Fade duration in seconds",
            },
            "start_time": {
                "type": "number",
                "minimum": 0.0,
                "default": 0.0,
                "description": "Start time in seconds",
            },
            "color": {
                "type": "string",
                "default": "black",
                "description": "Fade color (named or hex #RRGGBB)",
            },
            "alpha": {
                "type": "boolean",
                "default": False,
                "description": "Whether to fade the alpha channel",
            },
        },
        "required": ["fade_type", "duration"],
    },
    ai_hints={
        "fade_type": "Direction: 'in' fades from color, 'out' fades to color",
        "duration": "Fade duration in seconds, typical range 0.5-3.0",
        "start_time": "When the fade starts in seconds",
        "color": "Fade color: 'black', 'white', or hex '#FF0000'",
        "alpha": "Fade alpha channel instead of to/from a color",
    },
    preview_fn=_video_fade_preview,
    build_fn=_build_video_fade,
)

XFADE = EffectDefinition(
    name="Crossfade (Video)",
    description="Crossfade between two video inputs with selectable transition effect.",
    parameter_schema={
        "type": "object",
        "properties": {
            "transition": {
                "type": "string",
                "default": "fade",
                "description": "Transition effect name (e.g., fade, wipeleft, dissolve)",
            },
            "duration": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 60.0,
                "default": 1.0,
                "description": "Transition duration in seconds",
            },
            "offset": {
                "type": "number",
                "minimum": 0.0,
                "default": 0.0,
                "description": "When the transition starts relative to first input",
            },
        },
        "required": ["transition", "duration", "offset"],
    },
    ai_hints={
        "transition": "Effect type: fade, wipeleft, dissolve, circleopen, etc.",
        "duration": "Transition duration in seconds, typical range 0.5-2.0",
        "offset": "Start time of transition relative to first input in seconds",
    },
    preview_fn=_xfade_preview,
    build_fn=_build_xfade,
)

ACROSSFADE = EffectDefinition(
    name="Crossfade (Audio)",
    description="Crossfade between two audio inputs with configurable curve types.",
    parameter_schema={
        "type": "object",
        "properties": {
            "duration": {
                "type": "number",
                "minimum": 0.01,
                "maximum": 60.0,
                "default": 1.0,
                "description": "Crossfade duration in seconds",
            },
            "curve1": {
                "type": "string",
                "enum": [
                    "tri",
                    "qsin",
                    "hsin",
                    "esin",
                    "log",
                    "ipar",
                    "qua",
                    "cub",
                    "squ",
                    "cbr",
                    "par",
                ],
                "default": "tri",
                "description": "Fade curve for first input",
            },
            "curve2": {
                "type": "string",
                "enum": [
                    "tri",
                    "qsin",
                    "hsin",
                    "esin",
                    "log",
                    "ipar",
                    "qua",
                    "cub",
                    "squ",
                    "cbr",
                    "par",
                ],
                "default": "tri",
                "description": "Fade curve for second input",
            },
            "overlap": {
                "type": "boolean",
                "default": True,
                "description": "Whether inputs overlap during crossfade",
            },
        },
        "required": ["duration"],
    },
    ai_hints={
        "duration": "Crossfade duration in seconds, typical range 0.5-3.0",
        "curve1": "Fade curve for first input: tri (linear), qsin (smooth), log, etc.",
        "curve2": "Fade curve for second input: tri (linear), qsin (smooth), log, etc.",
        "overlap": "Whether the two inputs overlap. Default true",
    },
    preview_fn=_acrossfade_preview,
    build_fn=_build_acrossfade,
)


def create_default_registry() -> EffectRegistry:
    """Create a registry with all built-in effects registered.

    Returns:
        EffectRegistry with all built-in effects registered.
    """
    from stoat_ferret.effects.registry import EffectRegistry

    registry = EffectRegistry()
    registry.register("text_overlay", TEXT_OVERLAY)
    registry.register("speed_control", SPEED_CONTROL)
    registry.register("audio_mix", AUDIO_MIX)
    registry.register("volume", VOLUME)
    registry.register("audio_fade", AUDIO_FADE)
    registry.register("audio_ducking", AUDIO_DUCKING)
    registry.register("video_fade", VIDEO_FADE)
    registry.register("xfade", XFADE)
    registry.register("acrossfade", ACROSSFADE)
    return registry
