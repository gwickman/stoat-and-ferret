"""Timeline repository implementations."""

from __future__ import annotations

import copy
from typing import Any, Protocol

import aiosqlite

from stoat_ferret.db.models import Clip, Track


class AsyncTimelineRepository(Protocol):
    """Protocol for async timeline repository operations.

    Implementations must provide async methods for track CRUD,
    clip queries by track, and count methods.
    """

    async def create_track(self, track: Track) -> Track:
        """Create a track in the repository.

        Args:
            track: The track to create.

        Returns:
            The created track.

        Raises:
            ValueError: If a track with the same ID already exists or
                foreign key constraint fails.
        """
        ...

    async def get_track(self, track_id: str) -> Track | None:
        """Get a track by its ID.

        Args:
            track_id: The track ID.

        Returns:
            The track if found, None otherwise.
        """
        ...

    async def get_tracks_by_project(self, project_id: str) -> list[Track]:
        """List tracks in a project, ordered by z_index.

        Args:
            project_id: The project ID to filter by.

        Returns:
            List of tracks ordered by z_index.
        """
        ...

    async def update_track(self, track: Track) -> Track:
        """Update an existing track.

        Args:
            track: The track with updated fields.

        Returns:
            The updated track.

        Raises:
            ValueError: If the track does not exist.
        """
        ...

    async def delete_track(self, track_id: str) -> bool:
        """Delete a track by its ID.

        Args:
            track_id: The track ID.

        Returns:
            True if the track was deleted, False if it didn't exist.
        """
        ...

    async def get_clips_by_track(self, track_id: str) -> list[Clip]:
        """Get clips assigned to a track, ordered by timeline_start.

        Args:
            track_id: The track ID to filter by.

        Returns:
            List of clips ordered by timeline_start.
        """
        ...

    async def count_tracks(self, project_id: str) -> int:
        """Return the number of tracks in a project.

        Args:
            project_id: The project ID to count tracks for.

        Returns:
            Track count for the project.
        """
        ...

    async def count_clips(self, project_id: str) -> int:
        """Return the number of clips in a project.

        Args:
            project_id: The project ID to count clips for.

        Returns:
            Clip count for the project.
        """
        ...


