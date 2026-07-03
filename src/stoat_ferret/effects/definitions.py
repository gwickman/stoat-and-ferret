# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Effect definitions and built-in effect registrations."""

from __future__ import annotations

import asyncio
import importlib.resources
import json
import re
from asyncio import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from stoat_ferret_core import (
    AcrossfadeBuilder,
    AfadeBuilder,
    AmixBuilder,
    BlurBuilder,
    BurnedSubtitleBuilder,
    BurnedSubtitleSpec,
    ChromaKeyBuilder,
    ChromaticAberrationBuilder,
    ColorKeyBuilder,
    ColorLutBuilder,
    ConvolutionReverbBuilder,
    CurvesBuilder,
    DeesserBuilder,
    DeplosiveBuilder,
    DrawtextBuilder,
    DuckingPattern,
    FadeBuilder,
    FramerateConvertBuilder,
    FramerateMode,
    FreezeFrameBuilder,
    GradientGeneratorBuilder,
    LensDistortBuilder,
    LimiterBuilder,
    LoudnormBuilder,
    MultibandCompressorBuilder,
    NoiseGeneratorBuilder,
    NoiseReductionBuilder,
    OpacityBuilder,
    PanBuilder,
    ParametricEqBuilder,
    ReverseBuilder,
    ScaleBuilder,
    ScriptEntry,
    SharpenBuilder,
    SpeedControl,
    SpeedSegment,
    SubtitleScriptBuilder,
    SubtitleScriptSpec,
    TimeStretchBuilder,
    TransitionType,
    VariableSpeedBuilder,
    VignetteBuilder,
    VolumeBuilder,
    XfadeBuilder,
    ZoompanBuilder,
)

if TYPE_CHECKING:
    from stoat_ferret.effects.registry import EffectRegistry


class RenderError(Exception):
    """Raised when a render-related operation fails."""


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
        ai_summary: One-sentence natural-language summary for AI agent discovery.
        example_prompt: Example natural-language prompt that would invoke this effect.
        stream_kind: FFmpeg stream kind this effect applies to (e.g. "v", "a", "").
        arity: Number of input streams this effect consumes (default 1).
        chain_safe: Whether this effect can be chained with other effects in a single graph.
        timebase_mutating: Whether this effect changes the stream timebase.
        timeline_T_capable: Whether this effect supports the FFmpeg T (timeline) flag for
            enable expressions. When True and a window is present, the translator emits
            :enable='between(t,start_s,end_s)' instead of split/trim/concat.
        requires_path_escape: Whether this effect requires path escaping for option values.
        value_kind_per_option: Maps option names to their ValueKind string for escape dispatch.
    """

    name: str
    description: str
    parameter_schema: dict[str, object]
    ai_hints: dict[str, str]
    preview_fn: Callable[[], str] = field(repr=False)
    build_fn: Callable[[dict[str, Any]], str] = field(repr=False)
    ai_summary: str = ""
    example_prompt: str = ""
    automatable: frozenset[str] = field(default_factory=frozenset)
    automation_filter_template: str | None = None
    stream_kind: str = ""
    arity: int = 1
    chain_safe: bool = True
    timebase_mutating: bool = False
    timeline_T_capable: bool = False
    requires_path_escape: bool = False
    value_kind_per_option: dict[str, str] = field(default_factory=dict)


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
                "minimum": 8,
                "maximum": 256,
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
    ai_summary="Burn captions, titles, or watermark text onto a video clip.",
    example_prompt='Add the caption "Breaking News" in the bottom center of the clip.',
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
    ai_summary="Speed up or slow down video playback with matched audio retiming.",
    example_prompt="Play this clip back at 2x speed to create a fast-forward effect.",
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
    ai_summary="Combine multiple audio tracks into a single mixed stream.",
    example_prompt="Mix the narration and background music tracks into one output.",
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
    ai_summary="Adjust audio loudness up or down using a linear multiplier or dB value.",
    example_prompt="Reduce the audio volume on this clip to 50%.",
    automatable=frozenset({"volume"}),
    automation_filter_template="volume='{expr}':eval=frame",
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
    ai_summary="Fade audio in from silence or out to silence over a duration.",
    example_prompt="Fade the audio in over 2 seconds at the start of the clip.",
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
    ai_summary="Automatically lower music volume when a voice track is active.",
    example_prompt="Duck the background music whenever the narrator is speaking.",
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
    ai_summary="Fade a clip in from a solid color or out to a solid color.",
    example_prompt="Fade out to black over the final 1.5 seconds of this clip.",
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
    ai_summary="Crossfade between two video clips using a selectable transition style.",
    example_prompt='Transition between these two clips with a 1-second "wipeleft" effect.',
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
    ai_summary="Crossfade the audio of two adjacent clips so they blend smoothly.",
    example_prompt="Crossfade the audio of these two clips over 2 seconds.",
)


def _build_noise_reduction(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for noise reduction effect.

    Args:
        parameters: Effect parameters with required 'mode' key and optional
            'strength' (broadband) or 'threshold' (adeclick).

    Returns:
        FFmpeg afftdn or adeclick filter string.
    """
    mode = parameters.get("mode", "broadband")
    builder = NoiseReductionBuilder(mode)
    if mode == "broadband" and "strength" in parameters:
        builder = builder.strength(float(parameters["strength"]))
    elif mode == "adeclick" and "threshold" in parameters:
        builder = builder.threshold(float(parameters["threshold"]))
    return str(builder.build())


def _noise_reduction_preview() -> str:
    """Generate a filter preview for noise reduction with default parameters."""
    return str(NoiseReductionBuilder("broadband").strength(0.5).build())


NOISE_REDUCTION = EffectDefinition(
    name="Noise Reduction",
    description="Reduce broadband noise or remove clicks and impulses from audio.",
    parameter_schema={
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["broadband", "adeclick"],
                "default": "broadband",
                "description": "Noise reduction mode: broadband (afftdn) or adeclick",
            },
            "strength": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 0.5,
                "description": "Noise reduction strength (0.0–1.0). Broadband mode only.",
            },
            "threshold": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 0.5,
                "description": "Click detection threshold (0.0=sensitive, 1.0=aggressive).",
            },
        },
        "required": [],
        "additionalProperties": False,
    },
    ai_hints={
        "mode": (
            "Use 'broadband' for hum, room noise, HVAC, or tape hiss. "
            "Use 'adeclick' for vinyl pops, mic plosives, or digital glitches."
        ),
        "strength": "Start at 0.3-0.5 for speech; higher values may remove low-frequency content.",
        "threshold": "Lower values catch more clicks; raise if clean audio is being clipped.",
    },
    preview_fn=_noise_reduction_preview,
    build_fn=_build_noise_reduction,
    ai_summary="Reduce background noise or remove clicks from audio using FFmpeg adaptive filters.",
    example_prompt="Remove the background hum from the narration track.",
)


def _build_deesser(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for de-esser effect.

    Args:
        parameters: Effect parameters with optional 'frequency' (Hz) and 'mode'.

    Returns:
        FFmpeg deesser filter string.
    """
    frequency = float(parameters.get("frequency", 6000.0))
    builder = DeesserBuilder(frequency)
    if "mode" in parameters:
        builder = builder.mode(parameters["mode"])
    return str(builder.build())


def _deesser_preview() -> str:
    """Generate a filter preview for de-esser with default parameters."""
    return str(DeesserBuilder(6000.0).build())


DEESSER = EffectDefinition(
    name="De-esser",
    description="Reduce harsh sibilant sounds ('s', 'sh') in voice recordings.",
    parameter_schema={
        "type": "object",
        "properties": {
            "frequency": {
                "type": "number",
                "minimum": 1000.0,
                "maximum": 16000.0,
                "default": 6000.0,
                "description": "Sibilance detection frequency in Hz (1000–16000).",
            },
            "mode": {
                "type": "string",
                "enum": ["wide", "split"],
                "default": "wide",
                "description": (
                    "Filter mode: wide (affects full range) or split (splits at frequency)."
                ),
            },
        },
        "required": [],
        "additionalProperties": False,
    },
    ai_hints={
        "frequency": (
            "Typical sibilance sits between 5000–8000 Hz for most voices. "
            "Use lower values (3000–5000) for deep voices."
        ),
        "mode": "Use 'wide' for general de-essing; use 'split' for more targeted treatment.",
    },
    preview_fn=_deesser_preview,
    build_fn=_build_deesser,
    ai_summary="Remove harsh 's' and 'sh' sounds from voice audio using FFmpeg de-esser filter.",
    example_prompt="The narration sounds too sibilant, fix the harshness on the 's' sounds.",
)


def _build_deplosive(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for de-plosive effect.

    Args:
        parameters: Effect parameters with optional 'cutoff', 'threshold', 'ratio'.

    Returns:
        FFmpeg highpass+acompressor filter chain string.
    """
    builder = DeplosiveBuilder()
    if "cutoff" in parameters:
        builder = builder.cutoff(float(parameters["cutoff"]))
    if "threshold" in parameters:
        builder = builder.threshold(float(parameters["threshold"]))
    if "ratio" in parameters:
        builder = builder.ratio(float(parameters["ratio"]))
    return str(builder.build())


def _deplosive_preview() -> str:
    """Generate a filter preview for de-plosive with default parameters."""
    return str(DeplosiveBuilder().build())


DEPLOSIVE = EffectDefinition(
    name="De-plosive",
    description="Attenuate low-frequency plosive bursts ('p', 'b') in voice recordings.",
    parameter_schema={
        "type": "object",
        "properties": {
            "cutoff": {
                "type": "number",
                "minimum": 10.0,
                "maximum": 200.0,
                "default": 60.0,
                "description": (
                    "Highpass cutoff frequency in Hz (10–200). Energy below this is removed."
                ),
            },
            "threshold": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 0.1,
                "description": "Acompressor threshold (0.0–1.0). Lower values catch more plosives.",
            },
            "ratio": {
                "type": "number",
                "minimum": 1.0,
                "maximum": 20.0,
                "default": 4.0,
                "description": (
                    "Acompressor ratio (1.0–20.0). Higher values apply more compression."
                ),
            },
        },
        "required": [],
        "additionalProperties": False,
    },
    ai_hints={
        "cutoff": "60 Hz is a safe default; raise to 80–120 Hz if plosives are severe.",
        "threshold": "Start at 0.1; lower to 0.05 if plosives persist.",
        "ratio": "4:1 is typical for voice; increase to 8:1 or higher for severe plosives.",
    },
    preview_fn=_deplosive_preview,
    build_fn=_build_deplosive,
    ai_summary="Remove 'p' and 'b' plosive thumps from voice audio using highpass and compression.",
    example_prompt=(
        "There are loud plosive pops when the narrator says 'p' and 'b' sounds, please fix."
    ),
)


