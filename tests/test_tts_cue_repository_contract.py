# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""SQLite in-memory contract tests for TtsCue CRUD (BL-582-AC-4)."""

from __future__ import annotations

import hashlib
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import aiosqlite
import pytest

from stoat_ferret.db.models import TtsCue
from stoat_ferret.db.schema import create_tables_async
from stoat_ferret.db.tts_cue_repository import AsyncSQLiteTtsCueRepository

_PROJECT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_TRACK_ID = "track-voice-1"


def _cache_key(text: str, voice: str, backend: str) -> str:
    return hashlib.sha256(f"{text}::{voice}::{backend}".encode()).hexdigest()


def _make_cue(
    cue_id: str = "cue-001",
    project_id: str = _PROJECT_ID,
    start_s: float = 1.5,
    text: str = "Hello world",
    voice: str = "en_US-amy-medium",
    backend: str = "piper_local",
) -> TtsCue:
    now = datetime.now(timezone.utc)
    return TtsCue(
        id=cue_id,
        project_id=project_id,
        track_id=_TRACK_ID,
        start_s=start_s,
        text=text,
        voice=voice,
        backend=backend,
        gain_db=0.0,
        pan=0.0,
        cache_key=_cache_key(text, voice, backend),
        created_at=now,
        updated_at=now,
    )


async def _seed_project_and_track(db: aiosqlite.Connection, project_id: str, track_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO projects "
        "(id, name, output_width, output_height, output_fps, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (project_id, "Test Project", 1920, 1080, 30, now, now),
    )
    await db.execute(
        "INSERT INTO tracks (id, project_id, track_type, label, z_index, muted, locked) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (track_id, project_id, "audio", "Voice 1", 0, 0, 0),
    )
    await db.commit()


@pytest.fixture
async def sqlite_repo() -> AsyncGenerator[AsyncSQLiteTtsCueRepository, None]:
    async with aiosqlite.connect(":memory:") as db:
        await create_tables_async(db)
        await _seed_project_and_track(db, _PROJECT_ID, _TRACK_ID)
        yield AsyncSQLiteTtsCueRepository(db)


async def test_create_and_get(sqlite_repo: AsyncSQLiteTtsCueRepository) -> None:
    cue = _make_cue()
    created = await sqlite_repo.create(cue)
    assert created.id == cue.id
    assert created.text == "Hello world"

    fetched = await sqlite_repo.get(cue.id)
    assert fetched is not None
    assert fetched.id == cue.id
    assert fetched.start_s == pytest.approx(1.5)


async def test_get_missing_returns_none(sqlite_repo: AsyncSQLiteTtsCueRepository) -> None:
    result = await sqlite_repo.get("nonexistent-id")
    assert result is None


async def test_list_by_project(sqlite_repo: AsyncSQLiteTtsCueRepository) -> None:
    await sqlite_repo.create(_make_cue(cue_id="cue-a", start_s=2.0))
    await sqlite_repo.create(_make_cue(cue_id="cue-b", start_s=0.5))
    cues = await sqlite_repo.list_by_project(_PROJECT_ID)
    assert len(cues) == 2
    assert cues[0].start_s == pytest.approx(0.5)  # ordered by start_s


async def test_list_by_project_empty(sqlite_repo: AsyncSQLiteTtsCueRepository) -> None:
    cues = await sqlite_repo.list_by_project("no-such-project")
    assert cues == []


async def test_update(sqlite_repo: AsyncSQLiteTtsCueRepository) -> None:
    cue = _make_cue()
    await sqlite_repo.create(cue)
    now = datetime.now(timezone.utc)
    updated_cue = TtsCue(
        id=cue.id,
        project_id=cue.project_id,
        track_id=cue.track_id,
        start_s=5.0,
        text="Updated text",
        voice=cue.voice,
        backend=cue.backend,
        gain_db=cue.gain_db,
        pan=cue.pan,
        cache_key=_cache_key("Updated text", cue.voice, cue.backend),
        created_at=cue.created_at,
        updated_at=now,
    )
    result = await sqlite_repo.update(updated_cue)
    assert result.start_s == pytest.approx(5.0)
    assert result.text == "Updated text"

    fetched = await sqlite_repo.get(cue.id)
    assert fetched is not None
    assert fetched.text == "Updated text"


async def test_update_nonexistent_raises(sqlite_repo: AsyncSQLiteTtsCueRepository) -> None:
    cue = _make_cue(cue_id="ghost-cue")
    with pytest.raises(ValueError, match="ghost-cue"):
        await sqlite_repo.update(cue)


async def test_delete(sqlite_repo: AsyncSQLiteTtsCueRepository) -> None:
    cue = _make_cue()
    await sqlite_repo.create(cue)
    deleted = await sqlite_repo.delete(cue.id)
    assert deleted is True
    assert await sqlite_repo.get(cue.id) is None


async def test_delete_nonexistent_returns_false(
    sqlite_repo: AsyncSQLiteTtsCueRepository,
) -> None:
    result = await sqlite_repo.delete("no-such-cue")
    assert result is False


async def test_fk_violation_raises(sqlite_repo: AsyncSQLiteTtsCueRepository) -> None:
    cue = _make_cue(project_id="nonexistent-project-uuid")
    with pytest.raises(ValueError, match="constraint"):
        await sqlite_repo.create(cue)
