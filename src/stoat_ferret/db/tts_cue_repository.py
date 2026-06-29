# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""TtsCue repository implementations (BL-516)."""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Protocol

import aiosqlite

from stoat_ferret.db.models import TtsCue


class AsyncTtsCueRepository(Protocol):
    """Protocol for async TtsCue repository operations."""

    async def create(self, cue: TtsCue) -> TtsCue:
        """Create a TTS cue in the repository."""
        ...

    async def get(self, cue_id: str) -> TtsCue | None:
        """Get a TTS cue by its ID."""
        ...

    async def list_by_project(self, project_id: str) -> list[TtsCue]:
        """List all TTS cues for a project."""
        ...

    async def update(self, cue: TtsCue) -> TtsCue:
        """Update an existing TTS cue's mutable fields."""
        ...

    async def delete(self, cue_id: str) -> bool:
        """Delete a TTS cue by its ID."""
        ...

    async def update_status(
        self,
        cue_id: str,
        status: str,
        generated_asset_id: str | None = None,
        error: str | None = None,
    ) -> TtsCue | None:
        """Update the synthesis status of a TTS cue."""
        ...


class AsyncSQLiteTtsCueRepository:
    """Async SQLite implementation of AsyncTtsCueRepository."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize with an async database connection."""
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def create(self, cue: TtsCue) -> TtsCue:
        """Create a TTS cue in the repository."""
        try:
            await self._conn.execute(
                """
                INSERT INTO tts_cue (
                    id, project_id, track_id, start_s, text, voice, backend,
                    gain_db, pan, cache_key, generated_asset_id, status, error,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cue.id,
                    cue.project_id,
                    cue.track_id,
                    cue.start_s,
                    cue.text,
                    cue.voice,
                    cue.backend,
                    cue.gain_db,
                    cue.pan,
                    cue.cache_key,
                    cue.generated_asset_id,
                    cue.status,
                    cue.error,
                    cue.created_at.isoformat(),
                    cue.updated_at.isoformat(),
                ),
            )
            await self._conn.commit()
        except aiosqlite.IntegrityError as e:
            raise ValueError(f"TtsCue constraint violation: {e}") from e
        return cue

    async def get(self, cue_id: str) -> TtsCue | None:
        """Get a TTS cue by its ID."""
        cursor = await self._conn.execute("SELECT * FROM tts_cue WHERE id = ?", (cue_id,))
        row = await cursor.fetchone()
        return _row_to_cue(row) if row else None

    async def list_by_project(self, project_id: str) -> list[TtsCue]:
        """List all TTS cues for a project, ordered by start_s then created_at."""
        cursor = await self._conn.execute(
            "SELECT * FROM tts_cue WHERE project_id = ? ORDER BY start_s, created_at",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_cue(row) for row in rows]

    async def update(self, cue: TtsCue) -> TtsCue:
        """Update mutable fields of a TTS cue."""
        cursor = await self._conn.execute(
            """
            UPDATE tts_cue
            SET track_id = ?, start_s = ?, text = ?, voice = ?, backend = ?,
                gain_db = ?, pan = ?, cache_key = ?, generated_asset_id = ?,
                status = ?, error = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                cue.track_id,
                cue.start_s,
                cue.text,
                cue.voice,
                cue.backend,
                cue.gain_db,
                cue.pan,
                cue.cache_key,
                cue.generated_asset_id,
                cue.status,
                cue.error,
                cue.updated_at.isoformat(),
                cue.id,
            ),
        )
        await self._conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"TtsCue {cue.id} does not exist")
        return cue

    async def delete(self, cue_id: str) -> bool:
        """Delete a TTS cue by its ID."""
        cursor = await self._conn.execute("DELETE FROM tts_cue WHERE id = ?", (cue_id,))
        await self._conn.commit()
        return cursor.rowcount > 0

    async def update_status(
        self,
        cue_id: str,
        status: str,
        generated_asset_id: str | None = None,
        error: str | None = None,
    ) -> TtsCue | None:
        """Update the synthesis status of a TTS cue atomically."""
        from datetime import timezone

        now = datetime.now(timezone.utc).isoformat()
        cursor = await self._conn.execute(
            """
            UPDATE tts_cue
            SET status = ?, generated_asset_id = ?, error = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, generated_asset_id, error, now, cue_id),
        )
        await self._conn.commit()
        if cursor.rowcount == 0:
            return None
        return await self.get(cue_id)


class AsyncInMemoryTtsCueRepository:
    """In-memory implementation for testing."""

    def __init__(self) -> None:
        """Initialize with empty storage."""
        self._cues: dict[str, TtsCue] = {}

    async def create(self, cue: TtsCue) -> TtsCue:
        """Create a TTS cue in memory."""
        if cue.id in self._cues:
            raise ValueError(f"TtsCue {cue.id} already exists")
        self._cues[cue.id] = copy.deepcopy(cue)
        return copy.deepcopy(cue)

    async def get(self, cue_id: str) -> TtsCue | None:
        """Get a TTS cue by its ID."""
        cue = self._cues.get(cue_id)
        return copy.deepcopy(cue) if cue is not None else None

    async def list_by_project(self, project_id: str) -> list[TtsCue]:
        """List all TTS cues for a project."""
        return [
            copy.deepcopy(c)
            for c in sorted(self._cues.values(), key=lambda c: (c.start_s, c.created_at))
            if c.project_id == project_id
        ]

    async def update(self, cue: TtsCue) -> TtsCue:
        """Update mutable fields of a TTS cue."""
        if cue.id not in self._cues:
            raise ValueError(f"TtsCue {cue.id} does not exist")
        self._cues[cue.id] = copy.deepcopy(cue)
        return copy.deepcopy(cue)

    async def delete(self, cue_id: str) -> bool:
        """Delete a TTS cue by its ID."""
        if cue_id not in self._cues:
            return False
        del self._cues[cue_id]
        return True

    async def update_status(
        self,
        cue_id: str,
        status: str,
        generated_asset_id: str | None = None,
        error: str | None = None,
    ) -> TtsCue | None:
        """Update the synthesis status of a TTS cue in memory."""
        from datetime import timezone

        cue = self._cues.get(cue_id)
        if cue is None:
            return None
        updated = copy.deepcopy(cue)
        updated.status = status
        updated.generated_asset_id = generated_asset_id
        updated.error = error
        updated.updated_at = datetime.now(timezone.utc)
        self._cues[cue_id] = updated
        return copy.deepcopy(updated)


def _row_to_cue(row: aiosqlite.Row) -> TtsCue:
    """Convert a database row to a TtsCue object."""
    row_dict = dict(row)
    return TtsCue(
        id=row_dict["id"],
        project_id=row_dict["project_id"],
        track_id=row_dict["track_id"],
        start_s=float(row_dict["start_s"]),
        text=row_dict["text"],
        voice=row_dict["voice"],
        backend=row_dict["backend"],
        gain_db=float(row_dict["gain_db"]),
        pan=float(row_dict["pan"]),
        cache_key=row_dict["cache_key"],
        generated_asset_id=row_dict["generated_asset_id"],
        status=row_dict["status"],
        error=row_dict["error"],
        created_at=datetime.fromisoformat(row_dict["created_at"]),
        updated_at=datetime.fromisoformat(row_dict["updated_at"]),
    )