def _build_time_stretch(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for time-stretch effect.

    Args:
        parameters: Effect parameters with required 'factor' and optional 'mode'.

    Returns:
        FFmpeg atempo or rubberband filter chain string.
    """
    factor = float(parameters.get("factor", 1.0))
    mode = str(parameters.get("mode", "atempo"))
    return str(TimeStretchBuilder(factor, mode).build())


def _time_stretch_preview() -> str:
    """Generate a filter preview for time-stretch with default parameters."""
    return str(TimeStretchBuilder(0.8, "atempo").build())


TIME_STRETCH = EffectDefinition(
    name="Time Stretch",
    description="Adjust audio playback speed without affecting pitch.",
    parameter_schema={
        "type": "object",
        "properties": {
            "factor": {
                "type": "number",
                "minimum": 0.01,
                "maximum": 4.0,
                "default": 1.0,
                "description": (
                    "Time-stretch factor (0.0 exclusive – 4.0 inclusive). "
                    "Values < 1.0 slow down; values > 1.0 speed up."
                ),
            },
            "mode": {
                "type": "string",
                "enum": ["atempo", "rubberband", "auto"],
                "default": "atempo",
                "description": (
                    "Filter engine: 'atempo' (always available), "
                    "'rubberband' (high-quality, optional FFmpeg build), "
                    "or 'auto' (use rubberband if available, else atempo)."
                ),
            },
        },
        "required": ["factor"],
        "additionalProperties": False,
    },
    ai_hints={
        "factor": (
            "Use 0.8 to slow speech by 20%, 1.25 to speed it up by 25%. "
            "Factors outside [0.5, 2.0] are automatically chained."
        ),
        "mode": "Leave as 'atempo' unless rubberband is known to be available.",
    },
    preview_fn=_time_stretch_preview,
    build_fn=_build_time_stretch,
    ai_summary=(
        "Stretch or compress audio duration without pitch change using FFmpeg atempo/rubberband."
    ),
    example_prompt="Speed up the narration by 25% without changing the pitch.",
)


def _build_mastering_limiter(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for mastering limiter effect.

    Args:
        parameters: Effect parameters with required 'ceiling_dbtp'.

    Returns:
        FFmpeg alimiter filter string.
    """
    ceiling_dbtp = float(parameters.get("ceiling_dbtp", -1.0))
    return str(LimiterBuilder(ceiling_dbtp).build())


def _mastering_limiter_preview() -> str:
    """Generate a filter preview for mastering limiter with default parameters."""
    return str(LimiterBuilder(-1.0).build())


MASTERING_LIMITER = EffectDefinition(
    name="Mastering Limiter",
    description=(
        "True-peak limiter for master bus protection. "
        "Caps audio so true-peak does not exceed the configured ceiling."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "ceiling_dbtp": {
                "type": "number",
                "maximum": 0.0,
                "default": -1.0,
                "description": (
                    "True-peak ceiling in dBTP (must be <= 0.0). "
                    "Example: -1.0 dBTP → limit=0.891251 linear ratio."
                ),
            },
        },
        "required": ["ceiling_dbtp"],
        "additionalProperties": False,
    },
    ai_hints={
        "ceiling_dbtp": (
            "Use -1.0 dBTP for standard streaming/broadcast delivery. "
            "Use -0.1 dBTP for maximum loudness with minimal headroom. "
            "Values must be <= 0.0."
        ),
    },
    preview_fn=_mastering_limiter_preview,
    build_fn=_build_mastering_limiter,
    ai_summary=("Limit master bus true-peak to a configured dBTP ceiling using FFmpeg alimiter."),
    example_prompt="Limit the master to -1 dBTP true peak for streaming delivery.",
)


@dataclass
class LoudnormPassOneResult:
    """Pass-1 measurement result from FFmpeg loudnorm filter.

    Parsed from the JSON block that loudnorm emits to stderr during the measurement pass.
    Use :meth:`from_stderr` to construct from raw FFmpeg stderr output.
    """

    measured_i: float
    measured_lra: float
    measured_tp: float
    offset: float

    @classmethod
    def from_stderr(cls, stderr: str) -> LoudnormPassOneResult:
        """Parse loudnorm pass-1 JSON from FFmpeg stderr.

        Finds the last JSON object in stderr (loudnorm emits it at the end of the
        filter graph analysis) and extracts the four measurement fields.

        Args:
            stderr: Raw stderr string from the FFmpeg pass-1 run.

        Returns:
            LoudnormPassOneResult with parsed measurements.

        Raises:
            RenderError: If no valid JSON block is found or required fields are missing.
        """
        match = re.search(r"\{[^{}]*\}", stderr, re.DOTALL)
        if not match:
            raise RenderError(
                f"loudnorm pass-1 produced no JSON block in stderr. stderr={stderr!r}"
            )
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError as exc:
            raise RenderError(
                f"loudnorm pass-1 JSON is malformed: {exc}. stderr={stderr!r}"
            ) from exc

        required = ("input_i", "input_lra", "input_tp", "target_offset")
        missing = [k for k in required if k not in data]
        if missing:
            raise RenderError(
                f"loudnorm pass-1 JSON missing required fields {missing}. data={data!r}"
            )

        try:
            return cls(
                measured_i=float(data["input_i"]),
                measured_lra=float(data["input_lra"]),
                measured_tp=float(data["input_tp"]),
                offset=float(data["target_offset"]),
            )
        except (ValueError, TypeError) as exc:
            raise RenderError(
                f"loudnorm pass-1 JSON field is not a valid float: {exc}. data={data!r}"
            ) from exc


async def _run_loudnorm_pass1(
    artifact_path: str,
    target_lufs: float,
    ceiling_dbtp: float,
    lra: float = 11.0,
) -> LoudnormPassOneResult:
    """Run FFmpeg loudnorm pass-1 measurement on an audio/video file.

    Uses asyncio.create_subprocess_exec (QCService pattern) with stdout=PIPE,
    stderr=PIPE. The loudnorm JSON measurement is written to stderr by FFmpeg.

    Args:
        artifact_path: Path to the input audio or video file.
        target_lufs: Target integrated loudness in LUFS (e.g. -16.0).
        ceiling_dbtp: True-peak ceiling in dBTP (must be <= 0.0).
        lra: Loudness range target in LU (default 11.0).

    Returns:
        LoudnormPassOneResult with the four measured values.

    Raises:
        RenderError: If FFmpeg fails or the stderr JSON cannot be parsed.
    """
    builder = LoudnormBuilder(target_lufs, ceiling_dbtp, lra)
    filter_str = str(builder.build_pass1())

    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i",
        artifact_path,
        "-af",
        filter_str,
        "-f",
        "null",
        "-",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout_b, stderr_b = await proc.communicate()
    stderr_text = stderr_b.decode("utf-8", errors="replace")

    if proc.returncode != 0:
        raise RenderError(
            f"loudnorm pass-1 FFmpeg exited {proc.returncode}. stderr={stderr_text!r}"
        )

    return LoudnormPassOneResult.from_stderr(stderr_text)


