"""Clip repository implementations."""

from __future__ import annotations

import copy
import json
from datetime import datetime
from typing import Any, Protocol

import aiosqlite

from stoat_ferret.db.models import Clip


class AsyncClipRepository(Protocol):
    """Protocol for async clip repository operations.

    Implementations must provide async methods for CRUD operations
    on clip metadata.
    """

    async def add(self, clip: Clip) -> Clip:
        """Add a clip to the repository.

        Args:
            clip: The clip to add.

        Returns:
            The added clip.

        Raises:
            ValueError: If a clip with the same ID already exists or
                foreign key constraint fails.
        """
        ...

    async def get(self, id: str) -> Clip | None:
        """Get a clip by its ID.

        Args:
            id: The clip ID.

        Returns:
            The clip if found, None otherwise.
        """
        ...

    async def list_by_project(self, project_id: str) -> list[Clip]:
        """List clips in a project, ordered by timeline position.

        Args:
            project_id: The project ID to filter by.

        Returns:
            List of clips ordered by timeline position.
        """
        ...

    async def update(self, clip: Clip) -> Clip:
        """Update an existing clip.

        Args:
            clip: The clip with updated fields.

        Returns:
            The updated clip.

        Raises:
            ValueError: If the clip does not exist.
        """
        ...

    async def delete(self, id: str) -> bool:
        """Delete a clip by its ID.

        Args:
            id: The clip ID.

        Returns:
            True if the clip was deleted, False if it didn't exist.
        """
        ...


class AsyncSQLiteClipRepository:
    """Async SQLite implementation of the ClipRepository protocol."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize the repository with an async database connection.

        Args:
            conn: Async SQLite database connection.
        """
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def add(self, clip: Clip) -> Clip:
        """Add a clip to the repository."""
        effects_json = json.dumps(clip.effects) if clip.effects is not None else None
        try:
            await self._conn.execute(
                """
                INSERT INTO clips (id, project_id, source_video_id, in_point, out_point,
                                  timeline_position, effects_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clip.id,
                    clip.project_id,
                    clip.source_video_id,
                    clip.in_point,
                    clip.out_point,
                    clip.timeline_position,
                    effects_json,
                    clip.created_at.isoformat(),
                    clip.updated_at.isoformat(),
                ),
            )
            await self._conn.commit()
        except aiosqlite.IntegrityError as e:
            raise ValueError(f"Clip already exists or foreign key violation: {e}") from e
        return clip

    async def get(self, id: str) -> Clip | None:
        """Get a clip by its ID."""
        cursor = await self._conn.execute("SELECT * FROM clips WHERE id = ?", (id,))
        row = await cursor.fetchone()
        return self._row_to_clip(row) if row else None

    async def list_by_project(self, project_id: str) -> list[Clip]:
        """List clips in a project, ordered by timeline position."""
        cursor = await self._conn.execute(
            "SELECT * FROM clips WHERE project_id = ? ORDER BY timeline_position",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_clip(row) for row in rows]

    async def update(self, clip: Clip) -> Clip:
        """Update an existing clip."""
        effects_json = json.dumps(clip.effects) if clip.effects is not None else None
        cursor = await self._conn.execute(
            """
            UPDATE clips SET
                in_point = ?, out_point = ?, timeline_position = ?,
                effects_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                clip.in_point,
                clip.out_point,
                clip.timeline_position,
                effects_json,
                clip.updated_at.isoformat(),
                clip.id,
            ),
        )
        await self._conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Clip {clip.id} does not exist")
        return clip

    async def delete(self, id: str) -> bool:
        """Delete a clip by its ID."""
        cursor = await self._conn.execute("DELETE FROM clips WHERE id = ?", (id,))
        await self._conn.commit()
        return cursor.rowcount > 0

    def _row_to_clip(self, row: Any) -> Clip:
        """Convert a database row to a Clip object."""
        effects_raw = row["effects_json"]
        effects = json.loads(effects_raw) if effects_raw is not None else None
        return Clip(
            id=row["id"],
            project_id=row["project_id"],
            source_video_id=row["source_video_id"],
            in_point=row["in_point"],
            out_point=row["out_point"],
            timeline_position=row["timeline_position"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            effects=effects,
        )


class AsyncInMemoryClipRepository:
    """Async in-memory implementation for testing.

    Stores deepcopy-isolated objects so callers cannot mutate internal state.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._clips: dict[str, Clip] = {}

    async def add(self, clip: Clip) -> Clip:
        """Add a clip to the repository."""
        if clip.id in self._clips:
            raise ValueError(f"Clip {clip.id} already exists")
        self._clips[clip.id] = copy.deepcopy(clip)
        return copy.deepcopy(clip)

    async def get(self, id: str) -> Clip | None:
        """Get a clip by its ID."""
        clip = self._clips.get(id)
        return copy.deepcopy(clip) if clip is not None else None

    async def list_by_project(self, project_id: str) -> list[Clip]:
        """List clips in a project, ordered by timeline position."""
        clips = [c for c in self._clips.values() if c.project_id == project_id]
        return [copy.deepcopy(c) for c in sorted(clips, key=lambda c: c.timeline_position)]

    async def update(self, clip: Clip) -> Clip:
        """Update an existing clip."""
        if clip.id not in self._clips:
            raise ValueError(f"Clip {clip.id} does not exist")
        self._clips[clip.id] = copy.deepcopy(clip)
        return copy.deepcopy(clip)

    async def delete(self, id: str) -> bool:
        """Delete a clip by its ID."""
        if id not in self._clips:
            return False
        del self._clips[id]
        return True

    def seed(self, clips: list[Clip]) -> None:
        """Populate the repository with initial test data.

        Args:
            clips: List of clips to seed. Stored as deepcopies.
        """
        for clip in clips:
            self._clips[clip.id] = copy.deepcopy(clip)
