# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Delivery profile repository for persisting DeliveryProfile records."""

from __future__ import annotations

import json
from typing import Any, Protocol

import aiosqlite


class DeliveryProfile:
    """Runtime delivery profile data object."""

    __slots__ = (
        "id",
        "name",
        "output_formats",
        "loudness_target_lufs",
        "true_peak_ceiling_dbtp",
        "metadata_template",
        "created_at",
    )

    def __init__(
        self,
        id: str,
        name: str,
        output_formats: list[dict[str, Any]],
        loudness_target_lufs: float,
        true_peak_ceiling_dbtp: float,
        metadata_template: dict[str, Any] | None,
        created_at: str,
    ) -> None:
        """Initialize a DeliveryProfile."""
        self.id = id
        self.name = name
        self.output_formats = output_formats
        self.loudness_target_lufs = loudness_target_lufs
        self.true_peak_ceiling_dbtp = true_peak_ceiling_dbtp
        self.metadata_template = metadata_template
        self.created_at = created_at


class DeliveryProfileRepository(Protocol):
    """Protocol for async delivery profile repository operations."""

    async def add(self, profile: DeliveryProfile) -> DeliveryProfile:
        """Add a delivery profile to the repository."""
        ...

    async def list_all(self) -> list[DeliveryProfile]:
        """List all delivery profiles."""
        ...

    async def get_by_id(self, profile_id: str) -> DeliveryProfile | None:
        """Get a delivery profile by its UUID."""
        ...

    async def get_by_name(self, name: str) -> DeliveryProfile | None:
        """Get a delivery profile by its unique name."""
        ...

    async def delete(self, profile_id: str) -> bool:
        """Delete a delivery profile by UUID. Returns True if deleted."""
        ...


class AsyncSQLiteDeliveryProfileRepository:
    """Async SQLite implementation of the DeliveryProfileRepository protocol."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize the repository with an async database connection."""
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def add(self, profile: DeliveryProfile) -> DeliveryProfile:
        """Insert a new delivery profile."""
        await self._conn.execute(
            """
            INSERT INTO delivery_profiles
                (id, name, output_formats, loudness_target_lufs,
                 true_peak_ceiling_dbtp, metadata_template, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile.id,
                profile.name,
                json.dumps(profile.output_formats),
                profile.loudness_target_lufs,
                profile.true_peak_ceiling_dbtp,
                json.dumps(profile.metadata_template) if profile.metadata_template else None,
                profile.created_at,
            ),
        )
        await self._conn.commit()
        return profile

    async def list_all(self) -> list[DeliveryProfile]:
        """List all delivery profiles ordered by created_at ASC."""
        cursor = await self._conn.execute("SELECT * FROM delivery_profiles ORDER BY created_at ASC")
        rows = await cursor.fetchall()
        return [self._row_to_profile(row) for row in rows]

    async def get_by_id(self, profile_id: str) -> DeliveryProfile | None:
        """Get a delivery profile by its UUID."""
        cursor = await self._conn.execute(
            "SELECT * FROM delivery_profiles WHERE id = ?",
            (profile_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_profile(row) if row else None

    async def get_by_name(self, name: str) -> DeliveryProfile | None:
        """Get a delivery profile by its unique name."""
        cursor = await self._conn.execute(
            "SELECT * FROM delivery_profiles WHERE name = ?",
            (name,),
        )
        row = await cursor.fetchone()
        return self._row_to_profile(row) if row else None

    async def delete(self, profile_id: str) -> bool:
        """Delete a delivery profile by UUID. Returns True if deleted."""
        cursor = await self._conn.execute(
            "DELETE FROM delivery_profiles WHERE id = ?",
            (profile_id,),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    def _row_to_profile(self, row: aiosqlite.Row) -> DeliveryProfile:
        """Convert a database row to a DeliveryProfile."""
        return DeliveryProfile(
            id=row["id"],
            name=row["name"],
            output_formats=json.loads(row["output_formats"]),
            loudness_target_lufs=row["loudness_target_lufs"],
            true_peak_ceiling_dbtp=row["true_peak_ceiling_dbtp"],
            metadata_template=json.loads(row["metadata_template"])
            if row["metadata_template"]
            else None,
            created_at=row["created_at"],
        )


class AsyncInMemoryDeliveryProfileRepository:
    """Async in-memory delivery profile repository for testing."""

    def __init__(self) -> None:
        """Initialize with empty storage."""
        self._profiles: dict[str, DeliveryProfile] = {}

    async def add(self, profile: DeliveryProfile) -> DeliveryProfile:
        """Add a delivery profile."""
        self._profiles[profile.id] = profile
        return profile

    async def list_all(self) -> list[DeliveryProfile]:
        """List all delivery profiles ordered by created_at ASC."""
        return sorted(self._profiles.values(), key=lambda p: p.created_at)

    async def get_by_id(self, profile_id: str) -> DeliveryProfile | None:
        """Get a delivery profile by UUID."""
        return self._profiles.get(profile_id)

    async def get_by_name(self, name: str) -> DeliveryProfile | None:
        """Get a delivery profile by name."""
        for profile in self._profiles.values():
            if profile.name == name:
                return profile
        return None

    async def delete(self, profile_id: str) -> bool:
        """Delete a delivery profile. Returns True if deleted."""
        if profile_id not in self._profiles:
            return False
        del self._profiles[profile_id]
        return True