def _build_loudness_normalize(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for loudness_normalize effect.

    When pass-1 measurements are present in parameters (measured_i, measured_lra,
    measured_tp, offset), builds the pass-2 linear normalization filter.
    Otherwise builds the pass-1 measurement filter (used for schema preview and
    API-level inspection without a real audio file).

    Args:
        parameters: Effect parameters dict. May contain:
            - target_lufs (float, default -16.0)
            - ceiling_dbtp (float, default -1.0)
            - lra (float, default 11.0)
            - delivery_profile_target_lufs (float, optional): takes precedence over target_lufs
            - measured_i / measured_lra / measured_tp / offset: pass-1 measurements

    Returns:
        FFmpeg loudnorm filter string.
    """
    target_lufs = float(
        parameters.get("delivery_profile_target_lufs", parameters.get("target_lufs", -16.0))
    )
    ceiling_dbtp = float(parameters.get("ceiling_dbtp", -1.0))
    lra = float(parameters.get("lra", 11.0))
    builder = LoudnormBuilder(target_lufs, ceiling_dbtp, lra)

    if all(k in parameters for k in ("measured_i", "measured_lra", "measured_tp", "offset")):
        return str(
            builder.build_pass2(
                float(parameters["measured_i"]),
                float(parameters["measured_lra"]),
                float(parameters["measured_tp"]),
                float(parameters["offset"]),
            )
        )
    return str(builder.build_pass1())


def _loudness_normalize_preview() -> str:
    """Generate a filter preview for loudness_normalize with default parameters."""
    return str(LoudnormBuilder(-16.0, -1.0, 11.0).build_pass1())


LOUDNESS_NORMALIZE = EffectDefinition(
    name="Loudness Normalize",
    description=(
        "Two-pass LUFS loudness normalization to a target level with true-peak ceiling. "
        "Uses EBU R128 / ITU-R BS.1770 integrated loudness measurement."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "target_lufs": {
                "type": "number",
                "maximum": 0.0,
                "default": -16.0,
                "description": (
                    "Target integrated loudness in LUFS (must be <= 0.0). "
                    "Common values: -16 LUFS (podcasts), -14 LUFS (streaming), "
                    "-23 LUFS (broadcast EBU R128)."
                ),
            },
            "ceiling_dbtp": {
                "type": "number",
                "maximum": 0.0,
                "default": -1.0,
                "description": (
                    "True-peak ceiling in dBTP (must be <= 0.0). "
                    "Use -1.0 for standard streaming delivery."
                ),
            },
            "lra": {
                "type": "number",
                "minimum": 1.0,
                "maximum": 50.0,
                "default": 11.0,
                "description": (
                    "Loudness range target in LU (1–50). EBU R128 recommendation is 11.0 LU."
                ),
            },
        },
        "required": [],
        "additionalProperties": False,
    },
    ai_hints={
        "target_lufs": (
            "Use -16 LUFS for podcasts and general content, -14 for streaming platforms "
            "(Spotify/Apple Music), -23 for broadcast (EBU R128). Values must be <= 0."
        ),
        "ceiling_dbtp": "Use -1.0 dBTP for standard delivery; -0.1 for maximum loudness.",
        "lra": "Leave at 11.0 for most content. Reduce for tightly compressed material.",
    },
    preview_fn=_loudness_normalize_preview,
    build_fn=_build_loudness_normalize,
    ai_summary=(
        "Normalize audio loudness to a target LUFS level using two-pass EBU R128 measurement."
    ),
    example_prompt="Normalize the audio to -16 LUFS for podcast delivery.",
)


def _build_parametric_eq(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for parametric_eq effect.

    Args:
        parameters: Effect parameters with required 'bands' key — a list of
            dicts each with 'frequency', 'gain', and 'width' fields.

    Returns:
        FFmpeg anequalizer filter string.
    """
    bands = parameters.get("bands", [])
    return str(ParametricEqBuilder(bands).build())


def _parametric_eq_preview() -> str:
    """Generate a filter preview for parametric_eq with default parameters."""
    return str(ParametricEqBuilder([{"frequency": 1000.0, "gain": 0.0, "width": 200.0}]).build())


PARAMETRIC_EQ = EffectDefinition(
    name="Parametric EQ",
    description=(
        "Multi-band parametric equalizer for tonal shaping and vocal clarity. "
        "Each band has configurable frequency, gain, and width."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "bands": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["frequency", "gain", "width"],
                    "properties": {
                        "frequency": {
                            "type": "number",
                            "minimum": 20,
                            "maximum": 20000,
                            "description": "Band center frequency in Hz (20–20000).",
                        },
                        "gain": {
                            "type": "number",
                            "minimum": -24,
                            "maximum": 24,
                            "description": "Band gain in dB (−24 to +24).",
                        },
                        "width": {
                            "type": "number",
                            "exclusiveMinimum": 0,
                            "description": "Band width in Hz (must be > 0).",
                        },
                    },
                    "additionalProperties": False,
                },
                "description": "Array of EQ bands. Minimum 1 band required.",
            },
        },
        "required": ["bands"],
    },
    ai_hints={
        "bands": (
            "List of EQ bands. Each band needs frequency (20–20000 Hz), gain (−24 to +24 dB), "
            "and width (Hz, > 0). Example: boost vocals at 3000 Hz, cut mud at 200 Hz."
        ),
    },
    preview_fn=_parametric_eq_preview,
    build_fn=_build_parametric_eq,
    ai_summary=(
        "Apply multi-band parametric EQ to boost or cut specific frequency ranges in audio."
    ),
    example_prompt="Boost presence at 3 kHz by 4 dB and cut muddiness at 200 Hz by 3 dB.",
)


def _build_multiband_compressor(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter graph string for multiband_compressor effect.

    Args:
        parameters: Effect parameters with required 'bands' key — a list of
            dicts each with 'threshold', 'ratio', 'attack', and 'release' fields.

    Returns:
        FFmpeg filter graph string with asplit→acompressor×N→amix topology.
    """
    bands = parameters.get("bands", [])
    return str(MultibandCompressorBuilder(bands).build())


def _multiband_compressor_preview() -> str:
    """Generate a filter preview for multiband_compressor with 3 default bands."""
    default_bands = [
        {"threshold": -20.0, "ratio": 2.0, "attack": 10.0, "release": 100.0},
        {"threshold": -24.0, "ratio": 3.0, "attack": 5.0, "release": 80.0},
        {"threshold": -30.0, "ratio": 4.0, "attack": 3.0, "release": 50.0},
    ]
    return str(MultibandCompressorBuilder(default_bands).build())


MULTIBAND_COMPRESSOR = EffectDefinition(
    name="Multiband Compressor",
    description=(
        "Multiband dynamics processor splitting audio into independent bands, "
        "each compressed with configurable threshold and ratio. "
        "Uses asplit → acompressor × N → amix FilterGraph topology."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "bands": {
                "type": "array",
                "minItems": 2,
                "items": {
                    "type": "object",
                    "required": ["threshold", "ratio", "attack", "release"],
                    "properties": {
                        "threshold": {
                            "type": "number",
                            "exclusiveMaximum": 0,
                            "description": "Compression threshold in dB (must be < 0).",
                        },
                        "ratio": {
                            "type": "number",
                            "exclusiveMinimum": 1.0,
                            "description": "Compression ratio (must be > 1.0).",
                        },
                        "attack": {
                            "type": "number",
                            "exclusiveMinimum": 0,
                            "description": "Attack time in ms (must be > 0).",
                        },
                        "release": {
                            "type": "number",
                            "exclusiveMinimum": 0,
                            "description": "Release time in ms (must be > 0).",
                        },
                    },
                    "additionalProperties": False,
                },
                "description": "Array of compressor bands. Minimum 2 bands required.",
            },
        },
        "required": ["bands"],
    },
    ai_hints={
        "bands": (
            "List of compressor bands. Each band needs threshold (dB, < 0), "
            "ratio (> 1.0), attack (ms, > 0), and release (ms, > 0). "
            "Default: 3 bands for low/mid/high. "
            "Example: threshold=-20, ratio=2.0, attack=10, release=100."
        ),
    },
    preview_fn=_multiband_compressor_preview,
    build_fn=_build_multiband_compressor,
    ai_summary=(
        "Apply multiband compression to independently control dynamics in low, "
        "mid, and high frequency bands for broadcast-quality mastering."
    ),
    example_prompt="Apply gentle multiband compression with 3 bands for mastering.",
)


def _build_pan(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for stereo pan effect.

    Args:
        parameters: Effect parameters with required 'position' key in [-1.0, 1.0].

    Returns:
        FFmpeg pan or aeval filter string.
    """
    position = float(parameters.get("position", 0.0))
    builder = PanBuilder(position)
    if "automation" in parameters:
        builder = builder.with_automation(parameters["automation"])
    return str(builder.build())


def _pan_preview() -> str:
    """Generate a filter preview for pan with default parameters."""
    return str(PanBuilder(0.5).build())


PAN = EffectDefinition(
    name="pan",
    description="Position a mono source in the stereo field with optional time-varying automation.",
    parameter_schema={
        "type": "object",
        "properties": {
            "position": {
                "type": "number",
                "minimum": -1.0,
                "maximum": 1.0,
                "description": "Stereo position: -1.0 = full left, 0.0 = center, 1.0 = full right.",
            },
        },
        "required": ["position"],
    },
    ai_hints={
        "position": (
            "Stereo position in [-1.0, 1.0]. "
            "-1.0 = hard left, 0.0 = center, 1.0 = hard right. "
            "Use fractional values for subtle positioning (e.g., 0.3 for slightly right)."
        ),
    },
    preview_fn=_pan_preview,
    build_fn=_build_pan,
    ai_summary=(
        "Position a mono audio source in the stereo field. "
        "Supports static positioning and gradual movement via automation envelopes."
    ),
    example_prompt="Pan the voice slightly to the right at position 0.3.",
    automatable=frozenset({"position"}),
    automation_filter_template="aeval=exprs=max(0\\,1-({expr}))*c0|max(0\\,1+({expr}))*c1:eval=frame",
)


_IR_NAMES = ("hall_small", "room_medium", "plate")


def _resolve_ir_path(ir_name: str) -> Path:
    """Resolve an IR name to its bundled WAV file path."""
    try:
        ref = importlib.resources.files("stoat_ferret") / "assets" / "reverb-irs" / f"{ir_name}.wav"
        return Path(str(ref))
    except Exception:
        return Path(__file__).parent.parent / "assets" / "reverb-irs" / f"{ir_name}.wav"


def _build_convolution_reverb(parameters: dict[str, Any]) -> str:
    ir_name = str(parameters.get("ir_name", "hall_small"))
    mix = float(parameters.get("mix", 0.5))
    return str(ConvolutionReverbBuilder(ir_name, mix).build())


def _convolution_reverb_preview() -> str:
    return str(ConvolutionReverbBuilder("hall_small", 0.5).build())


CONVOLUTION_REVERB = EffectDefinition(
    name="convolution_reverb",
    description=(
        "Apply convolution reverb using a bundled impulse response. "
        "Adds natural room ambience to dry audio."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "ir_name": {
                "type": "string",
                "enum": list(_IR_NAMES),
                "description": "Name of the impulse response preset.",
            },
            "mix": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Wet/dry mix: 0.0 = dry, 1.0 = fully wet.",
            },
        },
        "required": ["ir_name", "mix"],
    },
    ai_hints={
        "ir_name": (
            "Choose from: 'hall_small' (intimate hall), "
            "'room_medium' (mid-size room), 'plate' (plate reverb)."
        ),
        "mix": ("Wet/dry mix in [0.0, 1.0]. 0.3–0.5 suits dialogue; 0.6–0.9 for ambient pads."),
    },
    preview_fn=_convolution_reverb_preview,
    build_fn=_build_convolution_reverb,
    ai_summary=(
        "Add convolution reverb to audio using a bundled impulse response preset. "
        "Supports hall, room, and plate presets with adjustable wet/dry mix."
    ),
    example_prompt="Add a small hall reverb at 40% wet to the narration track.",
)


