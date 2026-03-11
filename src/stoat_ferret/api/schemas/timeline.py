"""Timeline API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TrackCreate(BaseModel):
    """Create track request."""

    track_type: str = Field(..., pattern=r"^(video|audio|text)$")
    label: str = Field(..., min_length=1)
    z_index: int | None = None
    muted: bool = False
    locked: bool = False


class TrackResponse(BaseModel):
    """Track response with clips."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    track_type: str
    label: str
    z_index: int
    muted: bool
    locked: bool
    clips: list[TimelineClipResponse] = []


class TimelineClipCreate(BaseModel):
    """Assign clip to timeline track."""

    clip_id: str
    track_id: str
    timeline_start: float = Field(..., ge=0)
    timeline_end: float = Field(..., gt=0)


class TimelineClipUpdate(BaseModel):
    """Update clip timeline position."""

    timeline_start: float | None = Field(default=None, ge=0)
    timeline_end: float | None = Field(default=None, gt=0)
    track_id: str | None = None


class TimelineClipResponse(BaseModel):
    """Timeline clip response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    source_video_id: str
    track_id: str | None
    timeline_start: float | None
    timeline_end: float | None
    in_point: int
    out_point: int


class TimelineResponse(BaseModel):
    """Full timeline response."""

    project_id: str
    tracks: list[TrackResponse]
    duration: float
    version: int
