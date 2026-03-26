"""Database model definitions for video metadata storage."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from stoat_ferret_core import ClipValidationError as RustClipValidationError


class PreviewStatus(str, Enum):
    """Status of a preview session through its lifecycle.

    Transitions: initializing -> generating -> ready, ready -> seeking -> ready,
    any -> error, any -> expired.
    """

    INITIALIZING = "initializing"
    GENERATING = "generating"
    READY = "ready"
    SEEKING = "seeking"
    ERROR = "error"
    EXPIRED = "expired"


# Valid preview status transitions: from -> set of allowed targets
_PREVIEW_TRANSITIONS: dict[str, set[str]] = {
    "initializing": {"generating", "error", "expired"},
    "generating": {"ready", "error", "expired"},
    "ready": {"seeking", "error", "expired"},
    "seeking": {"ready", "error", "expired"},
    "error": {"expired"},
    "expired": set(),
}


def validate_preview_transition(current: str, new: str) -> None:
    """Validate that a preview status transition is allowed.

    Args:
        current: Current status value.
        new: Proposed new status value.

    Raises:
        ValueError: If the transition is not allowed.
    """
    allowed = _PREVIEW_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise ValueError(
            f"Invalid preview status transition: {current!r} -> {new!r}. "
            f"Allowed: {sorted(allowed) if allowed else 'none (terminal state)'}"
        )


class PreviewQuality(str, Enum):
    """Quality level for a preview session."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class PreviewSession:
    """Preview session metadata for HLS preview generation.

    Represents a preview session with lifecycle state management,
    HLS manifest tracking, and TTL-based expiry.

    Attributes:
        id: Unique identifier (UUID).
        project_id: FK to the project.
        status: Current lifecycle status.
        manifest_path: Path to HLS manifest file (None until ready).
        segment_count: Number of HLS segments generated.
        quality_level: Quality level of the preview.
        created_at: When the session was created.
        updated_at: When the session was last modified.
        expires_at: When the session expires.
        error_message: Error description (None on success).
    """

    id: str
    project_id: str
    status: PreviewStatus
    quality_level: PreviewQuality
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    manifest_path: str | None = None
    segment_count: int = 0
    error_message: str | None = None

    @staticmethod
    def new_id() -> str:
        """Generate a new unique ID for a preview session."""
        return str(uuid.uuid4())


class ThumbnailStripStatus(str, Enum):
    """Status of a thumbnail strip through its lifecycle.

    Transitions: pending -> generating -> ready, any -> error.
    """

    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    ERROR = "error"


@dataclass
class ThumbnailStrip:
    """Thumbnail strip sprite sheet metadata.

    Represents an NxM grid sprite sheet generated from a video using
    FFmpeg fps+scale+tile filters for timeline seek tooltips.

    Attributes:
        id: Unique identifier (UUID).
        video_id: FK to the source video.
        status: Current lifecycle status.
        file_path: Path to the sprite sheet JPEG (None until ready).
        frame_count: Number of frames in the sprite sheet.
        frame_width: Width of each frame in pixels.
        frame_height: Height of each frame in pixels.
        interval_seconds: Seconds between extracted frames.
        columns: Number of columns in the grid.
        rows: Number of rows in the grid.
        created_at: When the strip was created.
    """

    id: str
    video_id: str
    status: ThumbnailStripStatus
    created_at: datetime
    file_path: str | None = None
    frame_count: int = 0
    frame_width: int = 160
    frame_height: int = 90
    interval_seconds: float = 5.0
    columns: int = 10
    rows: int = 0

    @staticmethod
    def new_id() -> str:
        """Generate a new unique ID for a thumbnail strip."""
        return str(uuid.uuid4())


class WaveformStatus(str, Enum):
    """Status of a waveform through its lifecycle.

    Transitions: pending -> generating -> ready, any -> error.
    """

    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    ERROR = "error"


class WaveformFormat(str, Enum):
    """Output format for waveform generation."""

    PNG = "png"
    JSON = "json"


@dataclass
class Waveform:
    """Waveform metadata for audio visualization.

    Represents a waveform generated from a video's audio stream using
    FFmpeg showwavespic (PNG) or astats (JSON) filters.

    Attributes:
        id: Unique identifier (UUID).
        video_id: FK to the source video.
        format: Output format (png or json).
        status: Current lifecycle status.
        file_path: Path to the output file (None until ready).
        duration: Audio duration in seconds.
        channels: Number of audio channels.
        created_at: When the waveform was created.
    """

    id: str
    video_id: str
    format: WaveformFormat
    status: WaveformStatus
    created_at: datetime
    file_path: str | None = None
    duration: float = 0.0
    channels: int = 0

    @staticmethod
    def new_id() -> str:
        """Generate a new unique ID for a waveform."""
        return str(uuid.uuid4())


class ProxyStatus(str, Enum):
    """Status of a proxy file through its lifecycle.

    Transitions: pending -> generating -> ready, pending -> generating -> failed,
    ready -> stale.
    """

    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    STALE = "stale"