def _reverse_preview() -> str:
    """Generate a filter preview for the reverse effect with default parameters."""
    return str(ReverseBuilder().video_filter())


def _build_reverse(parameters: dict[str, Any]) -> str:  # noqa: ARG001
    """Build FFmpeg filter string for reverse effect.

    Args:
        parameters: Effect parameters (none required for reverse).

    Returns:
        FFmpeg reverse filter string.
    """
    return str(ReverseBuilder().video_filter())


REVERSE = EffectDefinition(
    name="Reverse",
    description=(
        "Reverse a clip so frames and audio play in reverse order. "
        "Enforces a configurable maximum duration to prevent memory exhaustion "
        "(see STOAT_REVERSE_MAX_DURATION_S)."
    ),
    parameter_schema={
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    ai_hints={},
    preview_fn=_reverse_preview,
    build_fn=_build_reverse,
    ai_summary="Play a clip backwards — frames and audio are reversed.",
    example_prompt="Play this clip in reverse.",
)


def _variable_speed_preview() -> str:
    """Generate a filter preview for variable_speed with default 2-segment parameters."""
    segments = [SpeedSegment(0, 30, 2.0), SpeedSegment(30, 60, 0.5)]
    return VariableSpeedBuilder(segments).build_filter_graph()


def _build_variable_speed(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter graph string for variable_speed effect.

    Args:
        parameters: Effect parameters with required 'segments' key — a list of
            dicts each with 'start_frame', 'end_frame', and 'speed_factor' fields.

    Returns:
        FFmpeg filter graph string using segmented concat with trim+setpts and atempo.
    """
    raw_segments = parameters.get("segments", [])
    segments = [
        SpeedSegment(
            int(seg["start_frame"]),
            int(seg["end_frame"]),
            float(seg["speed_factor"]),
        )
        for seg in raw_segments
    ]
    return VariableSpeedBuilder(segments).build_filter_graph()


VARIABLE_SPEED = EffectDefinition(
    name="Variable Speed",
    description=(
        "Apply a non-constant speed curve to a clip using segmented concat. "
        "Each segment defines a frame range and speed factor, allowing ramp "
        "effects (slow-motion, fast-forward) within a single clip."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "segments": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["start_frame", "end_frame", "speed_factor"],
                    "properties": {
                        "start_frame": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "First frame of the segment (inclusive).",
                        },
                        "end_frame": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Last frame of the segment (exclusive).",
                        },
                        "speed_factor": {
                            "type": "number",
                            "exclusiveMinimum": 0,
                            "maximum": 100.0,
                            "description": (
                                "Speed multiplier for this segment (0 exclusive – 100 inclusive). "
                                "Values < 1 slow down; values > 1 speed up."
                            ),
                        },
                    },
                    "additionalProperties": False,
                },
                "description": "Array of speed segments. Minimum 1 segment required.",
            },
        },
        "required": ["segments"],
    },
    ai_hints={
        "segments": (
            "List of speed segments. Each needs start_frame (int ≥ 0), end_frame (int > 0), "
            "and speed_factor (0 < x ≤ 100). Example: [{start_frame:0, end_frame:30, "
            "speed_factor:2.0}, {start_frame:30, end_frame:60, speed_factor:0.5}]."
        ),
    },
    preview_fn=_variable_speed_preview,
    build_fn=_build_variable_speed,
    ai_summary=(
        "Apply a variable speed curve to a clip using segmented constant-speed ranges, "
        "enabling smooth slow-motion and ramp effects within a single clip."
    ),
    example_prompt="Slow down the middle section of this clip to 0.5x speed for emphasis.",
)


def _framerate_convert_preview() -> str:
    """Generate a filter preview for framerate_convert with default parameters."""
    return str(FramerateConvertBuilder(30.0, FramerateMode.Duplicate).build())


def _build_framerate_convert(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for framerate_convert effect.

    Args:
        parameters: Effect parameters with required 'target_fps' and 'mode' keys.

    Returns:
        FFmpeg minterpolate or framerate filter string.
    """
    target_fps = float(parameters.get("target_fps", 30.0))
    mode_str = str(parameters.get("mode", "duplicate"))
    mode = FramerateMode.from_str(mode_str)
    return str(FramerateConvertBuilder(target_fps, mode).build())


FRAMERATE_CONVERT = EffectDefinition(
    name="Framerate Convert",
    description=(
        "Convert a clip to a target frame rate using duplicate, blend, or optical-flow "
        "interpolation. Duplicate is fastest; blend uses minterpolate frame-blending; "
        "optical_flow uses motion-compensated interpolation (requires libopencv FFmpeg build)."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "target_fps": {
                "type": "number",
                "minimum": 0.01,
                "default": 30.0,
                "description": "Target frame rate in frames per second (must be > 0).",
            },
            "mode": {
                "type": "string",
                "enum": ["duplicate", "blend", "optical_flow"],
                "default": "duplicate",
                "description": (
                    "Interpolation mode: 'duplicate' (framerate filter, fastest), "
                    "'blend' (minterpolate frame-blend), or "
                    "'optical_flow' (minterpolate mci, requires libopencv)."
                ),
            },
        },
        "required": ["target_fps", "mode"],
        "additionalProperties": False,
    },
    ai_hints={
        "target_fps": (
            "Target frame rate in fps. Common values: 24 (cinema), 30 (NTSC), 60 (smooth). "
            "Must be > 0. Fractional rates like 23.976 are supported."
        ),
        "mode": (
            "Use 'duplicate' for simple frame copying (no quality loss, fastest). "
            "Use 'blend' for smooth slow-motion or up-conversion with frame blending. "
            "Use 'optical_flow' for highest quality but requires --enable-libopencv FFmpeg build."
        ),
    },
    preview_fn=_framerate_convert_preview,
    build_fn=_build_framerate_convert,
    ai_summary=(
        "Convert a clip to a target frame rate using duplicate, blend, or optical-flow "
        "interpolation for smooth motion or simple frame-rate normalization."
    ),
    example_prompt="Convert this clip to 60fps using frame-blend interpolation.",
)


def _freeze_frame_preview() -> str:
    """Generate a filter preview for freeze_frame with default parameters."""
    return str(FreezeFrameBuilder(0, 2.0).build())


def _build_freeze_frame(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for freeze_frame effect."""
    frame_number = int(parameters.get("frame_number", 0))
    duration_s = float(parameters.get("duration_s", 1.0))
    return str(FreezeFrameBuilder(frame_number, duration_s).build())


FREEZE_FRAME = EffectDefinition(
    name="Freeze Frame",
    description=(
        "Hold a chosen frame for a configured duration, extending the clip. "
        "Uses FFmpeg freezeframes+tpad filters. Requires FFmpeg 4.0+. "
        "For a hold in the middle of the output timeline, use split (BL-445) + freeze composition."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "frame_number": {
                "type": "integer",
                "minimum": 0,
                "description": (
                    "0-indexed frame to freeze. Must be within the clip duration in frames."
                ),
            },
            "duration_s": {
                "type": "number",
                "minimum": 0.01,
                "default": 1.0,
                "description": "Duration to hold the frozen frame in seconds (must be > 0).",
            },
        },
        "required": ["frame_number", "duration_s"],
        "additionalProperties": False,
    },
    ai_hints={
        "frame_number": "0-indexed frame to freeze. Frame 0 is the first frame of the clip.",
        "duration_s": "Hold duration in seconds. Must be > 0. Example: 2.5 holds for 2.5 seconds.",
    },
    preview_fn=_freeze_frame_preview,
    build_fn=_build_freeze_frame,
    ai_summary="Hold a chosen frame for a configured duration, extending the clip by that amount.",
    example_prompt="Freeze frame 30 for 2 seconds to create an emphasis hold.",
)


def _blur_preview() -> str:
    """Generate a filter preview for blur with default parameters."""
    return str(BlurBuilder(2.0, "gaussian").build())


def _build_blur(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for blur effect.

    Args:
        parameters: Effect parameters with required 'sigma' and optional 'blur_type'.

    Returns:
        FFmpeg gblur or dblur filter string.
    """
    sigma = float(parameters.get("sigma", 2.0))
    blur_type = str(parameters.get("blur_type", "gaussian"))
    builder = BlurBuilder(sigma, blur_type)
    if "automation" in parameters:
        builder = builder.with_automation(parameters["automation"])
    return str(builder.build())


BLUR = EffectDefinition(
    name="Blur",
    description=(
        "Apply gaussian or directional blur to a video clip. "
        "Blur radius accepts an automation envelope for keyframable softness (slow defocus)."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "sigma": {
                "type": "number",
                "minimum": 0.01,
                "default": 2.0,
                "description": "Blur radius (must be > 0).",
            },
            "blur_type": {
                "type": "string",
                "enum": ["gaussian", "directional"],
                "default": "gaussian",
                "description": "Filter type: gaussian (gblur) or directional (dblur).",
            },
        },
        "required": ["sigma"],
        "additionalProperties": False,
    },
    ai_hints={
        "sigma": "Blur radius in pixels (> 0). Range 1–20 for typical use; higher = more blur.",
        "blur_type": "Use 'gaussian' for soft defocus; 'directional' for motion-blur style.",
    },
    preview_fn=_blur_preview,
    build_fn=_build_blur,
    ai_summary="Apply gaussian or directional blur to a clip with optional keyframable radius.",
    example_prompt="Add a soft gaussian blur with radius 3 to this clip.",
    automatable=frozenset({"sigma"}),
    automation_filter_template="gblur=sigma='{expr}':eval=frame",
    value_kind_per_option={"sigma": "numeric"},
)


def _sharpen_preview() -> str:
    """Generate a filter preview for sharpen with default parameters."""
    return str(SharpenBuilder(1.0).build())


def _build_sharpen(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for sharpen effect.

    Args:
        parameters: Effect parameters with required 'amount'.

    Returns:
        FFmpeg unsharp filter string.
    """
    amount = float(parameters.get("amount", 1.0))
    return str(SharpenBuilder(amount).build())


SHARPEN = EffectDefinition(
    name="Sharpen",
    description="Apply unsharp masking to sharpen a video clip.",
    parameter_schema={
        "type": "object",
        "properties": {
            "amount": {
                "type": "number",
                "minimum": 0.01,
                "default": 1.0,
                "description": "Sharpening strength (must be > 0). Typical range 0.5–3.0.",
            },
        },
        "required": ["amount"],
        "additionalProperties": False,
    },
    ai_hints={
        "amount": (
            "Sharpening amount (> 0). 1.0 = moderate sharpening; "
            "values > 2.0 produce a crisper, more aggressive result."
        ),
    },
    preview_fn=_sharpen_preview,
    build_fn=_build_sharpen,
    ai_summary="Apply unsharp masking to increase perceived sharpness of a video clip.",
    example_prompt="Sharpen this clip to make the details crisper.",
)


def _opacity_preview() -> str:
    """Generate a filter preview for opacity with default parameters."""
    return str(OpacityBuilder(1.0).build())


def _build_opacity(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for opacity effect.

    Args:
        parameters: Effect parameters with required 'opacity' key.

    Returns:
        FFmpeg format=rgba,colorchannelmixer filter string.
    """
    opacity = float(parameters.get("opacity", 1.0))
    builder = OpacityBuilder(opacity)
    if "automation" in parameters:
        builder = builder.with_automation(parameters["automation"])
    return str(builder.build())


OPACITY_EFFECT = EffectDefinition(
    name="Opacity",
    description=(
        "Adjust the opacity (alpha channel) of a video clip. "
        "Supports automation envelopes for keyframed crossfades."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "opacity": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 1.0,
                "description": "Opacity in [0.0, 1.0]. 0.0 = transparent, 1.0 = opaque.",
            },
        },
        "required": ["opacity"],
        "additionalProperties": False,
    },
    ai_hints={
        "opacity": (
            "Opacity in [0.0, 1.0]. 0.0 = fully transparent, 1.0 = fully opaque. "
            "Use automation for smooth crossfades."
        ),
    },
    preview_fn=_opacity_preview,
    build_fn=_build_opacity,
    ai_summary="Adjust clip opacity (alpha) with optional keyframed crossfade automation.",
    example_prompt="Fade this clip from transparent to fully opaque over 2 seconds.",
    automatable=frozenset({"opacity"}),
    automation_filter_template="format=rgba,colorchannelmixer=aa='{expr}':eval=frame",
    value_kind_per_option={"opacity": "numeric"},
)


