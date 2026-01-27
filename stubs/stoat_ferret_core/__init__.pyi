"""Type stubs for stoat_ferret_core.

This module provides type hints for the Rust-based stoat_ferret_core library.
These stubs are generated from the Rust code using pyo3-stub-gen.
"""

# Re-export all types from _core
from stoat_ferret_core._core import (
    # Utility
    health_check as health_check,
    # Clip types
    Clip as Clip,
    ClipValidationError as ClipValidationError,
    py_validate_clip as py_validate_clip,
    py_validate_clips as py_validate_clips,
    # Timeline types
    FrameRate as FrameRate,
    Position as Position,
    Duration as Duration,
    TimeRange as TimeRange,
    # FFmpeg command building
    FFmpegCommand as FFmpegCommand,
    Filter as Filter,
    FilterChain as FilterChain,
    FilterGraph as FilterGraph,
    # Filter helpers
    scale_filter as scale_filter,
    concat_filter as concat_filter,
    # Sanitization functions
    escape_filter_text as escape_filter_text,
    validate_path as validate_path,
    validate_crf as validate_crf,
    validate_speed as validate_speed,
    validate_volume as validate_volume,
    validate_video_codec as validate_video_codec,
    validate_audio_codec as validate_audio_codec,
    validate_preset as validate_preset,
    # Exceptions
    ValidationError as ValidationError,
    CommandError as CommandError,
    SanitizationError as SanitizationError,
)

__all__ = [
    # Utility
    "health_check",
    # Clip types
    "Clip",
    "ClipValidationError",
    "py_validate_clip",
    "py_validate_clips",
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
