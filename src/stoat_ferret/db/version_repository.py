"""Version repository implementations for project timeline versioning."""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import aiosqlite


@dataclass
class VersionRecord:
    """A saved version of a project timeline.

    Attributes:
        id: Database row ID (None for unsaved records).
        project_id: The project this version belongs to.
        version_number: Auto-incremented version number per project.
        timeline_json: Serialized timeline data.
        checksum: SHA-256 hex digest of timeline_json.
        created_at: When this version was created.
    """

    id: int | None
    project_id: str
    version_number: int
    timeline_json: str
    checksum: str
    created_at: datetime


def compute_checksum(timeline_json: str) -> str:
    """Compute SHA-256 checksum for timeline JSON data.

    Args:
        timeline_json: The timeline JSON string.

    Returns:
        Hex digest of the SHA-256 hash.
    """
    return hashlib.sha256(timeline_json.encode()).hexdigest()


class AsyncVersionRepository(Protocol):
    """Protocol for async version repository operations.

    Implementations must provide async methods for save, list, get,
    and restore operations on project versions.
    """

    async def save(self, project_id: str, timeline_json: str) -> VersionRecord:
        """Save a new version of a project timeline.

        Auto-increments the version number for the given project.

        Args:
            project_id: The project to save a version for.
            timeline_json: Serialized timeline data.

        Returns:
            The created version record.
        """
        ...

    async def list_versions(self, project_id: str) -> list[VersionRecord]:
        """List all versions for a project, ordered by version number descending.

        Args:
            project_id: The project to list versions for.

        Returns:
            List of version records, most recent first.
        """
        ...

    async def get_version(self, project_id: str, version_number: int) -> VersionRecord | None:
        """Get a specific version by project and version number.

        Args:
            project_id: The project ID.
            version_number: The version number to retrieve.

        Returns:
            The version record if found, None otherwise.
        """
        ...

    async def restore(self, project_id: str, version_number: int) -> VersionRecord:
        """Restore a previous version, creating a new version with that data.

        Non-destructive: restoring version 3 when current is 5 creates
        version 6 with version 3's timeline data.

        Args:
            project_id: The project ID.
            version_number: The version number to restore from.

        Returns:
            The newly created version record.

        Raises:
            ValueError: If the source version does not exist or checksum
                validation fails.
        """
        ...


class AsyncSQLiteVersionRepository:
    """Async SQLite implementation of the VersionRepository protocol."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize the repository with an async database connection.

        Args:
            conn: Async SQLite database connection.
        """
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def save(self, project_id: str, timeline_json: str) -> VersionRecord:
        """Save a new version of a project timeline."""
        checksum = compute_checksum(timeline_json)
        next_version = await self._next_version_number(project_id)
        now = datetime.now(timezone.utc)

        cursor = await self._conn.execute(
            """
            INSERT INTO project_versions
                (project_id, version_number, timeline_json, checksum, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, next_version, timeline_json, checksum, now.isoformat()),
        )
        await self._conn.commit()

        return VersionRecord(
            id=cursor.lastrowid,
            project_id=project_id,
            version_number=next_version,
            timeline_json=timeline_json,
            checksum=checksum,
            created_at=now,
        )

    async def list_versions(self, project_id: str) -> list[VersionRecord]:
        """List all versions for a project, most recent first."""
        cursor = await self._conn.execute(
            """
            SELECT * FROM project_versions
            WHERE project_id = ?
            ORDER BY version_number DESC
            """,
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_record(row) for row in rows]

    async def get_version(self, project_id: str, version_number: int) -> VersionRecord | None:
        """Get a specific version by project and version number."""
        cursor = await self._conn.execute(
            """
            SELECT * FROM project_versions
            WHERE project_id = ? AND version_number = ?
            """,
            (project_id, version_number),
        )
        row = await cursor.fetchone()
        return self._row_to_record(row) if row else None

    async def restore(self, project_id: str, version_number: int) -> VersionRecord:
        """Restore a previous version as a new version."""
        source = await self.get_version(project_id, version_number)
        if source is None:
            raise ValueError(f"Version {version_number} not found for project {project_id}")

        # Validate checksum integrity
        recomputed = compute_checksum(source.timeline_json)
        if recomputed != source.checksum:
            raise ValueError(
                f"Checksum mismatch for version {version_number}: "
                f"stored={source.checksum}, computed={recomputed}"
            )

        return await self.save(project_id, source.timeline_json)

    async def _next_version_number(self, project_id: str) -> int:
        """Get the next version number for a project.

        Args:
            project_id: The project ID.

        Returns:
            Next version number (1-based).
        """
        cursor = await self._conn.execute(
            "SELECT MAX(version_number) FROM project_versions WHERE project_id = ?",
            (project_id,),
        )
        row = await cursor.fetchone()
        assert row is not None  # MAX always returns a row
        current_max = row[0]
        return 1 if current_max is None else current_max + 1

    def _row_to_record(self, row: aiosqlite.Row) -> VersionRecord:
        """Convert a database row to a VersionRecord.

        Args:
            row: Database row.

        Returns:
            VersionRecord instance.
        """
        return VersionRecord(
            id=row["id"],
            project_id=row["project_id"],
            version_number=row["version_number"],
            timeline_json=row["timeline_json"],
            checksum=row["checksum"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


class AsyncInMemoryVersionRepository:
    """Async in-memory implementation for testing.

    Stores deepcopy-isolated objects so callers cannot mutate internal state.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._versions: dict[str, list[VersionRecord]] = {}
        self._next_id = 1

    async def save(self, project_id: str, timeline_json: str) -> VersionRecord:
        """Save a new version of a project timeline."""
        checksum = compute_checksum(timeline_json)
        project_versions = self._versions.setdefault(project_id, [])
        next_version = (
            1 if not project_versions else max(v.version_number for v in project_versions) + 1
        )
        now = datetime.now(timezone.utc)

        record = VersionRecord(
            id=self._next_id,
            project_id=project_id,
            version_number=next_version,
            timeline_json=timeline_json,
            checksum=checksum,
            created_at=now,
        )
        self._next_id += 1
        project_versions.append(copy.deepcopy(record))
        return record

    async def list_versions(self, project_id: str) -> list[VersionRecord]:
        """List all versions for a project, most recent first."""
        project_versions = self._versions.get(project_id, [])
        sorted_versions = sorted(project_versions, key=lambda v: v.version_number, reverse=True)
        return [copy.deepcopy(v) for v in sorted_versions]

    async def get_version(self, project_id: str, version_number: int) -> VersionRecord | None:
        """Get a specific version by project and version number."""
        project_versions = self._versions.get(project_id, [])
        for v in project_versions:
            if v.version_number == version_number:
                return copy.deepcopy(v)
        return None

    async def restore(self, project_id: str, version_number: int) -> VersionRecord:
        """Restore a previous version as a new version."""
        source = await self.get_version(project_id, version_number)
        if source is None:
            raise ValueError(f"Version {version_number} not found for project {project_id}")

        # Validate checksum integrity
        recomputed = compute_checksum(source.timeline_json)
        if recomputed != source.checksum:
            raise ValueError(
                f"Checksum mismatch for version {version_number}: "
                f"stored={source.checksum}, computed={recomputed}"
            )

        return await self.save(project_id, source.timeline_json)