def _scale_preview() -> str:
    """Generate a filter preview for scale with default parameters."""
    return str(ScaleBuilder(1.0).build())


def _build_scale(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for scale effect.

    Args:
        parameters: Effect parameters with required 'scale' key.

    Returns:
        FFmpeg scale filter string with trunc rounding.
    """
    scale = float(parameters.get("scale", 1.0))
    builder = ScaleBuilder(scale)
    if "automation" in parameters:
        builder = builder.with_automation(parameters["automation"])
    return str(builder.build())


SCALE_EFFECT = EffectDefinition(
    name="Scale",
    description=(
        "Scale a video clip by a multiplier with even-dimension rounding. "
        "Supports automation envelopes for slow-zoom effects."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "scale": {
                "type": "number",
                "minimum": 0.0,
                "default": 1.0,
                "description": "Scale factor (must be > 0). 1.0 = original size, 2.0 = double.",
            },
        },
        "required": ["scale"],
        "additionalProperties": False,
    },
    ai_hints={
        "scale": (
            "Scale factor > 0. 1.0 = original, 0.5 = half size, 2.0 = double. "
            "Use automation for slow-zoom (Ken Burns) effects."
        ),
    },
    preview_fn=_scale_preview,
    build_fn=_build_scale,
    ai_summary="Scale a clip by a multiplier; supports keyframed slow-zoom automation.",
    example_prompt="Apply a slow zoom from 1.0 to 1.2 scale over 5 seconds.",
    automatable=frozenset({"scale"}),
    automation_filter_template="scale=trunc(iw*('{expr}')/2)*2:trunc(ih*('{expr}')/2)*2:eval=frame",
    value_kind_per_option={"scale": "numeric"},
)


def _chroma_key_preview() -> str:
    """Generate a filter preview for chroma key with default parameters."""
    return str(ChromaKeyBuilder("#00FF00").build())


def _build_chroma_key(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for chroma key effect.

    Args:
        parameters: Effect parameters with required 'color' and optional 'similarity'.

    Returns:
        FFmpeg chromakey filter string.
    """
    color = str(parameters.get("color", "#00FF00"))
    similarity = parameters.get("similarity")
    builder = ChromaKeyBuilder(color, float(similarity) if similarity is not None else None)
    return str(builder.build())


CHROMA_KEY_EFFECT = EffectDefinition(
    name="Chroma Key",
    description=(
        "Remove a background colour using chroma keying (green/blue screen). "
        "Accepts a hex colour (#RRGGBB) or CSS named colour."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "color": {
                "type": "string",
                "default": "#00FF00",
                "description": "Key colour as #RRGGBB hex or CSS named colour (e.g. 'green').",
            },
            "similarity": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 0.1,
                "description": "Similarity threshold in [0.0, 1.0]. Higher = removes more colours.",
            },
        },
        "required": ["color"],
        "additionalProperties": False,
    },
    ai_hints={
        "color": "Key colour as '#RRGGBB' hex (e.g. '#00FF00') or named CSS colour (e.g. 'green').",
        "similarity": "Tolerance [0.0, 1.0]. Start at 0.1; increase if fringing remains.",
    },
    preview_fn=_chroma_key_preview,
    build_fn=_build_chroma_key,
    ai_summary="Remove a green/blue-screen background using FFmpeg chromakey.",
    example_prompt="Key out the green screen background on this clip.",
)


def _color_key_preview() -> str:
    """Generate a filter preview for color key with default parameters."""
    return str(ColorKeyBuilder("#FFFFFF").build())


