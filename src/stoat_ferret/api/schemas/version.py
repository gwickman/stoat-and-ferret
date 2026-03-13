"""Version API schemas."""

from __future__ import annotations

from pydantic import BaseModel


class VersionResponse(BaseModel):
    """Single version entry in a project's history.

    Attributes:
        version_number: Auto-incremented version number.
        created_at: ISO-8601 timestamp of when the version was created.
        checksum: SHA-256 hex digest of the timeline data.
    """

    version_number: int
    created_at: str
    checksum: str


class VersionListResponse(BaseModel):
    """Paginated list of project versions.

    Attributes:
        total: Total number of versions for the project.
        limit: Maximum number of versions returned.
        offset: Number of versions skipped.
        versions: List of version entries.
    """

    total: int
    limit: int
    offset: int
    versions: list[VersionResponse]


class RestoreResponse(BaseModel):
    """Response from restoring a previous version.

    Attributes:
        restored_version: The source version number that was restored.
        new_version: The newly created version number.
        message: Confirmation message.
    """

    restored_version: int
    new_version: int
    message: str
