"""stoat_ferret_core - Rust-powered video editing primitives.

This module provides the Python interface to the stoat_ferret_core Rust library,
which handles computationally intensive operations like filter generation,
timeline math, and FFmpeg command building.

Timeline Types
--------------
- FrameRate: Frame rate representation with common presets
- Position: Frame-accurate timeline position
- Duration: Frame-accurate duration
- TimeRange: Half-open interval [start, end) with set operations

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
- validate_crf: Validate CRF quality values (0-51)
- validate_speed: Validate speed multipliers (0.25-4.0)
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
        # Exceptions
        CommandError,
        Duration,
        # FFmpeg command building
        FFmpegCommand,
        Filter,
        FilterChain,
        FilterGraph,
        # Timeline types
        FrameRate,
        Position,
        SanitizationError,
        TimeRange,
        ValidationError,
        concat_filter,
        # Sanitization functions
        escape_filter_text,
        # Utility function
        health_check,
        # Filter helper functions
        scale_filter,
        validate_audio_codec,
        validate_crf,
        validate_path,
        validate_preset,
        validate_speed,
        validate_video_codec,
        validate_volume,
    )
except ImportError:  # pragma: no cover
    # Rust extension not built - provide stubs for development/testing

    def _not_built(*args, **kwargs):  # type: ignore[no-untyped-def]
        """Stub when native module unavailable."""
        raise RuntimeError(
            "stoat_ferret_core native extension not built. "
            "Run 'maturin develop' to build the Rust component."
        )

    health_check = _not_built
    FrameRate = _not_built  # type: ignore[misc,assignment]
    Position = _not_built  # type: ignore[misc,assignment]
    Duration = _not_built  # type: ignore[misc,assignment]
    TimeRange = _not_built  # type: ignore[misc,assignment]
    FFmpegCommand = _not_built  # type: ignore[misc,assignment]
    Filter = _not_built  # type: ignore[misc,assignment]
    FilterChain = _not_built  # type: ignore[misc,assignment]
    FilterGraph = _not_built  # type: ignore[misc,assignment]
    scale_filter = _not_built
    concat_filter = _not_built
    escape_filter_text = _not_built
    validate_path = _not_built
    validate_crf = _not_built
    validate_speed = _not_built
    validate_volume = _not_built
    validate_video_codec = _not_built
    validate_audio_codec = _not_built
    validate_preset = _not_built
    ValidationError = RuntimeError  # type: ignore[misc,assignment]
    CommandError = RuntimeError  # type: ignore[misc,assignment]
    SanitizationError = RuntimeError  # type: ignore[misc,assignment]


__all__ = [
    # Utility
    "health_check",
    # Timeline types
    "FrameRate",
    "Position",
    "Duration",
    "TimeRange",
    # FFmpeg command building
    "FFmpegCommand",
    "Filter",
    "FilterChain",
    "FilterGraph",
    # Filter helpers
    "scale_filter",
    "concat_filter",
    # Sanitization functions
    "escape_filter_text",
    "validate_path",
    "validate_crf",
    "validate_speed",
    "validate_volume",
    "validate_video_codec",
    "validate_audio_codec",
    "validate_preset",
    # Exceptions
    "ValidationError",
    "CommandError",
    "SanitizationError",
]
