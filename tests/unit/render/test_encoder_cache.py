"""Unit tests for encoder cache repository implementations.

Exercises both AsyncSQLiteEncoderCacheRepository and InMemoryEncoderCacheRepository
via parameterized fixtures, targeting the 17 uncovered statements in encoder_cache.py.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

import aiosqlite
import pytest

from stoat_ferret.db.schema import ENCODER_CACHE_TABLE
from stoat_ferret.render.encoder_cache import (
    AsyncSQLiteEncoderCacheRepository,
    EncoderCacheEntry,
    InMemoryEncoderCacheRepository,
)

_RepositoryType = AsyncSQLiteEncoderCacheRepository | InMemoryEncoderCacheRepository


def _make_entry(
    name: str = "libx264",
    codec: str = "h264",
    is_hardware: bool = False,
    encoder_type: str = "Software",
    description: str = "H.264 / AVC encoder",
    detected_at: datetime | None = None,
) -> EncoderCacheEntry:
    """Create a test encoder cache entry with sensible defaults."""
    if detected_at is None:
        detected_at = datetime.now(timezone.utc)
    return EncoderCacheEntry(
        id=None,
        name=name,
        codec=codec,
        is_hardware=is_hardware,
        encoder_type=encoder_type,
        description=description,
        detected_at=detected_at,
    )


@pytest.fixture(params=["sqlite", "memory"])
async def encoder_cache_repo(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[_RepositoryType, None]:
    """Provide both encoder cache implementations for contract testing."""
    if request.param == "sqlite":
        conn = await aiosqlite.connect(":memory:")
        conn.row_factory = aiosqlite.Row
        await conn.execute(ENCODER_CACHE_TABLE)
        await conn.commit()
        yield AsyncSQLiteEncoderCacheRepository(conn)
        await conn.close()
    else:
        yield InMemoryEncoderCacheRepository()


async def test_empty_cache_get_all(encoder_cache_repo: _RepositoryType) -> None:
    """get_all() returns empty list on a fresh repository."""
    result = await encoder_cache_repo.get_all()
    assert result == []


async def test_single_entry_roundtrip(encoder_cache_repo: _RepositoryType) -> None:
    """Insert one entry and retrieve it via get_all()."""
    entry = _make_entry(name="libx264", codec="h264")
    created = await encoder_cache_repo.create_many([entry])

    assert len(created) == 1
    assert created[0].id is not None
    assert created[0].name == "libx264"
    assert created[0].codec == "h264"

    all_entries = await encoder_cache_repo.get_all()
    assert len(all_entries) == 1
    assert all_entries[0].name == "libx264"
    assert all_entries[0].codec == "h264"


async def test_multiple_entries_create_many(encoder_cache_repo: _RepositoryType) -> None:
    """create_many() with multiple entries assigns IDs and persists all entries."""
    entries = [
        _make_entry(name="libx264", codec="h264"),
        _make_entry(name="libx265", codec="hevc"),
        _make_entry(name="h264_nvenc", codec="h264", is_hardware=True, encoder_type="Nvenc"),
    ]
    created = await encoder_cache_repo.create_many(entries)

    assert len(created) == 3
    assert all(e.id is not None for e in created)
    assert {e.name for e in created} == {"libx264", "libx265", "h264_nvenc"}

    all_entries = await encoder_cache_repo.get_all()
    assert len(all_entries) == 3


async def test_clear_operation(encoder_cache_repo: _RepositoryType) -> None:
    """clear() atomically removes all entries."""
    await encoder_cache_repo.create_many(
        [
            _make_entry(name="libx264"),
            _make_entry(name="libx265"),
        ]
    )
    assert len(await encoder_cache_repo.get_all()) == 2

    await encoder_cache_repo.clear()

    assert await encoder_cache_repo.get_all() == []


async def test_ttl_expiry_detection(encoder_cache_repo: _RepositoryType) -> None:
    """Entries with old detected_at are detectable as expired and cache can be refreshed."""
    old_time = datetime.now(timezone.utc) - timedelta(hours=24)
    await encoder_cache_repo.create_many([_make_entry(name="libx264", detected_at=old_time)])

    cached = await encoder_cache_repo.get_all()
    assert len(cached) == 1

    # detected_at is preserved; compute age for TTL decision (normalize if tzinfo stripped)
    retrieved_at = cached[0].detected_at
    if retrieved_at.tzinfo is None:
        retrieved_at = retrieved_at.replace(tzinfo=timezone.utc)
    assert datetime.now(timezone.utc) - retrieved_at > timedelta(hours=12)

    # Simulate cache refresh on TTL expiry: clear old entries, insert fresh
    await encoder_cache_repo.clear()
    await encoder_cache_repo.create_many([_make_entry(name="libx264")])

    refreshed = await encoder_cache_repo.get_all()
    assert len(refreshed) == 1
    fresh_at = refreshed[0].detected_at
    if fresh_at.tzinfo is None:
        fresh_at = fresh_at.replace(tzinfo=timezone.utc)
    assert datetime.now(timezone.utc) - fresh_at < timedelta(minutes=1)


async def test_datetime_iso_roundtrip(encoder_cache_repo: _RepositoryType) -> None:
    """detected_at datetime survives the store-and-retrieve cycle (_row_to_entry parsing)."""
    expected = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    await encoder_cache_repo.create_many([_make_entry(name="libx264", detected_at=expected)])

    retrieved = await encoder_cache_repo.get_all()
    assert len(retrieved) == 1

    retrieved_at = retrieved[0].detected_at
    # Normalize to UTC if tzinfo was stripped (e.g., SQLite stores without tz in some configs)
    if retrieved_at.tzinfo is None:
        retrieved_at = retrieved_at.replace(tzinfo=timezone.utc)
    assert retrieved_at == expected


async def test_get_all_ordered_by_name(encoder_cache_repo: _RepositoryType) -> None:
    """get_all() returns entries in ascending name order."""
    await encoder_cache_repo.create_many(
        [
            _make_entry(name="libx265"),
            _make_entry(name="h264_nvenc", is_hardware=True, encoder_type="Nvenc"),
            _make_entry(name="libx264"),
        ]
    )

    all_entries = await encoder_cache_repo.get_all()
    names = [e.name for e in all_entries]
    assert names == sorted(names)


async def test_hardware_encoder_flag_preserved(encoder_cache_repo: _RepositoryType) -> None:
    """is_hardware flag survives the store-and-retrieve cycle for both True and False."""
    await encoder_cache_repo.create_many(
        [
            _make_entry(name="h264_nvenc", is_hardware=True, encoder_type="Nvenc"),
            _make_entry(name="libx264", is_hardware=False, encoder_type="Software"),
        ]
    )

    by_name = {e.name: e for e in await encoder_cache_repo.get_all()}
    assert by_name["h264_nvenc"].is_hardware is True
    assert by_name["libx264"].is_hardware is False


async def test_sqlite_constraint_error(encoder_cache_repo: _RepositoryType) -> None:
    """SQLite raises IntegrityError on duplicate encoder name (UNIQUE constraint on name column)."""
    if isinstance(encoder_cache_repo, InMemoryEncoderCacheRepository):
        pytest.skip("SQLite-only: InMemory implementation does not enforce UNIQUE constraint")

    await encoder_cache_repo.create_many([_make_entry(name="libx264")])

    with pytest.raises(aiosqlite.IntegrityError):
        await encoder_cache_repo.create_many([_make_entry(name="libx264")])
