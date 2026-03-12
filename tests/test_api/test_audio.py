"""Tests for audio mix configuration endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.models import Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository

PREVIEW_URL = "/api/v1/audio/mix/preview"


def _mix_url(project_id: str) -> str:
    return f"/api/v1/projects/{project_id}/audio/mix"


def _make_project(project_id: str = "proj-1") -> Project:
    """Create a test project."""
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


def _valid_request(
    *,
    track_count: int = 2,
    volume: float = 1.0,
    master_volume: float = 1.0,
    normalize: bool = True,
) -> dict:
    """Build a valid AudioMixRequest body."""
    return {
        "tracks": [{"volume": volume, "fade_in": 0.5, "fade_out": 0.3} for _ in range(track_count)],
        "master_volume": master_volume,
        "normalize": normalize,
    }


# ---- POST /audio/mix/preview tests ----


@pytest.mark.api
def test_preview_returns_200(client: TestClient) -> None:
    """POST /audio/mix/preview with valid input returns 200."""
    response = client.post(PREVIEW_URL, json=_valid_request())
    assert response.status_code == 200


@pytest.mark.api
def test_preview_returns_filter_preview(client: TestClient) -> None:
    """POST /audio/mix/preview returns non-empty filter_preview string."""
    response = client.post(PREVIEW_URL, json=_valid_request())
    data = response.json()
    assert isinstance(data["filter_preview"], str)
    assert len(data["filter_preview"]) > 0


@pytest.mark.api
def test_preview_returns_tracks_configured(client: TestClient) -> None:
    """POST /audio/mix/preview returns correct tracks_configured count."""
    response = client.post(PREVIEW_URL, json=_valid_request(track_count=3))
    data = response.json()
    assert data["tracks_configured"] == 3


@pytest.mark.api
def test_preview_filter_contains_amix(client: TestClient) -> None:
    """Preview filter chain contains amix for multi-track mixing."""
    response = client.post(PREVIEW_URL, json=_valid_request())
    data = response.json()
    assert "amix" in data["filter_preview"]


@pytest.mark.api
def test_preview_filter_contains_volume(client: TestClient) -> None:
    """Preview filter chain contains volume filter for per-track volume."""
    response = client.post(PREVIEW_URL, json=_valid_request(volume=0.8))
    data = response.json()
    assert "volume" in data["filter_preview"]


@pytest.mark.api
def test_preview_master_volume_appended(client: TestClient) -> None:
    """Non-unity master volume appends VolumeBuilder filter via semicolon."""
    response = client.post(PREVIEW_URL, json=_valid_request(master_volume=1.5))
    data = response.json()
    filter_preview = data["filter_preview"]
    # Should contain semicolon-separated sections with master volume
    assert ";" in filter_preview
    assert "volume" in filter_preview


@pytest.mark.api
def test_preview_unity_master_volume_not_appended(client: TestClient) -> None:
    """Unity master volume (1.0) does not append extra volume filter."""
    response = client.post(PREVIEW_URL, json=_valid_request(master_volume=1.0))
    data = response.json()
    filter_preview = data["filter_preview"]
    # Count semicolons - with master_volume=1.0 there should be fewer sections
    response_with_master = client.post(PREVIEW_URL, json=_valid_request(master_volume=1.5))
    filter_with_master = response_with_master.json()["filter_preview"]
    # The filter with master volume should have more content
    assert len(filter_with_master) > len(filter_preview)


# ---- Volume validation tests ----


@pytest.mark.api
def test_preview_track_volume_too_high_returns_422(client: TestClient) -> None:
    """Track volume > 2.0 returns 422 with INVALID_AUDIO_VOLUME."""
    response = client.post(PREVIEW_URL, json=_valid_request(volume=2.5))
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "INVALID_AUDIO_VOLUME"


@pytest.mark.api
def test_preview_track_volume_negative_returns_422(client: TestClient) -> None:
    """Track volume < 0.0 returns 422 with INVALID_AUDIO_VOLUME."""
    response = client.post(PREVIEW_URL, json=_valid_request(volume=-0.1))
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "INVALID_AUDIO_VOLUME"


@pytest.mark.api
def test_preview_master_volume_too_high_returns_422(client: TestClient) -> None:
    """Master volume > 2.0 returns 422 with INVALID_AUDIO_VOLUME."""
    response = client.post(PREVIEW_URL, json=_valid_request(master_volume=2.5))
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "INVALID_AUDIO_VOLUME"


@pytest.mark.api
def test_preview_master_volume_negative_returns_422(client: TestClient) -> None:
    """Master volume < 0.0 returns 422 with INVALID_AUDIO_VOLUME."""
    response = client.post(PREVIEW_URL, json=_valid_request(master_volume=-0.5))
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "INVALID_AUDIO_VOLUME"


@pytest.mark.api
def test_preview_volume_boundary_zero_accepted(client: TestClient) -> None:
    """Volume at 0.0 boundary is accepted."""
    response = client.post(PREVIEW_URL, json=_valid_request(volume=0.0))
    assert response.status_code == 200


@pytest.mark.api
def test_preview_volume_boundary_two_accepted(client: TestClient) -> None:
    """Volume at 2.0 boundary is accepted."""
    response = client.post(PREVIEW_URL, json=_valid_request(volume=2.0))
    assert response.status_code == 200


# ---- Track count validation tests ----


@pytest.mark.api
def test_preview_one_track_returns_422(client: TestClient) -> None:
    """Fewer than 2 tracks returns 422 with INVALID_TRACK_COUNT."""
    response = client.post(PREVIEW_URL, json=_valid_request(track_count=1))
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "INVALID_TRACK_COUNT"


@pytest.mark.api
def test_preview_nine_tracks_returns_422(client: TestClient) -> None:
    """More than 8 tracks returns 422 with INVALID_TRACK_COUNT."""
    response = client.post(PREVIEW_URL, json=_valid_request(track_count=9))
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "INVALID_TRACK_COUNT"


@pytest.mark.api
def test_preview_two_tracks_accepted(client: TestClient) -> None:
    """Minimum 2 tracks is accepted."""
    response = client.post(PREVIEW_URL, json=_valid_request(track_count=2))
    assert response.status_code == 200


@pytest.mark.api
def test_preview_eight_tracks_accepted(client: TestClient) -> None:
    """Maximum 8 tracks is accepted."""
    response = client.post(PREVIEW_URL, json=_valid_request(track_count=8))
    assert response.status_code == 200
    data = response.json()
    assert data["tracks_configured"] == 8


# ---- PUT /projects/{id}/audio/mix tests ----


@pytest.mark.api
async def test_put_audio_mix_returns_200(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """PUT /projects/{id}/audio/mix with valid input returns 200."""
    project = _make_project()
    await project_repository.add(project)
    response = client.put(_mix_url("proj-1"), json=_valid_request())
    assert response.status_code == 200


@pytest.mark.api
async def test_put_audio_mix_returns_filter_preview(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """PUT returns filter_preview string."""
    project = _make_project()
    await project_repository.add(project)
    response = client.put(_mix_url("proj-1"), json=_valid_request())
    data = response.json()
    assert isinstance(data["filter_preview"], str)
    assert "amix" in data["filter_preview"]


@pytest.mark.api
async def test_put_audio_mix_persists_config(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """PUT persists audio mix configuration on the project."""
    project = _make_project()
    await project_repository.add(project)
    client.put(_mix_url("proj-1"), json=_valid_request())

    updated = await project_repository.get("proj-1")
    assert updated is not None
    assert updated.audio_mix is not None
    assert updated.audio_mix["master_volume"] == 1.0
    assert len(updated.audio_mix["tracks"]) == 2


@pytest.mark.api
async def test_put_audio_mix_project_not_found(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """PUT to non-existent project returns 404."""
    response = client.put(_mix_url("nonexistent"), json=_valid_request())
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_put_audio_mix_invalid_volume(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """PUT with invalid volume returns 422 INVALID_AUDIO_VOLUME."""
    project = _make_project()
    await project_repository.add(project)
    response = client.put(_mix_url("proj-1"), json=_valid_request(volume=3.0))
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "INVALID_AUDIO_VOLUME"


@pytest.mark.api
async def test_put_audio_mix_does_not_persist_on_validation_error(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """PUT with invalid input does not persist changes."""
    project = _make_project()
    await project_repository.add(project)
    client.put(_mix_url("proj-1"), json=_valid_request(volume=3.0))

    unchanged = await project_repository.get("proj-1")
    assert unchanged is not None
    assert unchanged.audio_mix is None


@pytest.mark.api
async def test_post_preview_does_not_persist(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """POST preview does not persist any data."""
    project = _make_project()
    await project_repository.add(project)
    client.post(PREVIEW_URL, json=_valid_request())

    unchanged = await project_repository.get("proj-1")
    assert unchanged is not None
    assert unchanged.audio_mix is None


# ---- Parity: Python AudioMixRequest to Rust AudioMixSpec mapping ----


@pytest.mark.api
def test_filter_preview_matches_rust_audio_mix_spec() -> None:
    """Python endpoint filter_preview matches direct Rust AudioMixSpec output."""
    from stoat_ferret_core import AudioMixSpec, TrackAudioConfig

    tracks = [
        TrackAudioConfig(1.0, 0.5, 0.3),
        TrackAudioConfig(0.8, 0.0, 0.0),
    ]
    spec = AudioMixSpec(tracks)
    expected = spec.build_filter_chain()

    from stoat_ferret.api.routers.audio import _build_filter_preview
    from stoat_ferret.api.schemas.audio import AudioMixRequest, TrackConfig

    request = AudioMixRequest(
        tracks=[
            TrackConfig(volume=1.0, fade_in=0.5, fade_out=0.3),
            TrackConfig(volume=0.8, fade_in=0.0, fade_out=0.0),
        ],
        master_volume=1.0,
        normalize=True,
    )
    actual = _build_filter_preview(request)
    assert actual == expected


@pytest.mark.api
def test_filter_preview_with_master_volume_matches_rust() -> None:
    """Filter preview with master volume matches Rust output + VolumeBuilder."""
    from stoat_ferret_core import AudioMixSpec, TrackAudioConfig, VolumeBuilder

    tracks = [
        TrackAudioConfig(1.0, 0.0, 0.0),
        TrackAudioConfig(1.0, 0.0, 0.0),
    ]
    spec = AudioMixSpec(tracks)
    expected_base = spec.build_filter_chain()
    master_filter = VolumeBuilder(1.5).build()
    expected = f"{expected_base};{master_filter}"

    from stoat_ferret.api.routers.audio import _build_filter_preview
    from stoat_ferret.api.schemas.audio import AudioMixRequest, TrackConfig

    request = AudioMixRequest(
        tracks=[
            TrackConfig(volume=1.0, fade_in=0.0, fade_out=0.0),
            TrackConfig(volume=1.0, fade_in=0.0, fade_out=0.0),
        ],
        master_volume=1.5,
        normalize=True,
    )
    actual = _build_filter_preview(request)
    assert actual == expected


# ---- DTO round-trip tests ----


@pytest.mark.api
def test_track_config_round_trip() -> None:
    """TrackConfig serializes and deserializes correctly."""
    from stoat_ferret.api.schemas.audio import TrackConfig

    track = TrackConfig(volume=0.8, fade_in=1.0, fade_out=0.5)
    data = track.model_dump()
    restored = TrackConfig.model_validate(data)
    assert restored == track


@pytest.mark.api
def test_audio_mix_request_round_trip() -> None:
    """AudioMixRequest serializes and deserializes correctly."""
    from stoat_ferret.api.schemas.audio import AudioMixRequest, TrackConfig

    req = AudioMixRequest(
        tracks=[
            TrackConfig(volume=1.0, fade_in=0.5, fade_out=0.3),
            TrackConfig(volume=0.5, fade_in=0.0, fade_out=1.0),
        ],
        master_volume=1.5,
        normalize=False,
    )
    data = req.model_dump()
    restored = AudioMixRequest.model_validate(data)
    assert restored == req


@pytest.mark.api
def test_audio_mix_response_round_trip() -> None:
    """AudioMixResponse serializes and deserializes correctly."""
    from stoat_ferret.api.schemas.audio import AudioMixResponse

    resp = AudioMixResponse(
        filter_preview="[0:a]volume=1.0[a0];amix=inputs=2",
        tracks_configured=2,
    )
    data = resp.model_dump()
    restored = AudioMixResponse.model_validate(data)
    assert restored == resp


# ---- Broadcast wiring tests ----


@pytest.mark.api
async def test_put_audio_mix_broadcasts_audio_mix_changed(
    app: FastAPI,
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """PUT /projects/{id}/audio/mix broadcasts audio_mix_changed event."""
    project = _make_project()
    await project_repository.add(project)

    mock_manager = AsyncMock(spec=ConnectionManager)
    app.state.ws_manager = mock_manager

    client.put(_mix_url("proj-1"), json=_valid_request())

    mock_manager.broadcast.assert_awaited_once()
    event = mock_manager.broadcast.call_args[0][0]
    assert event["type"] == "audio_mix_changed"
    assert event["payload"]["project_id"] == "proj-1"
    assert event["payload"]["tracks_configured"] == 2


@pytest.mark.api
async def test_put_audio_mix_no_broadcast_without_ws_manager(
    app: FastAPI,
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """PUT /projects/{id}/audio/mix does not fail without ws_manager."""
    project = _make_project()
    await project_repository.add(project)

    if hasattr(app.state, "ws_manager"):
        delattr(app.state, "ws_manager")

    response = client.put(_mix_url("proj-1"), json=_valid_request())
    assert response.status_code == 200


@pytest.mark.api
def test_preview_does_not_broadcast(app: FastAPI, client: TestClient) -> None:
    """POST /audio/mix/preview does not broadcast any events."""
    mock_manager = AsyncMock(spec=ConnectionManager)
    app.state.ws_manager = mock_manager

    client.post(PREVIEW_URL, json=_valid_request())

    mock_manager.broadcast.assert_not_awaited()
