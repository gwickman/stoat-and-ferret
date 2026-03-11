"""stoat_ferret_core - Rust-powered video editing primitives.

This module provides the Python interface to the stoat_ferret_core Rust library,
which handles computationally intensive operations like filter generation,
timeline math, and FFmpeg command building.

Clip Types
----------
- Clip: Video clip representing a segment of a source media file
- ClipValidationError: Validation error with detailed information
- validate_clip: Validate a single clip
- validate_clips: Validate multiple clips

Timeline Types
--------------
- FrameRate: Frame rate representation with common presets
- Position: Frame-accurate timeline position
- Duration: Frame-accurate duration
- TimeRange: Half-open interval [start, end) with set operations

Speed Control
-------------
- SpeedControl: Speed adjustment builder with setpts and atempo auto-chaining

FFmpeg Command Building
-----------------------
- FFmpegCommand: Type-safe builder for FFmpeg command arguments
- Filter: Single FFmpeg filter with parameters
- FilterChain: Sequence of filters connected with commas
- FilterGraph: Multiple filter chains connected with semicolons

Sanitization Functions
----------------------
- escape_filter_text: Escape special characters in filter parameters
- validate_path: Validate file paths are safe to use
- validate_volume: Validate volume multipliers (0.0-10.0)
- validate_video_codec: Validate video codec names
- validate_audio_codec: Validate audio codec names
- validate_preset: Validate encoding preset names

Exceptions
----------
- ValidationError: Raised when input validation fails
- CommandError: Raised when FFmpeg command building fails
- SanitizationError: Raised when input sanitization fails
"""

from __future__ import annotations

try:
    from stoat_ferret_core._core import (
        AcrossfadeBuilder,
        AfadeBuilder,
        AmixBuilder,
        AudioMixSpec,
        BatchJobStatus,
        BatchProgress,
        Clip,
        ClipValidationError,
        CommandError,
        CompositionClip,
        DrawtextBuilder,
        DuckingPattern,
        Duration,
        FadeBuilder,
        FFmpegCommand,
        Filter,
        FilterChain,
        FilterGraph,
        FrameRate,
        LayoutPosition,
        LayoutPreset,
        LayoutSpec,
        Position,
        SanitizationError,
        SpeedControl,
        TimeRange,
        TrackAudioConfig,
        TransitionSpec,
        TransitionType,
        ValidationError,
        VolumeBuilder,
        XfadeBuilder,
        build_composition_graph,
        build_overlay_filter,
        build_scale_for_layout,
        calculate_batch_progress,
        calculate_composition_positions,
        calculate_timeline_duration,
        concat_filter,
        escape_filter_text,
        health_check,
        scale_filter,
        validate_audio_codec,
        validate_clip,
        validate_clips,
        validate_path,
        validate_preset,
        validate_video_codec,
        validate_volume,
    )
