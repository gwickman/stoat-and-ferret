"""Database model definitions for video metadata storage."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stoat_ferret_core import ClipValidationError as RustClipValidationError


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

        # Note: type ignores due to incomplete auto-generated stubs for Position/Duration/Clip
        in_pos = Position(self.in_point)  # type: ignore[call-arg]
        out_pos = Position(self.out_point)  # type: ignore[call-arg]
        source_dur = (
            Duration(source_duration_frames)  # type: ignore[call-arg]
            if source_duration_frames is not None
            else None
        )

        rust_clip = RustClip(source_path, in_pos, out_pos, source_dur)  # type: ignore[call-arg]
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
