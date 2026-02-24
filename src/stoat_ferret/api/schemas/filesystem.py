"""Filesystem API schemas."""

from __future__ import annotations

from pydantic import BaseModel


class DirectoryEntry(BaseModel):
    """A single directory entry in a listing.

    Represents a subdirectory with its display name and full path.
    """

    name: str
    path: str


class DirectoryListResponse(BaseModel):
    """Response for a directory listing request.

    Contains the parent path and list of subdirectories within it.
    """

    path: str
    directories: list[DirectoryEntry]
