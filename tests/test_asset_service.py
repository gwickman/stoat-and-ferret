# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for asset library service logic (BL-515).

Covers: path traversal rejection, magic-bytes validation, and repository
CRUD (insert, dedup, soft-delete, restore) using an aiosqlite in-memory DB.
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import pytest

from stoat_ferret.api.routers.assets import _resolve_safe_path, _validate_image_magic_bytes
from stoat_ferret.db.asset_repository import AssetRecord, AsyncSQLiteAssetRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_png() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color=(255, 0, 0)).save(buf, format="JPEG")
    return buf.getvalue()


def _make_asset(
    *,
    content_hash: str = "abc123",
    kind: str = "image",
    deleted_at: str | None = None,
) -> AssetRecord:
    now = datetime.now(timezone.utc).isoformat()
    return AssetRecord(
        id=str(uuid.uuid4()),
        original_filename="test.png",
        content_hash=content_hash,
        mime_type="image/png",
        kind=kind,
        size_bytes=100,
        file_path="/tmp/test.png",
        created_at=now,
        updated_at=now,
        deleted_at=deleted_at,
    )


_ASSETS_DDL = """
CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    mime_type TEXT NOT NULL,
    kind TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


@pytest.fixture
async def repo() -> AsyncSQLiteAssetRepository:
    async with aiosqlite.connect(":memory:") as db:
        db.row_factory = aiosqlite.Row
        await db.execute(_ASSETS_DDL)
        await db.commit()
        yield AsyncSQLiteAssetRepository(db)


# ---------------------------------------------------------------------------
# _resolve_safe_path
# ---------------------------------------------------------------------------


def test_resolve_safe_path_valid(tmp_path: Path) -> None:
    path = _resolve_safe_path(tmp_path, "abc123.png")
    assert path == (tmp_path / "abc123.png").resolve()
    assert str(path).startswith(str(tmp_path.resolve()))


def test_resolve_safe_path_traversal_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="escapes"):
        _resolve_safe_path(tmp_path, "../outside.png")


def test_resolve_safe_path_nested_traversal_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="escapes"):
        _resolve_safe_path(tmp_path, "sub/../../escape.png")


# ---------------------------------------------------------------------------
# _validate_image_magic_bytes
# ---------------------------------------------------------------------------


def test_validate_png_accepted() -> None:
    fmt, mime = _validate_image_magic_bytes(_make_png())
    assert fmt == "PNG"
    assert mime == "image/png"


def test_validate_jpeg_accepted() -> None:
    fmt, mime = _validate_image_magic_bytes(_make_jpeg())
    assert fmt == "JPEG"
    assert mime == "image/jpeg"


def test_validate_non_image_rejected() -> None:
    with pytest.raises(ValueError):
        _validate_image_magic_bytes(b"not an image at all \x00\x01\x02")


def test_validate_bmp_rejected() -> None:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (1, 1)).save(buf, format="BMP")
    bmp_bytes = buf.getvalue()
    with pytest.raises(ValueError, match="not allowed"):
        _validate_image_magic_bytes(bmp_bytes)


# ---------------------------------------------------------------------------
# AsyncSQLiteAssetRepository
# ---------------------------------------------------------------------------


async def test_repo_insert_and_get_by_id(repo: AsyncSQLiteAssetRepository) -> None:
    asset = _make_asset(content_hash="hash001")
    saved = await repo.insert(asset)
    assert saved.id == asset.id

    fetched = await repo.get_by_id(asset.id)
    assert fetched is not None
    assert fetched.content_hash == "hash001"


async def test_repo_get_by_content_hash(repo: AsyncSQLiteAssetRepository) -> None:
    asset = _make_asset(content_hash="hash002")
    await repo.insert(asset)

    result = await repo.get_by_content_hash("hash002")
    assert result is not None
    assert result.id == asset.id


async def test_repo_get_by_id_not_found(repo: AsyncSQLiteAssetRepository) -> None:
    result = await repo.get_by_id("nonexistent-id")
    assert result is None


async def test_repo_list_excludes_deleted(repo: AsyncSQLiteAssetRepository) -> None:
    active = _make_asset(content_hash="active")
    deleted = _make_asset(
        content_hash="deleted",
        deleted_at=datetime.now(timezone.utc).isoformat(),
    )
    await repo.insert(active)
    await repo.insert(deleted)

    items = await repo.list_assets(kind=None, tags=None, offset=0, limit=50)
    ids = [r.id for r in items]
    assert active.id in ids
    assert deleted.id not in ids


async def test_repo_list_kind_filter(repo: AsyncSQLiteAssetRepository) -> None:
    img = _make_asset(content_hash="img", kind="image")
    fnt = _make_asset(content_hash="fnt", kind="font")
    await repo.insert(img)
    await repo.insert(fnt)

    items = await repo.list_assets(kind="image", tags=None, offset=0, limit=50)
    kinds = {r.kind for r in items}
    assert kinds == {"image"}


async def test_repo_soft_delete(repo: AsyncSQLiteAssetRepository) -> None:
    asset = _make_asset(content_hash="del001")
    await repo.insert(asset)

    ok = await repo.soft_delete(asset.id)
    assert ok is True

    record = await repo.get_by_id(asset.id)
    assert record is not None
    assert record.deleted_at is not None


async def test_repo_soft_delete_idempotent(repo: AsyncSQLiteAssetRepository) -> None:
    asset = _make_asset(content_hash="del002")
    await repo.insert(asset)
    await repo.soft_delete(asset.id)

    second = await repo.soft_delete(asset.id)
    assert second is False


async def test_repo_soft_delete_unknown_returns_false(repo: AsyncSQLiteAssetRepository) -> None:
    result = await repo.soft_delete("no-such-id")
    assert result is False


async def test_repo_restore(repo: AsyncSQLiteAssetRepository) -> None:
    now = datetime.now(timezone.utc).isoformat()
    deleted = _make_asset(content_hash="res001", deleted_at=now)
    await repo.insert(deleted)

    restored = await repo.restore(deleted.id)
    assert restored is not None
    assert restored.deleted_at is None


async def test_repo_get_by_content_hash_includes_deleted(
    repo: AsyncSQLiteAssetRepository,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    asset = _make_asset(content_hash="softdel", deleted_at=now)
    await repo.insert(asset)

    result = await repo.get_by_content_hash("softdel")
    assert result is not None
    assert result.deleted_at is not None