def _build_color_key(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for color key effect.

    Args:
        parameters: Effect parameters with required 'color' and optional 'similarity'.

    Returns:
        FFmpeg colorkey filter string.
    """
    color = str(parameters.get("color", "#FFFFFF"))
    similarity = parameters.get("similarity")
    builder = ColorKeyBuilder(color, float(similarity) if similarity is not None else None)
    return str(builder.build())


COLOR_KEY_EFFECT = EffectDefinition(
    name="Color Key",
    description=(
        "Remove a flat-colour background using colour keying. "
        "Suitable for solid backgrounds such as white or black."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "color": {
                "type": "string",
                "default": "#FFFFFF",
                "description": "Key colour as #RRGGBB hex or CSS named colour (e.g. 'white').",
            },
            "similarity": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 0.1,
                "description": "Similarity threshold in [0.0, 1.0]. Higher = removes more colours.",
            },
        },
        "required": ["color"],
        "additionalProperties": False,
    },
    ai_hints={
        "color": "Key colour as '#RRGGBB' hex (e.g. '#FFFFFF') or named CSS colour (e.g. 'white').",
        "similarity": "Tolerance [0.0, 1.0]. Start at 0.1; increase if edges remain.",
    },
    preview_fn=_color_key_preview,
    build_fn=_build_color_key,
    ai_summary="Remove a flat-colour background (e.g. white or black) using FFmpeg colorkey.",
    example_prompt="Remove the white background from this clip using colour keying.",
)


_LUT_PRESET_NAMES = ("calming_teal", "warm_fade", "identity")


def _resolve_lut_path(preset_name: str) -> Path:
    """Resolve a LUT preset name to its bundled .cube file path."""
    try:
        ref = importlib.resources.files("stoat_ferret") / "assets" / "luts" / f"{preset_name}.cube"
        return Path(str(ref))
    except Exception:
        return Path(__file__).parent.parent / "assets" / "luts" / f"{preset_name}.cube"


def _color_lut_preview() -> str:
    lut_path = _resolve_lut_path("identity")
    return f"lut3d=file={str(lut_path).replace(chr(92), '/')}"


def _build_color_lut(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for color LUT effect.

    Args:
        parameters: Effect parameters with required 'preset'.

    Returns:
        FFmpeg lut3d filter string with resolved bundled asset path.
    """
    preset = str(parameters.get("preset", "identity"))
    builder = ColorLutBuilder(preset)
    lut_path = _resolve_lut_path(builder.preset_name())
    return f"lut3d=file={str(lut_path).replace(chr(92), '/')}"


COLOR_LUT = EffectDefinition(
    name="Color LUT",
    description="Apply a 3D color look-up table (LUT) to grade a video clip.",
    parameter_schema={
        "type": "object",
        "properties": {
            "preset": {
                "type": "string",
                "enum": list(_LUT_PRESET_NAMES),
                "description": "Bundled LUT preset name.",
            },
        },
        "required": ["preset"],
        "additionalProperties": False,
    },
    ai_hints={
        "preset": (
            "Choose from: 'calming_teal' (cool, cyan-shifted look), "
            "'warm_fade' (lifted shadows with warm highlights), "
            "'identity' (passthrough, no color change)."
        ),
    },
    preview_fn=_color_lut_preview,
    build_fn=_build_color_lut,
    ai_summary="Apply a bundled 3D color LUT preset to grade the video clip's look.",
    example_prompt="Apply a calming teal color grade to this clip.",
)


def _lens_distort_preview() -> str:
    """Generate a filter preview for lens_distort with default parameters."""
    return str(LensDistortBuilder(0.0, 0.0).build())


def _build_lens_distort(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for lens_distort effect.

    Args:
        parameters: Effect parameters with required 'k1' and 'k2' keys.

    Returns:
        FFmpeg lenscorrection filter string.
    """
    k1 = float(parameters.get("k1", 0.0))
    k2 = float(parameters.get("k2", 0.0))
    return str(LensDistortBuilder(k1, k2).build())


LENS_DISTORT_EFFECT = EffectDefinition(
    name="Lens Distort",
    description=(
        "Apply barrel or pincushion lens distortion to a video clip "
        "using FFmpeg lenscorrection. Positive k values produce barrel distortion; "
        "negative values produce pincushion distortion."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "k1": {
                "type": "number",
                "minimum": -1.0,
                "maximum": 1.0,
                "default": 0.0,
                "description": "Radial distortion coefficient for x-axis. Range [-1.0, 1.0].",
            },
            "k2": {
                "type": "number",
                "minimum": -1.0,
                "maximum": 1.0,
                "default": 0.0,
                "description": "Radial distortion coefficient for y-axis. Range [-1.0, 1.0].",
            },
        },
        "required": ["k1", "k2"],
        "additionalProperties": False,
    },
    ai_hints={
        "k1": (
            "Radial distortion for x-axis in [-1.0, 1.0]. "
            "Positive = barrel (edges bow outward); negative = pincushion (edges bow inward). "
            "Values near 0 produce subtle corrections; ±0.5 produce strong distortion."
        ),
        "k2": (
            "Radial distortion for y-axis in [-1.0, 1.0]. "
            "Typically set to the same value as k1 for symmetric distortion. "
            "Use different values for asymmetric lens effects."
        ),
    },
    preview_fn=_lens_distort_preview,
    build_fn=_build_lens_distort,
    ai_summary=(
        "Apply barrel or pincushion lens distortion to a clip using FFmpeg lenscorrection."
    ),
    example_prompt="Add barrel lens distortion with k1=0.5, k2=0.5 to this clip.",
)


def _chromatic_aberration_preview() -> str:
    """Generate a filter preview for chromatic_aberration with default parameters."""
    return str(ChromaticAberrationBuilder(5, 0, 0, 0, -5, 0).build())


def _build_chromatic_aberration(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for chromatic_aberration effect.

    Args:
        parameters: Effect parameters with optional rx/ry/gx/gy/bx/by shift values.

    Returns:
        FFmpeg rgbashift filter string.
    """
    rx = int(parameters.get("rx", 5))
    ry = int(parameters.get("ry", 0))
    gx = int(parameters.get("gx", 0))
    gy = int(parameters.get("gy", 0))
    bx = int(parameters.get("bx", -5))
    by = int(parameters.get("by", 0))
    return str(ChromaticAberrationBuilder(rx, ry, gx, gy, bx, by).build())


CHROMATIC_ABERRATION_EFFECT = EffectDefinition(
    name="Chromatic Aberration",
    description=(
        "Apply configurable chromatic aberration (RGB channel shift) to a video clip "
        "using FFmpeg rgbashift. Shifts each RGB channel independently by pixel offsets."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "rx": {
                "type": "integer",
                "minimum": -255,
                "maximum": 255,
                "default": 5,
                "description": "Red channel horizontal shift in [-255, 255].",
            },
            "ry": {
                "type": "integer",
                "minimum": -255,
                "maximum": 255,
                "default": 0,
                "description": "Red channel vertical shift in [-255, 255].",
            },
            "gx": {
                "type": "integer",
                "minimum": -255,
                "maximum": 255,
                "default": 0,
                "description": "Green channel horizontal shift in [-255, 255].",
            },
            "gy": {
                "type": "integer",
                "minimum": -255,
                "maximum": 255,
                "default": 0,
                "description": "Green channel vertical shift in [-255, 255].",
            },
            "bx": {
                "type": "integer",
                "minimum": -255,
                "maximum": 255,
                "default": -5,
                "description": "Blue channel horizontal shift in [-255, 255].",
            },
            "by": {
                "type": "integer",
                "minimum": -255,
                "maximum": 255,
                "default": 0,
                "description": "Blue channel vertical shift in [-255, 255].",
            },
        },
        "required": [],
        "additionalProperties": False,
    },
    ai_hints={
        "rx": "Red channel horizontal shift in pixels [-255, 255]. Positive shifts right.",
        "ry": "Red channel vertical shift in pixels [-255, 255]. Positive shifts down.",
        "gx": "Green channel horizontal shift in pixels [-255, 255]. Usually kept near 0.",
        "gy": "Green channel vertical shift in pixels [-255, 255]. Usually kept near 0.",
        "bx": "Blue channel horizontal shift in pixels [-255, 255]. Opposite of rx for aberration.",
        "by": "Blue channel vertical shift in pixels [-255, 255]. Positive shifts down.",
    },
    preview_fn=_chromatic_aberration_preview,
    build_fn=_build_chromatic_aberration,
    ai_summary=(
        "Apply chromatic aberration by shifting RGB channels independently using FFmpeg rgbashift."
    ),
    example_prompt="Add chromatic aberration with red shifted right 5px and blue shifted left 5px.",
)


def _gradient_generator_preview() -> str:
    """Generate a filter preview for gradient_generator with default parameters."""
    return str(GradientGeneratorBuilder("black", "white", 5.0).build())


def _build_gradient_generator(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for gradient_generator effect.

    Args:
        parameters: Effect parameters with required 'color1', 'color2', 'duration'.

    Returns:
        FFmpeg gradients lavfi source filter string.
    """
    color1 = str(parameters.get("color1", "black"))
    color2 = str(parameters.get("color2", "white"))
    duration = float(parameters.get("duration", 5.0))
    width = parameters.get("width")
    height = parameters.get("height")
    builder = GradientGeneratorBuilder(
        color1,
        color2,
        duration,
        int(width) if width is not None else None,
        int(height) if height is not None else None,
    )
    return str(builder.build())


GRADIENT_GENERATOR = EffectDefinition(
    name="Gradient Generator",
    description=(
        "Generate a gradient source clip with two configurable colours. "
        "Uses FFmpeg gradients lavfi source; suitable for calming visual backgrounds."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "color1": {
                "type": "string",
                "default": "black",
                "description": "First gradient colour as #RRGGBB hex or CSS named colour.",
            },
            "color2": {
                "type": "string",
                "default": "white",
                "description": "Second gradient colour as #RRGGBB hex or CSS named colour.",
            },
            "duration": {
                "type": "number",
                "minimum": 0.01,
                "default": 5.0,
                "description": "Clip duration in seconds (must be > 0).",
            },
            "width": {
                "type": "integer",
                "minimum": 1,
                "default": 1920,
                "description": "Output width in pixels.",
            },
            "height": {
                "type": "integer",
                "minimum": 1,
                "default": 1080,
                "description": "Output height in pixels.",
            },
        },
        "required": ["color1", "color2", "duration"],
        "additionalProperties": False,
    },
    ai_hints={
        "color1": "Start colour as '#RRGGBB' hex (e.g. '#000080' for navy) or named CSS colour.",
        "color2": "End colour as '#RRGGBB' hex or named CSS colour (e.g. 'white').",
        "duration": "Clip duration in seconds (> 0). Use 5–30 for background loops.",
        "width": "Output width in pixels. Default 1920 for HD.",
        "height": "Output height in pixels. Default 1080 for HD.",
    },
    preview_fn=_gradient_generator_preview,
    build_fn=_build_gradient_generator,
    ai_summary=(
        "Generate a two-colour gradient source clip of configurable duration "
        "using FFmpeg gradients lavfi source."
    ),
    example_prompt="Create a 10-second gradient from navy blue to white for a calming background.",
)


def _noise_generator_preview() -> str:
    """Generate a filter preview for noise_generator with default parameters."""
    return str(NoiseGeneratorBuilder(5.0).build())


def _build_noise_generator(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for noise_generator effect.

    Args:
        parameters: Effect parameters with required 'duration' key.

    Returns:
        FFmpeg cellauto lavfi source filter string.
    """
    duration = float(parameters.get("duration", 5.0))
    width = parameters.get("width")
    height = parameters.get("height")
    builder = NoiseGeneratorBuilder(
        duration,
        int(width) if width is not None else None,
        int(height) if height is not None else None,
    )
    return str(builder.build())


NOISE_GENERATOR = EffectDefinition(
    name="Noise Generator",
    description=(
        "Generate an evolving cellular-automaton pattern source clip. "
        "Uses FFmpeg cellauto lavfi source for animated noise patterns."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "duration": {
                "type": "number",
                "minimum": 0.01,
                "default": 5.0,
                "description": "Clip duration in seconds (must be > 0).",
            },
            "width": {
                "type": "integer",
                "minimum": 1,
                "default": 1920,
                "description": "Output width in pixels.",
            },
            "height": {
                "type": "integer",
                "minimum": 1,
                "default": 1080,
                "description": "Output height in pixels.",
            },
        },
        "required": ["duration"],
        "additionalProperties": False,
    },
    ai_hints={
        "duration": "Clip duration in seconds (> 0). Use 5–30 for background loops.",
        "width": "Output width in pixels. Default 1920 for HD.",
        "height": "Output height in pixels. Default 1080 for HD.",
    },
    preview_fn=_noise_generator_preview,
    build_fn=_build_noise_generator,
    ai_summary=(
        "Generate an evolving cellular-automaton noise/pattern source clip "
        "using FFmpeg cellauto lavfi source."
    ),
    example_prompt="Create a 10-second evolving noise pattern for a background visual.",
)


def _zoompan_preview() -> str:
    """Generate a filter preview for zoompan with default parameters."""
    b = ZoompanBuilder("1.5", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)", 125, 1920, 1080, 30)
    return str(b.build())


def _build_zoompan(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for zoompan effect.

    Args:
        parameters: Effect parameters with required 'z_expr', 'x_expr', 'y_expr',
            'd', 'width', 'height', 'fps' keys.

    Returns:
        FFmpeg zoompan+fps+settb filter chain string.
    """
    z_expr = str(parameters.get("z_expr", "1.5"))
    x_expr = str(parameters.get("x_expr", "iw/2-(iw/zoom/2)"))
    y_expr = str(parameters.get("y_expr", "ih/2-(ih/zoom/2)"))
    d = int(parameters.get("d", 125))
    width = int(parameters.get("width", 1920))
    height = int(parameters.get("height", 1080))
    fps = int(parameters.get("fps", 30))
    return str(ZoompanBuilder(z_expr, x_expr, y_expr, d, width, height, fps).build())


ZOOMPAN = EffectDefinition(
    name="Zoom Pan",
    description=(
        "Fixed-canvas Ken Burns slow-zoom / pan effect. "
        "Emits a zoompan filter with a mandatory fps/settb pin chain. "
        "NOT for stream-dimension slow-zoom (see scale automation at definitions.py:2031). "
        "NOT timeline-T capable — windowed application routes through "
        "the split/trim/concat fallback."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "z_expr": {
                "type": "string",
                "default": "1.5",
                "description": "Zoom expression (e.g. '1.5' for 1.5x zoom). No apostrophes.",
            },
            "x_expr": {
                "type": "string",
                "default": "iw/2-(iw/zoom/2)",
                "description": "X-pan expression. No apostrophes.",
            },
            "y_expr": {
                "type": "string",
                "default": "ih/2-(ih/zoom/2)",
                "description": "Y-pan expression. No apostrophes.",
            },
            "d": {
                "type": "integer",
                "minimum": 1,
                "default": 125,
                "description": "Duration in frames (must be > 0).",
            },
            "width": {
                "type": "integer",
                "minimum": 1,
                "default": 1920,
                "description": "Output canvas width in pixels.",
            },
            "height": {
                "type": "integer",
                "minimum": 1,
                "default": 1080,
                "description": "Output canvas height in pixels.",
            },
            "fps": {
                "type": "integer",
                "minimum": 1,
                "default": 30,
                "description": "Output frame rate (also used in settb pin).",
            },
        },
        "required": ["z_expr", "x_expr", "y_expr", "d", "width", "height", "fps"],
        "additionalProperties": False,
    },
    ai_hints={
        "z_expr": (
            "Zoom expression (e.g. '1.5' for static 1.5x zoom, "
            "or 'if(lte(zoom,1.5),zoom+0.002,zoom)' for animated zoom). "
            "No apostrophes allowed."
        ),
        "x_expr": "X-pan expression (e.g. 'iw/2-(iw/zoom/2)' to centre-pan). No apostrophes.",
        "y_expr": "Y-pan expression (e.g. 'ih/2-(ih/zoom/2)' to centre-pan). No apostrophes.",
        "d": "Duration in frames. At 30 fps, 125 frames = ~4 seconds.",
        "width": "Canvas width in pixels. Default 1920 for HD.",
        "height": "Canvas height in pixels. Default 1080 for HD.",
        "fps": "Output frame rate. Must match the project frame rate. Default 30.",
    },
    preview_fn=_zoompan_preview,
    build_fn=_build_zoompan,
    ai_summary=(
        "Ken Burns pan/zoom effect with mandatory fps/settb pin. "
        "Fixed-canvas only — not for stream-dimension slow-zoom."
    ),
    example_prompt="Apply a slow Ken Burns zoom from 1.0x to 1.5x centred on the clip.",
    stream_kind="video",
    timeline_T_capable=False,
    requires_path_escape=False,
)


def _curves_preview() -> str:
    """Generate a filter preview for curves with default parameters."""
    return str(CurvesBuilder(preset="vintage").build())


def _build_curves(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for curves colour grading effect.

    Args:
        parameters: Effect parameters. Either 'preset' (string) or one or more of
            'master', 'red', 'green', 'blue', 'all' (KneeString values).

    Returns:
        FFmpeg curves filter string.
    """
    preset = parameters.get("preset")
    master = parameters.get("master")
    red = parameters.get("red")
    green = parameters.get("green")
    blue = parameters.get("blue")
    all_ = parameters.get("all")
    builder = CurvesBuilder(
        preset=str(preset) if preset is not None else None,
        master=str(master) if master is not None else None,
        red=str(red) if red is not None else None,
        green=str(green) if green is not None else None,
        blue=str(blue) if blue is not None else None,
        all=str(all_) if all_ is not None else None,
    )
    return str(builder.build())


CURVES = EffectDefinition(
    name="Curves",
    description=(
        "Colour grading using FFmpeg curves filter. "
        "Supports preset-based grading (vintage, cross_process, darker, etc.) "
        "or per-channel knee-string grading (red/green/blue/master/all channels). "
        "The two modes are mutually exclusive. Timeline-T capable."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "preset": {
                "type": "string",
                "enum": [
                    "none",
                    "color_negative",
                    "cross_process",
                    "darker",
                    "increase_contrast",
                    "lighter",
                    "linear_contrast",
                    "medium_contrast",
                    "negative",
                    "strong_contrast",
                    "vintage",
                ],
                "description": "Named colour curves preset.",
            },
            "master": {
                "type": "string",
                "description": "Master channel knee string (e.g. '0/0 0.5/0.4 1/1').",
            },
            "red": {
                "type": "string",
                "description": "Red channel knee string.",
            },
            "green": {
                "type": "string",
                "description": "Green channel knee string.",
            },
            "blue": {
                "type": "string",
                "description": "Blue channel knee string.",
            },
            "all": {
                "type": "string",
                "description": "All-channels knee string.",
            },
        },
        "required": [],
        "additionalProperties": False,
    },
    ai_hints={
        "preset": (
            "Named preset: none, color_negative, cross_process, darker, increase_contrast, "
            "lighter, linear_contrast, medium_contrast, negative, strong_contrast, vintage. "
            "Cannot be combined with per-channel knee strings."
        ),
        "red": "Red channel knee string e.g. '0/0 0.5/0.4 1/1'. Pairs are x/y with monotonic x.",
        "green": "Green channel knee string e.g. '0/0 0.5/0.5 1/1'.",
        "blue": "Blue channel knee string e.g. '0/0 0.5/0.6 1/1'.",
        "master": "Master (all-channel) knee string.",
        "all": "All-channels knee string (alternative to per-channel fields).",
    },
    preview_fn=_curves_preview,
    build_fn=_build_curves,
    ai_summary=(
        "Colour grading via FFmpeg curves: preset-based (vintage, cross_process, etc.) "
        "or per-channel knee-string grading."
    ),
    example_prompt="Apply a vintage colour grade to this clip.",
    stream_kind="video",
    timeline_T_capable=True,
    requires_path_escape=False,
)


def _vignette_preview() -> str:
    """Generate a filter preview for vignette with default parameters."""
    return str(VignetteBuilder(position="centre").build())


def _build_vignette(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for vignette corner-darkening effect.

    Args:
        parameters: Effect parameters including position, x_offset, y_offset,
            angle, mode, and eval_mode.

    Returns:
        FFmpeg vignette filter string.
    """
    position = parameters.get("position", "centre")
    x_offset = int(parameters.get("x_offset", 0))
    y_offset = int(parameters.get("y_offset", 0))
    angle = float(parameters.get("angle", 0.628))
    mode = str(parameters.get("mode", "forward"))
    eval_mode = str(parameters.get("eval_mode", "init"))
    builder = VignetteBuilder(
        position=str(position),
        x_offset=x_offset,
        y_offset=y_offset,
        angle=angle,
        mode=mode,
        eval_mode=eval_mode,
    )
    return str(builder.build())


VIGNETTE = EffectDefinition(
    name="Vignette",
    description=(
        "Cinematic corner-darkening effect using FFmpeg vignette filter. "
        "Accepts a position enum (centre, top_left, top_right, bottom_left, bottom_right) "
        "plus numeric x_offset/y_offset. Timeline-T capable — windowed application supported."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "position": {
                "type": "string",
                "enum": ["centre", "top_left", "top_right", "bottom_left", "bottom_right"],
                "description": "Vignette centre position on the frame.",
            },
            "x_offset": {
                "type": "integer",
                "description": "Integer pixel offset added to the resolved x0 coordinate.",
            },
            "y_offset": {
                "type": "integer",
                "description": "Integer pixel offset added to the resolved y0 coordinate.",
            },
            "angle": {
                "type": "number",
                "description": "Vignette angle in radians; range [0, PI/2]. Default PI/5 (≈0.628).",
            },
            "mode": {
                "type": "string",
                "enum": ["forward", "backward"],
                "description": "forward darkens corners; backward lightens corners.",
            },
            "eval_mode": {
                "type": "string",
                "enum": ["init", "frame"],
                "description": "init evaluates once at stream start; frame re-evaluates per frame.",
            },
        },
        "required": ["position"],
        "additionalProperties": False,
    },
    ai_hints={
        "position": (
            "Where to centre the vignette: centre, top_left, top_right, bottom_left, bottom_right."
        ),
        "x_offset": "Integer pixel offset from the resolved x position.",
        "y_offset": "Integer pixel offset from the resolved y position.",
        "angle": "Vignette angle in radians [0, PI/2]. Larger = wider dark border.",
        "mode": "forward (default) darkens corners; backward inverts to lighten corners.",
        "eval_mode": "init (default) or frame. Use frame for per-frame angle animation.",
    },
    preview_fn=_vignette_preview,
    build_fn=_build_vignette,
    ai_summary=(
        "Cinematic corner-darkening vignette via FFmpeg vignette filter. "
        "Position enum surface; AC-1 raw x0/y0 expressions deferred to a future version."
    ),
    example_prompt="Add a cinematic vignette effect centred on the frame.",
    stream_kind="video",
    timeline_T_capable=True,
    requires_path_escape=False,
)


def _hue_rotation_preview() -> str:
    """Generate a filter preview for hue rotation with a default expression."""
    from stoat_ferret_core import HueRotationBuilder

    return str(HueRotationBuilder("2*PI*t/3").build())


def _build_hue_rotation(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for hue rotation / colour cycling effect.

    Args:
        parameters: Effect parameters including h_expr.

    Returns:
        FFmpeg hue filter string.
    """
    from stoat_ferret_core import HueRotationBuilder

    h_expr = str(parameters.get("h_expr", "2*PI*t/3"))
    return str(HueRotationBuilder(h_expr).build())


HUE_ROTATION = EffectDefinition(
    name="Hue Rotation",
    description=(
        "Colour cycling / hue rotation via FFmpeg hue filter. "
        "Accepts an FFmpeg time expression for H= (e.g. '2*PI*t/3'). "
        "Comma-bearing expressions are supported via single-quote wrap (no \\, escape). "
        "Timeline-T capable — windowed application supported."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "h_expr": {
                "type": "string",
                "description": (
                    "FFmpeg time expression for the H= hue-angle option "
                    "(e.g. '2*PI*t/3'). Must not contain single-quote characters."
                ),
            },
        },
        "required": ["h_expr"],
        "additionalProperties": False,
    },
    ai_hints={
        "h_expr": (
            "FFmpeg expression for hue angle in radians "
            "(e.g. '2*PI*t/3' for a full colour cycle every 3 seconds). "
            "Commas allowed inside expressions; single quotes not permitted."
        ),
    },
    preview_fn=_hue_rotation_preview,
    build_fn=_build_hue_rotation,
    ai_summary=(
        "Hue rotation / colour cycling via FFmpeg hue filter. "
        "Single-quote wrap policy; no BL-502 comma-escape rules."
    ),
    example_prompt="Add a hue rotation effect that cycles through colours every 3 seconds.",
    stream_kind="video",
    timeline_T_capable=True,
    requires_path_escape=False,
)


def _subtitle_script_preview() -> str:
    """Generate a filter preview for subtitle_script with default parameters."""
    entries = [ScriptEntry(0.0, 2.0, "Sample caption")]
    spec = SubtitleScriptSpec(entries=entries)
    return SubtitleScriptBuilder.build(spec)


def _build_subtitle_script(parameters: dict[str, Any]) -> str:
    """Build FFmpeg drawtext chain for timed subtitle captions.

    Args:
        parameters: Effect parameters with required 'entries' key.

    Returns:
        Comma-separated drawtext filter chain with enable= expressions.
    """
    raw_entries = parameters.get("entries", [])
    entries = [
        ScriptEntry(
            float(e["start_s"]),
            float(e["end_s"]),
            str(e["text"]),
        )
        for e in raw_entries
    ]
    spec = SubtitleScriptSpec(
        entries=entries,
        position=str(parameters.get("position", "bottom")),
        font_size=int(parameters.get("font_size", 24)),
        font_color=str(parameters.get("font_color", "white")),
        font_file=parameters.get("font_file") or None,
    )
    return SubtitleScriptBuilder.build(spec)


SUBTITLE_SCRIPT = EffectDefinition(
    name="Subtitle Script",
    description=(
        "Add timed captions to a video from a list of (start_s, end_s, text) entries. "
        "Each entry emits a drawtext filter with enable='between(t,s,e)' for time-windowed "
        "display. Style is uniform across all captions (position, font_size, font_color)."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "entries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "start_s": {
                            "type": "number",
                            "description": "Caption start time in seconds.",
                        },
                        "end_s": {
                            "type": "number",
                            "description": "Caption end time in seconds.",
                        },
                        "text": {"type": "string", "description": "Caption text."},
                    },
                    "required": ["start_s", "end_s", "text"],
                    "additionalProperties": False,
                },
                "minItems": 1,
                "description": "List of timed caption entries.",
            },
            "position": {
                "type": "string",
                "enum": ["bottom", "top", "center"],
                "default": "bottom",
                "description": "Screen position for all captions.",
            },
            "font_size": {
                "type": "integer",
                "minimum": 6,
                "maximum": 256,
                "default": 24,
                "description": "Font size in pixels, applied to all captions.",
            },
            "font_color": {
                "type": "string",
                "default": "white",
                "description": "Font color name or hex value, applied to all captions.",
            },
            "font_file": {
                "type": "string",
                "description": "Absolute path to a font file. Omit to use fontconfig fallback.",
            },
        },
        "required": ["entries"],
        "additionalProperties": False,
    },
    ai_hints={
        "entries": (
            "List of caption entries. Each entry needs start_s (float), "
            "end_s (float), and text (str). "
            "Entries can overlap in time — each has its own enable= expression."
        ),
        "position": (
            "'bottom' (default) places captions near the lower edge; "
            "'top' near upper edge; 'center' in the middle."
        ),
        "font_size": "Caption font size in pixels. Typical range 18-48 for video.",
        "font_color": (
            "Color name (white, yellow) or hex (#FFFFFF). White is most readable on video."
        ),
        "font_file": (
            "Optional: absolute path to a .ttf/.otf font file. Leave unset for system fontconfig."
        ),
    },
    preview_fn=_subtitle_script_preview,
    build_fn=_build_subtitle_script,
    ai_summary=(
        "Burn timed caption text onto a video clip using a list of (start_s, end_s, text) entries. "
        "Ideal for affirmation, wellness, and subtitle-style overlays."
    ),
    example_prompt="Add captions: 'Breathe in' at 0-3s, 'Hold' at 3-6s, 'Release' at 6-9s.",
    stream_kind="video",
    timeline_T_capable=False,
    requires_path_escape=True,
    value_kind_per_option={"font_file": "path"},
)


