# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""HTTP-layer tests for DuckingPair CRUD endpoints (BL-581)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any

import aiosqlite
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.ducking_pair_repository import (
    AsyncInMemoryDuckingPairRepository,
    AsyncSQLiteDuckingPairRepository,
)
from stoat_ferret.db.models import DuckingPair, Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.schema import create_tables_async

_PROJECT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_TRACK_A = "track-music-1"
_TRACK_B = "track-voice-1"


def _make_project(project_id: str = _PROJECT_ID) -> Project:
    now = datetime.now(timezone.utc)
    return Project(
        id=project_id,
        name="Test Project",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def project_repo() -> AsyncInMemoryProjectRepository:
    repo = AsyncInMemoryProjectRepository()
    repo.seed([_make_project()])
    return repo


@pytest.fixture
def ducking_pair_repo() -> AsyncInMemoryDuckingPairRepository:
    return AsyncInMemoryDuckingPairRepository()


@pytest.fixture
def ducking_app(
    project_repo: AsyncInMemoryProjectRepository,
    ducking_pair_repo: AsyncInMemoryDuckingPairRepository,
) -> FastAPI:
    return create_app(
        project_repository=project_repo,
        ducking_pair_repository=ducking_pair_repo,
    )


@pytest.fixture
def client(ducking_app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(ducking_app) as c:
        yield c


def _post_pair(
    client: TestClient,
    *,
    project_id: str = _PROJECT_ID,
    ducked: str = _TRACK_A,
    sidechain: str = _TRACK_B,
) -> dict[str, Any]:
    resp = client.post(
        f"/api/v1/projects/{project_id}/ducking_pairs",
        json={
            "ducked_track_id": ducked,
            "sidechain_track_id": sidechain,
            "threshold": 0.5,
            "ratio": 4.0,
            "attack_ms": 10.0,
            "release_ms": 100.0,
            "apply_pre_volume": True,
        },
    )
    assert resp.status_code == 201
    return resp.json()  # type: ignore[no-any-return]


def test_create_ducking_pair(client: TestClient) -> None:
    data = _post_pair(client)
    assert "id" in data
    assert data["ducked_track_id"] == _TRACK_A
    assert data["sidechain_track_id"] == _TRACK_B
    assert data["threshold"] == pytest.approx(0.5)


def test_create_self_ducking_422(client: TestClient) -> None:
    resp = client.post(
        f"/api/v1/projects/{_PROJECT_ID}/ducking_pairs",
        json={
            "ducked_track_id": _TRACK_A,
            "sidechain_track_id": _TRACK_A,
            "threshold": 0.5,
            "ratio": 4.0,
            "attack_ms": 10.0,
            "release_ms": 100.0,
            "apply_pre_volume": False,
        },
    )
    assert resp.status_code == 422


def test_list_ducking_pairs(client: TestClient) -> None:
    _post_pair(client)
    resp = client.get(f"/api/v1/projects/{_PROJECT_ID}/ducking_pairs")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["ducked_track_id"] == _TRACK_A


def test_get_ducking_pair_by_id(client: TestClient) -> None:
    created = _post_pair(client)
    pair_id = created["id"]
    resp = client.get(f"/api/v1/projects/{_PROJECT_ID}/ducking_pairs/{pair_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == pair_id


def test_get_ducking_pair_not_found(client: TestClient) -> None:
    resp = client.get(f"/api/v1/projects/{_PROJECT_ID}/ducking_pairs/nonexistent-pair")
    assert resp.status_code == 404


def test_patch_ducking_pair(client: TestClient) -> None:
    created = _post_pair(client)
    pair_id = created["id"]
    resp = client.patch(
        f"/api/v1/projects/{_PROJECT_ID}/ducking_pairs/{pair_id}",
        json={"threshold": 0.25},
    )
    assert resp.status_code == 200
    assert resp.json()["threshold"] == pytest.approx(0.25)


def test_patch_immutable_track_id_forbidden(client: TestClient) -> None:
    created = _post_pair(client)
    pair_id = created["id"]
    resp = client.patch(
        f"/api/v1/projects/{_PROJECT_ID}/ducking_pairs/{pair_id}",
        json={"ducked_track_id": "new-track"},
    )
    assert resp.status_code == 422


def test_delete_ducking_pair(client: TestClient) -> None:
    created = _post_pair(client)
    pair_id = created["id"]
    del_resp = client.delete(f"/api/v1/projects/{_PROJECT_ID}/ducking_pairs/{pair_id}")
    assert del_resp.status_code == 204
    get_resp = client.get(f"/api/v1/projects/{_PROJECT_ID}/ducking_pairs/{pair_id}")
    assert get_resp.status_code == 404


def test_missing_project_returns_404(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/projects/no-such-project/ducking_pairs",
        json={
            "ducked_track_id": _TRACK_A,
            "sidechain_track_id": _TRACK_B,
            "threshold": 0.5,
            "ratio": 4.0,
            "attack_ms": 10.0,
            "release_ms": 100.0,
            "apply_pre_volume": False,
        },
    )
    assert resp.status_code == 404


def test_multi_pair_non_blocking(client: TestClient) -> None:
    _post_pair(client, ducked=_TRACK_A, sidechain=_TRACK_B)
    _post_pair(client, ducked=_TRACK_B, sidechain=_TRACK_A)
    resp = client.get(f"/api/v1/projects/{_PROJECT_ID}/ducking_pairs")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2


# ---------------------------------------------------------------------------
# BL-581-AC-4: SQLite FK constraint coverage
# ---------------------------------------------------------------------------


@pytest.fixture
async def sqlite_ducking_repo() -> AsyncSQLiteDuckingPairRepository:
    async with aiosqlite.connect(":memory:") as db:
        await create_tables_async(db)
        yield AsyncSQLiteDuckingPairRepository(db)


async def test_ducking_pair_fk_violation(
    sqlite_ducking_repo: AsyncSQLiteDuckingPairRepository,
) -> None:
    now = datetime.now(timezone.utc)
    pair = DuckingPair(
        id="pair-fk-test",
        project_id="nonexistent-project-id",
        ducked_track_id="track-a",
        sidechain_track_id="track-b",
        threshold=0.02,
        ratio=8.0,
        attack_ms=20.0,
        release_ms=300.0,
        apply_pre_volume=False,
        created_at=now,
        updated_at=now,
    )
    with pytest.raises(ValueError, match="constraint"):
        await sqlite_ducking_repo.create(pair)
