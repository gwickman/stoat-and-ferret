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
    """Paginated response for a directory listing request.

    Contains the parent path, list of subdirectories within it,
    and pagination metadata.
    """

    path: str
    directories: list[DirectoryEntry]
    total: int
    limit: int
    offset: int
