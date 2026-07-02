# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""HTTP-layer tests for TTS CRUD and synthesise endpoints (BL-580)."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.settings import Settings
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.tts_cue_repository import AsyncInMemoryTtsCueRepository

_PROJECT_ID = "12345678-1234-5678-1234-567812345678"
_TRACK_ID = "track-voice-1"


@pytest.fixture
def tts_repo() -> AsyncInMemoryTtsCueRepository:
    return AsyncInMemoryTtsCueRepository()


@pytest.fixture
def tts_app(tts_repo: AsyncInMemoryTtsCueRepository) -> FastAPI:
    return create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        tts_cue_repository=tts_repo,
    )


@pytest.fixture
def client(tts_app: FastAPI) -> Generator[TestClient, None, None]:
    with (
        patch(
            "stoat_ferret.api.routers.tts._validate_voice_track",
            new_callable=AsyncMock,
        ),
        TestClient(tts_app) as c,
    ):
        tts_app.state._settings = Settings()
        yield c


def _post_cue(
    client: TestClient,
    project_id: str = _PROJECT_ID,
    text: str = "Hello world",
) -> dict[str, Any]:
    resp = client.post(
        f"/api/v1/projects/{project_id}/tts_cues",
        json={
            "project_id": project_id,
            "track_id": _TRACK_ID,
            "start_s": 1.5,
            "text": text,
            "voice": "en_US-ryan-medium",
        },
    )
    assert resp.status_code == 201
    return resp.json()  # type: ignore[no-any-return]


def test_create_tts_cue(client: TestClient) -> None:
    data = _post_cue(client)
    assert "id" in data
    assert data["audio_path"] is None
    assert data["status"] == "pending"
    assert data["text"] == "Hello world"
    assert data["track_id"] == _TRACK_ID


def test_create_tts_cue_missing_text(client: TestClient) -> None:
    resp = client.post(
        f"/api/v1/projects/{_PROJECT_ID}/tts_cues",
        json={
            "project_id": _PROJECT_ID,
            "track_id": _TRACK_ID,
            "start_s": 0.0,
            "voice": "en_US-ryan-medium",
        },
    )
    assert resp.status_code == 422


def test_list_tts_cues(client: TestClient) -> None:
    _post_cue(client)
    resp = client.get(f"/api/v1/projects/{_PROJECT_ID}/tts_cues")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


def test_get_tts_cue_by_id(client: TestClient) -> None:
    created = _post_cue(client)
    cue_id = created["id"]
    resp = client.get(f"/api/v1/projects/{_PROJECT_ID}/tts_cues/{cue_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == cue_id


def test_get_tts_cue_not_found(client: TestClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000001"
    resp = client.get(f"/api/v1/projects/{_PROJECT_ID}/tts_cues/{fake_id}")
    assert resp.status_code == 404


def test_patch_tts_cue_start_s(client: TestClient) -> None:
    created = _post_cue(client)
    cue_id = created["id"]
    resp = client.patch(
        f"/api/v1/projects/{_PROJECT_ID}/tts_cues/{cue_id}",
        json={"start_s": 5.0},
    )
    assert resp.status_code == 200
    assert resp.json()["start_s"] == pytest.approx(5.0)


def test_delete_tts_cue(client: TestClient) -> None:
    created = _post_cue(client)
    cue_id = created["id"]
    del_resp = client.delete(f"/api/v1/projects/{_PROJECT_ID}/tts_cues/{cue_id}")
    assert del_resp.status_code == 204
    get_resp = client.get(f"/api/v1/projects/{_PROJECT_ID}/tts_cues/{cue_id}")
    assert get_resp.status_code == 404


def test_synthesise_returns_503_without_tts_service(client: TestClient) -> None:
    created = _post_cue(client)
    cue_id = created["id"]
    resp = client.post(f"/api/v1/projects/{_PROJECT_ID}/tts_cues/{cue_id}/synthesise")
    assert resp.status_code == 503
    assert resp.json()["detail"]["code"] == "TTS_SERVICE_UNAVAILABLE"


def test_list_voices_returns_200(client: TestClient) -> None:
    resp = client.get("/api/v1/tts/voices")
    assert resp.status_code == 200
    assert "voices" in resp.json()


async def test_audio_path_field_maps_generated_asset_id(
    tts_repo: AsyncInMemoryTtsCueRepository,
    tts_app: FastAPI,
) -> None:
    """BL-577 regression: audio_path in response must map cue.generated_asset_id."""
    with (
        patch(
            "stoat_ferret.api.routers.tts._validate_voice_track",
            new_callable=AsyncMock,
        ),
        TestClient(tts_app) as c,
    ):
        tts_app.state._settings = Settings()

        created = _post_cue(c)
        cue_id = created["id"]

        await tts_repo.update_status(
            cue_id,
            "ready",
            generated_asset_id="/cache/audio.wav",
        )

        resp = c.get(f"/api/v1/projects/{_PROJECT_ID}/tts_cues/{cue_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["audio_path"] == "/cache/audio.wav"
        assert "generated_asset_id" not in body
        assert body["status"] == "ready"
