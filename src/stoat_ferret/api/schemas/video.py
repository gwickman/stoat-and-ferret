# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Video API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
    subtitle_count: int = 0
    data_count: int = 0
    subtitle_streams: list[dict[str, Any]] = Field(default_factory=list)


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


class ScanRequest(BaseModel):
    """Directory scan request.

    Specifies the directory to scan and whether to recurse into subdirectories.
    """

    model_config = ConfigDict(extra="forbid")

    path: str
    recursive: bool = True


class ScanError(BaseModel):
    """Scan error for an individual file.

    Records the path and error message when a file fails to process.
    """

    path: str
    error: str


class ScanResponse(BaseModel):
    """Scan results summary.

    Contains counts of scanned, new, updated, and skipped files,
    along with any errors encountered.
    """

    scanned: int
    new: int
    updated: int
    skipped: int
    errors: list[ScanError]
