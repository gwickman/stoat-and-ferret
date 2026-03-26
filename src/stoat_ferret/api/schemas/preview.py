"""Preview API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PreviewStartRequest(BaseModel):
    """Request to start a preview session."""

    quality: str = Field(default="medium", description="Preview quality level (low, medium, high)")


class PreviewStartResponse(BaseModel):
    """Response after starting a preview session."""

    session_id: str


class PreviewStatusResponse(BaseModel):
    """Response with preview session status."""

    session_id: str
    status: str
    manifest_url: str | None = None
    error_message: str | None = None


class PreviewSeekRequest(BaseModel):
    """Request to seek within a preview session."""

    position: float = Field(..., ge=0.0, description="Seek position in seconds")


class PreviewSeekResponse(BaseModel):
    """Response after seeking in a preview session."""

    session_id: str
    status: str


class PreviewStopResponse(BaseModel):
    """Response after stopping a preview session."""

    session_id: str
    stopped: bool = True
