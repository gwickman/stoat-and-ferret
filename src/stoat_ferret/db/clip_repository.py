# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

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

    async def split_atomic(self, clip_a: Clip, clip_b: Clip, original_id: str) -> tuple[Clip, Clip]:
        """Create clip_a and clip_b and delete original in a single atomic transaction.

        Args:
            clip_a: First segment of the split.
            clip_b: Second segment of the split.
            original_id: ID of the original clip to delete.

        Returns:
            Tuple of (clip_a, clip_b) after successful commit.

        Raises:
            ValueError: If the insert or delete fails.
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
        generator_params_json = (
            json.dumps(clip.generator_params) if clip.generator_params is not None else None
        )
        try:
            await self._conn.execute(
                """
                INSERT INTO clips (id, project_id, source_video_id, in_point, out_point,
                                  timeline_position, effects_json, created_at, updated_at,
                                  track_id, timeline_start, timeline_end,
                                  clip_type, generator_params, source_asset_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    clip.track_id,
                    clip.timeline_start,
                    clip.timeline_end,
                    clip.clip_type,
                    generator_params_json,
                    clip.source_asset_id,
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
                effects_json = ?, updated_at = ?,
                track_id = ?, timeline_start = ?, timeline_end = ?
            WHERE id = ?
            """,
            (
                clip.in_point,
                clip.out_point,
                clip.timeline_position,
                effects_json,
                clip.updated_at.isoformat(),
                clip.track_id,
                clip.timeline_start,
                clip.timeline_end,
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

    async def split_atomic(self, clip_a: Clip, clip_b: Clip, original_id: str) -> tuple[Clip, Clip]:
        """Create clip_a and clip_b and delete original in a single atomic transaction."""
        _insert = """
            INSERT INTO clips (id, project_id, source_video_id, in_point, out_point,
                               timeline_position, effects_json, created_at, updated_at,
                               track_id, timeline_start, timeline_end,
                               clip_type, generator_params, source_asset_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        def _params(clip: Clip) -> tuple[Any, ...]:
            effects_json = json.dumps(clip.effects) if clip.effects is not None else None
            gen_json = (
                json.dumps(clip.generator_params) if clip.generator_params is not None else None
            )
            return (
                clip.id,
                clip.project_id,
                clip.source_video_id,
                clip.in_point,
                clip.out_point,
                clip.timeline_position,
                effects_json,
                clip.created_at.isoformat(),
                clip.updated_at.isoformat(),
                clip.track_id,
                clip.timeline_start,
                clip.timeline_end,
                clip.clip_type,
                gen_json,
                clip.source_asset_id,
            )

        try:
            await self._conn.execute(_insert, _params(clip_a))
            await self._conn.execute(_insert, _params(clip_b))
            await self._conn.execute("DELETE FROM clips WHERE id = ?", (original_id,))
            await self._conn.commit()
        except aiosqlite.IntegrityError as e:
            await self._conn.rollback()
            raise ValueError(f"Split failed: {e}") from e
        return clip_a, clip_b

    def _row_to_clip(self, row: Any) -> Clip:
        """Convert a database row to a Clip object.

        Uses dict-style .get() for optional columns so that rows from
        databases that have not yet been migrated still work.
        """
        effects_raw = row["effects_json"]
        effects = json.loads(effects_raw) if effects_raw is not None else None
        # Convert aiosqlite.Row to dict for safe .get() access on new columns
        row_dict = dict(row)
        generator_params_raw = row_dict.get("generator_params")
        generator_params = (
            json.loads(generator_params_raw) if generator_params_raw is not None else None
        )
        return Clip(
            id=row["id"],
            project_id=row["project_id"],
            source_video_id=row_dict.get("source_video_id"),
            clip_type=row_dict.get("clip_type") or "file",
            generator_params=generator_params,
            in_point=row["in_point"],
            out_point=row["out_point"],
            timeline_position=row["timeline_position"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            effects=effects,
            track_id=row_dict.get("track_id"),
            timeline_start=row_dict.get("timeline_start"),
            timeline_end=row_dict.get("timeline_end"),
            source_asset_id=row_dict.get("source_asset_id"),
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

    async def split_atomic(self, clip_a: Clip, clip_b: Clip, original_id: str) -> tuple[Clip, Clip]:
        """Create clip_a and clip_b and delete original atomically (in-memory)."""
        self._clips[clip_a.id] = copy.deepcopy(clip_a)
        self._clips[clip_b.id] = copy.deepcopy(clip_b)
        del self._clips[original_id]
        return copy.deepcopy(clip_a), copy.deepcopy(clip_b)

    def seed(self, clips: list[Clip]) -> None:
        """Populate the repository with initial test data.

        Args:
            clips: List of clips to seed. Stored as deepcopies.
        """
        for clip in clips:
            self._clips[clip.id] = copy.deepcopy(clip)