class ProxyQuality(str, Enum):
    """Quality level for a proxy file."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ProxyFile:
    """Proxy file metadata for lower-resolution editing previews.

    Represents a proxy file generated from a source video at a specific
    quality level. Each (source_video_id, quality) pair is unique.

    Attributes:
        id: Unique identifier (UUID).
        source_video_id: FK to the source video.
        quality: Quality level of the proxy.
        file_path: Absolute path to the proxy file.
        file_size_bytes: Size of the proxy file in bytes.
        status: Current lifecycle status.
        source_checksum: SHA-256 checksum of the source video.
        generated_at: When generation completed (None until ready).
        last_accessed_at: When the proxy was last accessed.
    """

    id: str
    source_video_id: str
    quality: ProxyQuality
    file_path: str
    file_size_bytes: int
    status: ProxyStatus
    source_checksum: str
    generated_at: datetime | None
    last_accessed_at: datetime

    @staticmethod
    def new_id() -> str:
        """Generate a new unique ID for a proxy file."""
        return str(uuid.uuid4())


class ClipValidationError(Exception):
    """Exception raised when clip validation fails.

    Wraps the Rust ClipValidationError data class as a Python exception.
    """

    def __init__(
        self,
        field: str,
        message: str,
        actual: str | None = None,
        expected: str | None = None,
    ) -> None:
        """Initialize the validation error.

        Args:
            field: The name of the field that failed validation.
            message: A human-readable explanation of the error.
            actual: The actual value that was provided (optional).
            expected: The expected value or constraint (optional).
        """
        self.field = field
        self.message = message
        self.actual = actual
        self.expected = expected
        super().__init__(f"{field}: {message}")

    @classmethod
    def from_rust(cls, err: RustClipValidationError) -> ClipValidationError:
        """Create from a Rust ClipValidationError.

        Args:
            err: The Rust validation error data.

        Returns:
            A Python ClipValidationError exception.
        """
        return cls(
            field=err.field,
            message=err.message,
            actual=err.actual,
            expected=err.expected,
        )


@dataclass
class Track:
    """Timeline track within a project.

    Represents a video, audio, or text track that clips are assigned to.
    Tracks define the layering order (z_index) and can be muted or locked.
    """

    id: str
    project_id: str
    track_type: str  # "video", "audio", "text"
    label: str
    z_index: int = 0
    muted: bool = False
    locked: bool = False

    @staticmethod
    def new_id() -> str:
        """Generate a new unique ID for a track."""
        return str(uuid.uuid4())


@dataclass
class Clip:
    """Video clip within a project.

    Represents a segment of a source video placed on a timeline.
    Validation is delegated to the Rust core library.
    """

    id: str
    project_id: str
    source_video_id: str
    in_point: int  # frames
    out_point: int  # frames
    timeline_position: int  # frames
    created_at: datetime
    updated_at: datetime
    effects: list[dict[str, Any]] | None = field(default=None)
    track_id: str | None = field(default=None)
    timeline_start: float | None = field(default=None)
    timeline_end: float | None = field(default=None)

    @staticmethod
    def new_id() -> str:
        """Generate a new unique ID for a clip."""
        return str(uuid.uuid4())

    def validate(self, source_path: str, source_duration_frames: int | None = None) -> None:
        """Validate clip using Rust core.

        Creates a Rust Clip and validates it. Raises ClipValidationError if invalid.

        Args:
            source_path: Path to the source video file.
            source_duration_frames: Total duration of source video in frames (optional).

        Raises:
            ClipValidationError: If clip validation fails.
        """
        from stoat_ferret_core import Clip as RustClip
        from stoat_ferret_core import Duration, Position, validate_clip

        in_pos = Position(self.in_point)
        out_pos = Position(self.out_point)
        source_dur = (
            Duration(source_duration_frames) if source_duration_frames is not None else None
        )

        rust_clip = RustClip(source_path, in_pos, out_pos, source_dur)
        errors = validate_clip(rust_clip)
        if errors:
            # Raise the first validation error wrapped as a Python exception
            raise ClipValidationError.from_rust(errors[0])


@dataclass
class Project:
    """Video editing project.

    Represents a project that organizes clips and defines output settings.
    """

    id: str
    name: str
    output_width: int
    output_height: int
    output_fps: int
    created_at: datetime
    updated_at: datetime
    transitions: list[dict[str, Any]] | None = field(default=None)
    audio_mix: dict[str, Any] | None = field(default=None)

    @staticmethod
    def new_id() -> str:
        """Generate a new unique ID for a project."""
        return str(uuid.uuid4())


@dataclass
class AuditEntry:
    """Audit log entry for tracking data modifications.

    Records changes made to entities in the database, including
    the operation type, affected entity, and any field changes.
    """

    id: str
    timestamp: datetime
    operation: str  # INSERT, UPDATE, DELETE
    entity_type: str
    entity_id: str
    changes_json: str | None = None
    context: str | None = None

    @staticmethod
    def new_id() -> str:
        """Generate a new unique ID for an audit entry."""
        return str(uuid.uuid4())


@dataclass
class Video:
    """Video metadata entity.

    Represents a video file's metadata as stored in the database.
    All fields map directly to the videos table schema.
    """

    id: str
    path: str
    filename: str
    duration_frames: int
    frame_rate_numerator: int
    frame_rate_denominator: int
    width: int
    height: int
    video_codec: str
    file_size: int
    created_at: datetime
    updated_at: datetime
    audio_codec: str | None = None
    thumbnail_path: str | None = None

    @property
    def frame_rate(self) -> float:
        """Compute frame rate as a float from numerator/denominator."""
        return self.frame_rate_numerator / self.frame_rate_denominator

    @property
    def duration_seconds(self) -> float:
        """Compute duration in seconds from frames and frame rate."""
        return self.duration_frames / self.frame_rate

    @staticmethod
    def new_id() -> str:
        """Generate a new unique ID for a video."""
        return str(uuid.uuid4())