except ImportError:
    # Rust extension not built - provide stubs for development/testing.
    # Tested in tests/test_coverage/test_import_fallback.py

    def _not_built(*args, **kwargs):  # type: ignore[no-untyped-def]  # intentional catch-all signature
        """Stub when native module unavailable."""
        raise RuntimeError(
            "stoat_ferret_core native extension not built. "
            "Run 'maturin develop' to build the Rust component."
        )

    health_check = _not_built
    # Callable stub replacing typed classes (intentional fallback)
    BatchJobStatus = _not_built  # type: ignore[misc,assignment]
    BatchProgress = _not_built  # type: ignore[misc,assignment]
    calculate_batch_progress = _not_built
    Clip = _not_built  # type: ignore[misc,assignment]
    ClipValidationError = _not_built  # type: ignore[misc,assignment]
    validate_clip = _not_built
    validate_clips = _not_built
    FrameRate = _not_built  # type: ignore[misc,assignment]
    Position = _not_built  # type: ignore[misc,assignment]
    Duration = _not_built  # type: ignore[misc,assignment]
    TimeRange = _not_built  # type: ignore[misc,assignment]
    DrawtextBuilder = _not_built  # type: ignore[misc,assignment]
    SpeedControl = _not_built  # type: ignore[misc,assignment]
    VolumeBuilder = _not_built  # type: ignore[misc,assignment]
    AfadeBuilder = _not_built  # type: ignore[misc,assignment]
    AmixBuilder = _not_built  # type: ignore[misc,assignment]
    DuckingPattern = _not_built  # type: ignore[misc,assignment]
    TrackAudioConfig = _not_built  # type: ignore[misc,assignment]
    AudioMixSpec = _not_built  # type: ignore[misc,assignment]
    TransitionType = _not_built  # type: ignore[misc,assignment]
    FadeBuilder = _not_built  # type: ignore[misc,assignment]
    XfadeBuilder = _not_built  # type: ignore[misc,assignment]
    AcrossfadeBuilder = _not_built  # type: ignore[misc,assignment]
    FFmpegCommand = _not_built  # type: ignore[misc,assignment]
    Filter = _not_built  # type: ignore[misc,assignment]
    FilterChain = _not_built  # type: ignore[misc,assignment]
    FilterGraph = _not_built  # type: ignore[misc,assignment]
    LayoutPosition = _not_built  # type: ignore[misc,assignment]
    LayoutPreset = _not_built  # type: ignore[misc,assignment]
    LayoutSpec = _not_built  # type: ignore[misc,assignment]
    TransitionSpec = _not_built  # type: ignore[misc,assignment]
    build_composition_graph = _not_built
    build_overlay_filter = _not_built
    build_scale_for_layout = _not_built
    calculate_composition_positions = _not_built
    calculate_timeline_duration = _not_built
    CompositionClip = _not_built  # type: ignore[misc,assignment]
    scale_filter = _not_built
    concat_filter = _not_built
    escape_filter_text = _not_built
    validate_path = _not_built
    validate_volume = _not_built
    validate_video_codec = _not_built
    validate_audio_codec = _not_built
    validate_preset = _not_built
    # Aliasing exceptions to RuntimeError (intentional fallback)
    ValidationError = RuntimeError  # type: ignore[misc,assignment]
    CommandError = RuntimeError  # type: ignore[misc,assignment]
    SanitizationError = RuntimeError  # type: ignore[misc,assignment]


__all__ = [
    # Utility
    "health_check",
    # Batch progress types
    "BatchJobStatus",
    "BatchProgress",
    "calculate_batch_progress",
    # Clip types
    "Clip",
    "ClipValidationError",
    "validate_clip",
    "validate_clips",
    # Timeline types
    "FrameRate",
    "Position",
    "Duration",
    "TimeRange",
    # Drawtext builder
    "DrawtextBuilder",
    # Speed control builder
    "SpeedControl",
    # Audio mixing builders
    "VolumeBuilder",
    "AfadeBuilder",
    "AmixBuilder",
    "DuckingPattern",
    "TrackAudioConfig",
    "AudioMixSpec",
    # Transition builders
    "TransitionType",
    "FadeBuilder",
    "XfadeBuilder",
    "AcrossfadeBuilder",
    # FFmpeg command building
    "FFmpegCommand",
    "Filter",
    "FilterChain",
    "FilterGraph",
    # Layout types
    "LayoutPosition",
    "LayoutPreset",
    "LayoutSpec",
    # Composition timeline
    "CompositionClip",
    "TransitionSpec",
    "calculate_composition_positions",
    "calculate_timeline_duration",
    # Composition graph builder
    "build_composition_graph",
    # Composition functions
    "build_overlay_filter",
    "build_scale_for_layout",
    # Filter helpers
    "scale_filter",
    "concat_filter",
    # Sanitization functions
    "escape_filter_text",
    "validate_path",
    "validate_volume",
    "validate_video_codec",
    "validate_audio_codec",
    "validate_preset",
    # Exceptions
    "ValidationError",
    "CommandError",
    "SanitizationError",
]
