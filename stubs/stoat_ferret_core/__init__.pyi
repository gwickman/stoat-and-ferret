"""Type stubs for stoat_ferret_core.

This module provides type hints for the Rust-based stoat_ferret_core library.
These stubs are generated from the Rust code using pyo3-stub-gen.
"""

# Re-export all types from _core
from stoat_ferret_core._core import (
    # Clip types
    Clip as Clip,
)
from stoat_ferret_core._core import (
    ClipValidationError as ClipValidationError,
)
from stoat_ferret_core._core import (
    CommandError as CommandError,
)
from stoat_ferret_core._core import (
    Duration as Duration,
)
from stoat_ferret_core._core import (
    # FFmpeg command building
    FFmpegCommand as FFmpegCommand,
)
from stoat_ferret_core._core import (
    Filter as Filter,
)
from stoat_ferret_core._core import (
    FilterChain as FilterChain,
)
from stoat_ferret_core._core import (
    FilterGraph as FilterGraph,
)
from stoat_ferret_core._core import (
    # Timeline types
    FrameRate as FrameRate,
)
from stoat_ferret_core._core import (
    Position as Position,
)
from stoat_ferret_core._core import (
    SanitizationError as SanitizationError,
)
from stoat_ferret_core._core import (
    TimeRange as TimeRange,
)
from stoat_ferret_core._core import (
    # Exceptions
    ValidationError as ValidationError,
)
from stoat_ferret_core._core import (
    concat_filter as concat_filter,
)
from stoat_ferret_core._core import (
    # Sanitization functions
    escape_filter_text as escape_filter_text,
)
from stoat_ferret_core._core import (
    # Utility
    health_check as health_check,
)
from stoat_ferret_core._core import (
    # Filter helpers
    scale_filter as scale_filter,
)
from stoat_ferret_core._core import (
    validate_audio_codec as validate_audio_codec,
)
from stoat_ferret_core._core import (
    validate_clip as validate_clip,
)
from stoat_ferret_core._core import (
    validate_clips as validate_clips,
)
from stoat_ferret_core._core import (
    validate_path as validate_path,
)
from stoat_ferret_core._core import (
    validate_preset as validate_preset,
)
from stoat_ferret_core._core import (
    validate_video_codec as validate_video_codec,
)
from stoat_ferret_core._core import (
    validate_volume as validate_volume,
)

__all__ = [
    # Utility
    "health_check",
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
    "validate_volume",
    "validate_video_codec",
    "validate_audio_codec",
    "validate_preset",
    # Exceptions
    "ValidationError",
    "CommandError",
    "SanitizationError",
]
