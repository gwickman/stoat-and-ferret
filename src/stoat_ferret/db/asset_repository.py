# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Async asset repository for the user-asset library (BL-515)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

import aiosqlite


@dataclass
class AssetRecord:
    """Database record for a user-uploaded asset."""

    id: str
    original_filename: str
    content_hash: str
    mime_type: str
    kind: str
    size_bytes: int
    file_path: str
    created_at: str
    updated_at: str
    deleted_at: str | None = field(default=None)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_asset(row: aiosqlite.Row) -> AssetRecord:
    return AssetRecord(
        id=row["id"],
        original_filename=row["original_filename"],
        content_hash=row["content_hash"],
        mime_type=row["mime_type"],
        kind=row["kind"],
        size_bytes=row["size_bytes"],
        file_path=row["file_path"],
        deleted_at=row["deleted_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class AsyncAssetRepository(Protocol):
    """Protocol for async asset repository operations."""

    async def insert(self, asset: AssetRecord) -> AssetRecord:
        """Insert a new asset record."""
        ...

    async def get_by_id(self, asset_id: str) -> AssetRecord | None:
        """Get an asset by UUID, including soft-deleted."""
        ...

    async def get_by_content_hash(self, content_hash: str) -> AssetRecord | None:
        """Get an asset by content hash (SHA-256 hex), including soft-deleted."""
        ...

    async def list_assets(
        self,
        kind: str | None,
        tags: list[str] | None,
        offset: int,
        limit: int,
    ) -> list[AssetRecord]:
        """List active (non-deleted) assets, optionally filtered by kind."""
        ...

    async def soft_delete(self, asset_id: str) -> bool:
        """Soft-delete an asset by ID. Returns True if found and deleted."""
        ...

    async def restore(self, asset_id: str) -> AssetRecord | None:
        """Clear deleted_at on a soft-deleted asset and update updated_at."""
        ...


class AsyncSQLiteAssetRepository:
    """SQLite-backed async implementation of AsyncAssetRepository."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        """Initialize repository with an async SQLite connection.

        Args:
            db: An open aiosqlite connection with row_factory set.
        """
        self._db = db

    async def insert(self, asset: AssetRecord) -> AssetRecord:
        """Insert a new asset record and return it.

        Args:
            asset: The AssetRecord to persist.

        Returns:
            The persisted AssetRecord.
        """
        await self._db.execute(
            """
            INSERT INTO assets
                (id, original_filename, content_hash, mime_type, kind,
                 size_bytes, file_path, deleted_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset.id,
                asset.original_filename,
                asset.content_hash,
                asset.mime_type,
                asset.kind,
                asset.size_bytes,
                asset.file_path,
                asset.deleted_at,
                asset.created_at,
                asset.updated_at,
            ),
        )
        await self._db.commit()
        return asset

    async def get_by_id(self, asset_id: str) -> AssetRecord | None:
        """Get an asset by UUID (includes soft-deleted records).

        Args:
            asset_id: UUID string.

        Returns:
            AssetRecord or None if not found.
        """
        cursor = await self._db.execute("SELECT * FROM assets WHERE id = ?", (asset_id,))
        row = await cursor.fetchone()
        return _row_to_asset(row) if row else None

    async def get_by_content_hash(self, content_hash: str) -> AssetRecord | None:
        """Get an asset by SHA-256 content hash (includes soft-deleted records).

        Args:
            content_hash: Hex-encoded SHA-256 digest.

        Returns:
            AssetRecord or None if not found.
        """
        cursor = await self._db.execute(
            "SELECT * FROM assets WHERE content_hash = ?", (content_hash,)
        )
        row = await cursor.fetchone()
        return _row_to_asset(row) if row else None

    async def list_assets(
        self,
        kind: str | None,
        tags: list[str] | None,
        offset: int,
        limit: int,
    ) -> list[AssetRecord]:
        """List active (non-deleted) assets with optional kind filter.

        Tags filtering is deferred post-v090 (tags not stored in schema v090).

        Args:
            kind: Optional kind filter (e.g. "image").
            tags: Reserved for future use; ignored in v090.
            offset: Pagination offset.
            limit: Page size.

        Returns:
            List of AssetRecord objects.
        """
        if kind is not None:
            cursor = await self._db.execute(
                """
                SELECT * FROM assets
                WHERE deleted_at IS NULL AND kind = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (kind, limit, offset),
            )
        else:
            cursor = await self._db.execute(
                """
                SELECT * FROM assets
                WHERE deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
        rows = await cursor.fetchall()
        return [_row_to_asset(r) for r in rows]

    async def soft_delete(self, asset_id: str) -> bool:
        """Mark an asset as deleted by setting deleted_at.

        Args:
            asset_id: UUID string.

        Returns:
            True if the record was found and updated, False otherwise.
        """
        now = _now_iso()
        cursor = await self._db.execute(
            """
            UPDATE assets
            SET deleted_at = ?, updated_at = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (now, now, asset_id),
        )
        await self._db.commit()
        return (cursor.rowcount or 0) > 0

    async def restore(self, asset_id: str) -> AssetRecord | None:
        """Clear deleted_at on a soft-deleted asset (dedup restore path).

        Args:
            asset_id: UUID string.

        Returns:
            The restored AssetRecord, or None if not found.
        """
        now = _now_iso()
        await self._db.execute(
            """
            UPDATE assets
            SET deleted_at = NULL, updated_at = ?
            WHERE id = ?
            """,
            (now, asset_id),
        )
        await self._db.commit()
        return await self.get_by_id(asset_id)
