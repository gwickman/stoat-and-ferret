"""Database model definitions for video metadata storage."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


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