def _burned_subtitle_preview() -> str:
    """Generate a filter preview for burned_subtitle with a default SRT path."""
    spec = BurnedSubtitleSpec(source_path="/path/to/subtitle.srt")
    return BurnedSubtitleBuilder.build(spec)


def _build_burned_subtitle(parameters: dict[str, Any]) -> str:
    """Build FFmpeg filter string for SRT/ASS subtitle burn-in.

    Args:
        parameters: Effect parameters with 'source_path' and/or 'inline_text',
                    and optional 'force_style' dict.
    """
    spec = BurnedSubtitleSpec(
        source_path=parameters.get("source_path") or None,
        inline_text=parameters.get("inline_text") or None,
        force_style=parameters.get("force_style") or None,
    )
    return BurnedSubtitleBuilder.build(spec)


BURNED_SUBTITLE_BUILDER = EffectDefinition(
    name="Burned Subtitle",
    description=(
        "Burn subtitle text from an SRT or ASS sidecar file directly onto the video frames. "
        "SRT files use the FFmpeg 'subtitles' filter; ASS files use the 'ass' filter. "
        "Optional force_style overrides (Fontname, Fontsize, PrimaryColour, etc.) apply "
        "to SRT only — ASS files embed styles inline."
    ),
    parameter_schema={
        "type": "object",
        "properties": {
            "source_path": {
                "type": "string",
                "description": "Absolute path to an SRT or ASS subtitle file.",
            },
            "inline_text": {
                "type": "string",
                "description": ("Alternative: pre-resolved path to a subtitle file."),
            },
            "force_style": {
                "type": "object",
                "description": (
                    "Optional KEY=VALUE style overrides for SRT rendering "
                    "(Fontname, Fontsize, PrimaryColour, Outline, etc.)."
                ),
            },
        },
        "anyOf": [
            {"required": ["source_path"]},
            {"required": ["inline_text"]},
        ],
    },
    ai_hints={
        "source_path": (
            "Absolute path to an SRT or ASS subtitle sidecar file. "
            "Format auto-detected by extension (.srt → subtitles filter, .ass → ass filter)."
        ),
        "inline_text": ("Alternative to source_path: pre-resolved path to a subtitle file."),
        "force_style": (
            "Optional SRT-only style overrides as a dict: "
            "{'Fontname': 'Arial', 'Fontsize': '32', 'PrimaryColour': '&Hffffff&'}. "
            "Ignored for ASS files (ASS styles are embedded inline)."
        ),
    },
    preview_fn=_burned_subtitle_preview,
    build_fn=_build_burned_subtitle,
    ai_summary=(
        "Burn SRT or ASS subtitle text directly onto video frames. "
        "SRT supports optional force_style overrides; ASS uses its own inline styles."
    ),
    example_prompt="Burn English subtitles from subtitles_en.srt onto the video with Fontsize=28.",
    stream_kind="video",
    timeline_T_capable=False,
    requires_path_escape=True,
    value_kind_per_option={"source_path": "path", "inline_text": "path"},
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
    registry.register("noise_reduction", NOISE_REDUCTION)
    registry.register("deesser", DEESSER)
    registry.register("deplosive", DEPLOSIVE)
    registry.register("time_stretch", TIME_STRETCH)
    registry.register("mastering_limiter", MASTERING_LIMITER)
    registry.register("loudness_normalize", LOUDNESS_NORMALIZE)
    registry.register("parametric_eq", PARAMETRIC_EQ)
    registry.register("multiband_compressor", MULTIBAND_COMPRESSOR)
    registry.register("pan", PAN)
    registry.register("convolution_reverb", CONVOLUTION_REVERB)
    registry.register("reverse", REVERSE)
    registry.register("variable_speed", VARIABLE_SPEED)
    registry.register("framerate_convert", FRAMERATE_CONVERT)
    registry.register("freeze_frame", FREEZE_FRAME)
    registry.register("blur", BLUR)
    registry.register("sharpen", SHARPEN)
    registry.register("opacity", OPACITY_EFFECT)
    registry.register("scale", SCALE_EFFECT)
    registry.register("chroma_key", CHROMA_KEY_EFFECT)
    registry.register("color_key", COLOR_KEY_EFFECT)
    registry.register("color_lut", COLOR_LUT)
    registry.register("lens_distort", LENS_DISTORT_EFFECT)
    registry.register("gradient_generator", GRADIENT_GENERATOR)
    registry.register("noise_generator", NOISE_GENERATOR)
    registry.register("chromatic_aberration", CHROMATIC_ABERRATION_EFFECT)
    registry.register("zoompan", ZOOMPAN)
    registry.register("curves", CURVES)
    registry.register("vignette", VIGNETTE)
    registry.register("hue_rotation", HUE_ROTATION)
    registry.register("subtitle_script", SUBTITLE_SCRIPT)
    registry.register("burned_subtitle", BURNED_SUBTITLE_BUILDER)
    return registry