class AsyncSQLiteTimelineRepository:
    """Async SQLite implementation of the TimelineRepository protocol."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize the repository with an async database connection.

        Args:
            conn: Async SQLite database connection.
        """
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def create_track(self, track: Track) -> Track:
        """Create a track in the repository."""
        try:
            await self._conn.execute(
                """
                INSERT INTO tracks (id, project_id, track_type, label, z_index, muted, locked)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    track.id,
                    track.project_id,
                    track.track_type,
                    track.label,
                    track.z_index,
                    int(track.muted),
                    int(track.locked),
                ),
            )
            await self._conn.commit()
        except aiosqlite.IntegrityError as e:
            raise ValueError(f"Track already exists or foreign key violation: {e}") from e
        return track

    async def get_track(self, track_id: str) -> Track | None:
        """Get a track by its ID."""
        cursor = await self._conn.execute("SELECT * FROM tracks WHERE id = ?", (track_id,))
        row = await cursor.fetchone()
        return self._row_to_track(row) if row else None

    async def get_tracks_by_project(self, project_id: str) -> list[Track]:
        """List tracks in a project, ordered by z_index."""
        cursor = await self._conn.execute(
            "SELECT * FROM tracks WHERE project_id = ? ORDER BY z_index",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_track(row) for row in rows]

    async def update_track(self, track: Track) -> Track:
        """Update an existing track."""
        cursor = await self._conn.execute(
            """
            UPDATE tracks SET label = ?, muted = ?, locked = ?
            WHERE id = ?
            """,
            (
                track.label,
                int(track.muted),
                int(track.locked),
                track.id,
            ),
        )
        await self._conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Track {track.id} does not exist")
        return track

    async def delete_track(self, track_id: str) -> bool:
        """Delete a track by its ID."""
        cursor = await self._conn.execute("DELETE FROM tracks WHERE id = ?", (track_id,))
        await self._conn.commit()
        return cursor.rowcount > 0

    async def get_clips_by_track(self, track_id: str) -> list[Clip]:
        """Get clips assigned to a track, ordered by timeline_start."""
        cursor = await self._conn.execute(
            "SELECT * FROM clips WHERE track_id = ? ORDER BY timeline_start",
            (track_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_clip(row) for row in rows]

    async def count_tracks(self, project_id: str) -> int:
        """Return the number of tracks in a project."""
        cursor = await self._conn.execute(
            "SELECT COUNT(*) FROM tracks WHERE project_id = ?",
            (project_id,),
        )
        row = await cursor.fetchone()
        assert row is not None  # COUNT(*) always returns a row
        return int(row[0])

    async def count_clips(self, project_id: str) -> int:
        """Return the number of clips in a project."""
        cursor = await self._conn.execute(
            "SELECT COUNT(*) FROM clips WHERE project_id = ?",
            (project_id,),
        )
        row = await cursor.fetchone()
        assert row is not None  # COUNT(*) always returns a row
        return int(row[0])

    def _row_to_track(self, row: Any) -> Track:
        """Convert a database row to a Track object."""
        return Track(
            id=row["id"],
            project_id=row["project_id"],
            track_type=row["track_type"],
            label=row["label"],
            z_index=row["z_index"],
            muted=bool(row["muted"]),
            locked=bool(row["locked"]),
        )

    def _row_to_clip(self, row: Any) -> Clip:
        """Convert a database row to a Clip object.

        Uses dict-style .get() for timeline columns so that rows from
        databases that have not yet been migrated still work.
        """
        import json
        from datetime import datetime

        effects_raw = row["effects_json"]
        effects = json.loads(effects_raw) if effects_raw is not None else None
        row_dict = dict(row)
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
            track_id=row_dict.get("track_id"),
            timeline_start=row_dict.get("timeline_start"),
            timeline_end=row_dict.get("timeline_end"),
        )


class AsyncInMemoryTimelineRepository:
    """Async in-memory implementation for testing.

    Stores deepcopy-isolated objects so callers cannot mutate internal state.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._tracks: dict[str, Track] = {}
        self._clips: dict[str, Clip] = {}

    async def create_track(self, track: Track) -> Track:
        """Create a track in the repository."""
        if track.id in self._tracks:
            raise ValueError(f"Track {track.id} already exists")
        self._tracks[track.id] = copy.deepcopy(track)
        return copy.deepcopy(track)

    async def get_track(self, track_id: str) -> Track | None:
        """Get a track by its ID."""
        track = self._tracks.get(track_id)
        return copy.deepcopy(track) if track is not None else None

    async def get_tracks_by_project(self, project_id: str) -> list[Track]:
        """List tracks in a project, ordered by z_index."""
        tracks = [t for t in self._tracks.values() if t.project_id == project_id]
        return [copy.deepcopy(t) for t in sorted(tracks, key=lambda t: t.z_index)]

    async def update_track(self, track: Track) -> Track:
        """Update an existing track."""
        if track.id not in self._tracks:
            raise ValueError(f"Track {track.id} does not exist")
        self._tracks[track.id] = copy.deepcopy(track)
        return copy.deepcopy(track)

    async def delete_track(self, track_id: str) -> bool:
        """Delete a track by its ID."""
        if track_id not in self._tracks:
            return False
        del self._tracks[track_id]
        return True

    async def get_clips_by_track(self, track_id: str) -> list[Clip]:
        """Get clips assigned to a track, ordered by timeline_start."""
        clips = [c for c in self._clips.values() if c.track_id == track_id]

        def _sort_key(c: Clip) -> float:
            return c.timeline_start if c.timeline_start is not None else 0.0

        return [copy.deepcopy(c) for c in sorted(clips, key=_sort_key)]

    async def count_tracks(self, project_id: str) -> int:
        """Return the number of tracks in a project."""
        return sum(1 for t in self._tracks.values() if t.project_id == project_id)

    async def count_clips(self, project_id: str) -> int:
        """Return the number of clips in a project."""
        return sum(1 for c in self._clips.values() if c.project_id == project_id)

    def seed(self, tracks: list[Track], clips: list[Clip] | None = None) -> None:
        """Populate the repository with initial test data.

        Args:
            tracks: List of tracks to seed. Stored as deepcopies.
            clips: Optional list of clips to seed. Stored as deepcopies.
        """
        for track in tracks:
            self._tracks[track.id] = copy.deepcopy(track)
        if clips is not None:
            for clip in clips:
                self._clips[clip.id] = copy.deepcopy(clip)
