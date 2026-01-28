"""Video API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VideoResponse(BaseModel):
    """Video response schema.

    Represents the API response format for a single video.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    path: str
    filename: str
    duration_frames: int
    frame_rate_numerator: int
    frame_rate_denominator: int
    width: int
    height: int
    video_codec: str
    audio_codec: str | None = None
    file_size: int
    thumbnail_path: str | None = None
    created_at: datetime
    updated_at: datetime


class VideoListResponse(BaseModel):
    """Paginated video list response.

    Contains a list of videos along with pagination metadata.
    """

    videos: list[VideoResponse]
    total: int
    limit: int
    offset: int


class VideoSearchResponse(BaseModel):
    """Search results response.

    Contains search results along with the query that was executed.
    """

    videos: list[VideoResponse]
    total: int
    query: str
