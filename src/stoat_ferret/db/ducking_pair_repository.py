# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""DuckingPair repository implementations (BL-517)."""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Protocol

import aiosqlite

from stoat_ferret.db.models import DuckingPair


class AsyncDuckingPairRepository(Protocol):
    """Protocol for async DuckingPair repository operations."""

    async def create(self, pair: DuckingPair) -> DuckingPair:
        """Create a ducking pair in the repository."""
        ...

    async def get(self, pair_id: str) -> DuckingPair | None:
        """Get a ducking pair by its ID."""
        ...

    async def list_by_project(self, project_id: str) -> list[DuckingPair]:
        """List all ducking pairs for a project."""
        ...

    async def update(self, pair: DuckingPair) -> DuckingPair:
        """Update an existing ducking pair's mutable fields."""
        ...

    async def delete(self, pair_id: str) -> bool:
        """Delete a ducking pair by its ID."""
        ...


class AsyncSQLiteDuckingPairRepository:
    """Async SQLite implementation of AsyncDuckingPairRepository."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize with an async database connection."""
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def create(self, pair: DuckingPair) -> DuckingPair:
        """Create a ducking pair in the repository."""
        try:
            await self._conn.execute(
                """
                INSERT INTO ducking_pair (
                    id, project_id, ducked_track_id, sidechain_track_id,
                    threshold, ratio, attack_ms, release_ms, apply_pre_volume,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pair.id,
                    pair.project_id,
                    pair.ducked_track_id,
                    pair.sidechain_track_id,
                    pair.threshold,
                    pair.ratio,
                    pair.attack_ms,
                    pair.release_ms,
                    int(pair.apply_pre_volume),
                    pair.created_at.isoformat(),
                    pair.updated_at.isoformat(),
                ),
            )
            await self._conn.commit()
        except aiosqlite.IntegrityError as e:
            raise ValueError(f"DuckingPair constraint violation: {e}") from e
        return pair

    async def get(self, pair_id: str) -> DuckingPair | None:
        """Get a ducking pair by its ID."""
        cursor = await self._conn.execute("SELECT * FROM ducking_pair WHERE id = ?", (pair_id,))
        row = await cursor.fetchone()
        return _row_to_pair(row) if row else None

    async def list_by_project(self, project_id: str) -> list[DuckingPair]:
        """List all ducking pairs for a project, ordered by created_at."""
        cursor = await self._conn.execute(
            "SELECT * FROM ducking_pair WHERE project_id = ? ORDER BY created_at",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_pair(row) for row in rows]

    async def update(self, pair: DuckingPair) -> DuckingPair:
        """Update mutable fields of a ducking pair."""
        cursor = await self._conn.execute(
            """
            UPDATE ducking_pair
            SET threshold = ?, ratio = ?, attack_ms = ?, release_ms = ?,
                apply_pre_volume = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                pair.threshold,
                pair.ratio,
                pair.attack_ms,
                pair.release_ms,
                int(pair.apply_pre_volume),
                pair.updated_at.isoformat(),
                pair.id,
            ),
        )
        await self._conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"DuckingPair {pair.id} does not exist")
        return pair

    async def delete(self, pair_id: str) -> bool:
        """Delete a ducking pair by its ID."""
        cursor = await self._conn.execute("DELETE FROM ducking_pair WHERE id = ?", (pair_id,))
        await self._conn.commit()
        return cursor.rowcount > 0


class AsyncInMemoryDuckingPairRepository:
    """In-memory implementation for testing."""

    def __init__(self) -> None:
        """Initialize with empty storage."""
        self._pairs: dict[str, DuckingPair] = {}

    async def create(self, pair: DuckingPair) -> DuckingPair:
        """Create a ducking pair in memory."""
        if pair.id in self._pairs:
            raise ValueError(f"DuckingPair {pair.id} already exists")
        if pair.ducked_track_id == pair.sidechain_track_id:
            raise ValueError("ducked_track_id and sidechain_track_id must be different")
        self._pairs[pair.id] = copy.deepcopy(pair)
        return copy.deepcopy(pair)

    async def get(self, pair_id: str) -> DuckingPair | None:
        """Get a ducking pair by its ID."""
        pair = self._pairs.get(pair_id)
        return copy.deepcopy(pair) if pair is not None else None

    async def list_by_project(self, project_id: str) -> list[DuckingPair]:
        """List all ducking pairs for a project."""
        return [
            copy.deepcopy(p)
            for p in sorted(self._pairs.values(), key=lambda p: p.created_at)
            if p.project_id == project_id
        ]

    async def update(self, pair: DuckingPair) -> DuckingPair:
        """Update mutable fields of a ducking pair."""
        if pair.id not in self._pairs:
            raise ValueError(f"DuckingPair {pair.id} does not exist")
        self._pairs[pair.id] = copy.deepcopy(pair)
        return copy.deepcopy(pair)

    async def delete(self, pair_id: str) -> bool:
        """Delete a ducking pair by its ID."""
        if pair_id not in self._pairs:
            return False
        del self._pairs[pair_id]
        return True


def _row_to_pair(row: aiosqlite.Row) -> DuckingPair:
    """Convert a database row to a DuckingPair object."""
    row_dict = dict(row)
    return DuckingPair(
        id=row_dict["id"],
        project_id=row_dict["project_id"],
        ducked_track_id=row_dict["ducked_track_id"],
        sidechain_track_id=row_dict["sidechain_track_id"],
        threshold=float(row_dict["threshold"]),
        ratio=float(row_dict["ratio"]),
        attack_ms=float(row_dict["attack_ms"]),
        release_ms=float(row_dict["release_ms"]),
        apply_pre_volume=bool(row_dict["apply_pre_volume"]),
        created_at=datetime.fromisoformat(row_dict["created_at"]),
        updated_at=datetime.fromisoformat(row_dict["updated_at"]),
    )
