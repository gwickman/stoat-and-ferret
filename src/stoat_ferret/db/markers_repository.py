"""Markers repository for timeline markers persistence."""

from __future__ import annotations

from typing import Protocol

import aiosqlite


class Marker:
    """Runtime marker data object."""

    __slots__ = ("id", "project_id", "start_time", "end_time", "name", "region_type", "created_at")

    def __init__(
        self,
        id: str,
        project_id: str,
        start_time: float,
        end_time: float | None,
        name: str | None,
        region_type: str,
        created_at: str,
    ) -> None:
        """Initialize a Marker."""
        self.id = id
        self.project_id = project_id
        self.start_time = start_time
        self.end_time = end_time
        self.name = name
        self.region_type = region_type
        self.created_at = created_at


class MarkerRepository(Protocol):
    """Protocol for async marker repository operations."""

    async def add(self, marker: Marker) -> Marker:
        """Add a marker to the repository."""
        ...

    async def list_by_project(
        self, project_id: str, region_type: str | None = None
    ) -> list[Marker]:
        """List markers for a project ordered by start_time ASC."""
        ...

    async def get(self, marker_id: str) -> Marker | None:
        """Get a marker by its ID."""
        ...

    async def update(self, marker: Marker) -> Marker | None:
        """Update a marker. Returns None if not found."""
        ...

    async def delete(self, marker_id: str) -> bool:
        """Delete a marker. Returns True if deleted, False if not found."""
        ...

    async def check_overlap(
        self,
        project_id: str,
        start_time: float,
        end_time: float,
        exclude_id: str | None = None,
    ) -> bool:
        """Return True if any existing section marker overlaps the given interval."""
        ...

    async def get_project_markers(self, project_id: str) -> list[Marker]:
        """Return all markers for a project ordered by start_time ASC (DI-accessible alias)."""
        ...


class AsyncSQLiteMarkerRepository:
    """Async SQLite implementation of the MarkerRepository protocol."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize the repository with an async database connection."""
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def add(self, marker: Marker) -> Marker:
        """Insert a new marker."""
        await self._conn.execute(
            """
            INSERT INTO project_markers
                (id, project_id, start_time, end_time, name, region_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                marker.id,
                marker.project_id,
                marker.start_time,
                marker.end_time,
                marker.name,
                marker.region_type,
                marker.created_at,
            ),
        )
        await self._conn.commit()
        return marker

    async def list_by_project(
        self, project_id: str, region_type: str | None = None
    ) -> list[Marker]:
        """List markers for a project ordered by start_time ASC."""
        if region_type is not None:
            cursor = await self._conn.execute(
                "SELECT * FROM project_markers WHERE project_id = ? AND region_type = ? "
                "ORDER BY start_time ASC",
                (project_id, region_type),
            )
        else:
            cursor = await self._conn.execute(
                "SELECT * FROM project_markers WHERE project_id = ? ORDER BY start_time ASC",
                (project_id,),
            )
        rows = await cursor.fetchall()
        return [self._row_to_marker(row) for row in rows]

    async def get(self, marker_id: str) -> Marker | None:
        """Get a marker by its ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM project_markers WHERE id = ?",
            (marker_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_marker(row) if row else None

    async def update(self, marker: Marker) -> Marker | None:
        """Update mutable fields of a marker. Returns None if not found."""
        cursor = await self._conn.execute(
            """
            UPDATE project_markers
               SET start_time = ?, end_time = ?, name = ?
             WHERE id = ?
            """,
            (marker.start_time, marker.end_time, marker.name, marker.id),
        )
        await self._conn.commit()
        if cursor.rowcount == 0:
            return None
        return marker

    async def delete(self, marker_id: str) -> bool:
        """Delete a marker by its ID."""
        cursor = await self._conn.execute(
            "DELETE FROM project_markers WHERE id = ?",
            (marker_id,),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def check_overlap(
        self,
        project_id: str,
        start_time: float,
        end_time: float,
        exclude_id: str | None = None,
    ) -> bool:
        """Return True if any existing section marker overlaps [start_time, end_time).

        Two intervals [a,b) and [c,d) overlap when a < d and c < b.
        Adjacent markers (end_time == start_time of next) are NOT overlapping.
        """
        if exclude_id is not None:
            cursor = await self._conn.execute(
                """
                SELECT 1 FROM project_markers
                 WHERE project_id = ?
                   AND region_type = 'section'
                   AND id != ?
                   AND start_time < ?
                   AND end_time > ?
                 LIMIT 1
                """,
                (project_id, exclude_id, end_time, start_time),
            )
        else:
            cursor = await self._conn.execute(
                """
                SELECT 1 FROM project_markers
                 WHERE project_id = ?
                   AND region_type = 'section'
                   AND start_time < ?
                   AND end_time > ?
                 LIMIT 1
                """,
                (project_id, end_time, start_time),
            )
        row = await cursor.fetchone()
        return row is not None

    async def get_project_markers(self, project_id: str) -> list[Marker]:
        """Return all markers for a project ordered by start_time ASC.

        DI-accessible alias for list() per BL-419-AC-5.
        """
        return await self.list_by_project(project_id)

    def _row_to_marker(self, row: aiosqlite.Row) -> Marker:
        """Convert a database row to a Marker."""
        return Marker(
            id=row["id"],
            project_id=row["project_id"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            name=row["name"],
            region_type=row["region_type"],
            created_at=row["created_at"],
        )


class AsyncInMemoryMarkerRepository:
    """Async in-memory marker repository for testing."""

    def __init__(self) -> None:
        """Initialize with empty storage."""
        self._markers: dict[str, Marker] = {}

    async def add(self, marker: Marker) -> Marker:
        """Add a marker."""
        self._markers[marker.id] = marker
        return marker

    async def list_by_project(
        self, project_id: str, region_type: str | None = None
    ) -> list[Marker]:
        """List markers for a project ordered by start_time ASC."""
        result = [m for m in self._markers.values() if m.project_id == project_id]
        if region_type is not None:
            result = [m for m in result if m.region_type == region_type]
        return sorted(result, key=lambda m: m.start_time)

    async def get(self, marker_id: str) -> Marker | None:
        """Get a marker by ID."""
        return self._markers.get(marker_id)

    async def update(self, marker: Marker) -> Marker | None:
        """Update a marker. Returns None if not found."""
        if marker.id not in self._markers:
            return None
        self._markers[marker.id] = marker
        return marker

    async def delete(self, marker_id: str) -> bool:
        """Delete a marker. Returns True if deleted."""
        if marker_id not in self._markers:
            return False
        del self._markers[marker_id]
        return True

    async def check_overlap(
        self,
        project_id: str,
        start_time: float,
        end_time: float,
        exclude_id: str | None = None,
    ) -> bool:
        """Return True if an existing section marker overlaps [start_time, end_time)."""
        for m in self._markers.values():
            if m.project_id != project_id or m.region_type != "section":
                continue
            if exclude_id is not None and m.id == exclude_id:
                continue
            if m.end_time is None:
                continue
            if m.start_time < end_time and m.end_time > start_time:
                return True
        return False

    async def get_project_markers(self, project_id: str) -> list[Marker]:
        """Return all markers for a project ordered by start_time ASC."""
        return await self.list_by_project(project_id)

    def delete_by_project(self, project_id: str) -> None:
        """Remove all markers for a project (test helper for cascade simulation)."""
        self._markers = {mid: m for mid, m in self._markers.items() if m.project_id != project_id}
