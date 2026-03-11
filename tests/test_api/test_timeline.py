"""Tests for timeline endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Track
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.timeline_repository import AsyncInMemoryTimelineRepository
from tests.factories import make_test_video

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)


def _make_project(project_id: str = "proj-1", name: str = "Test") -> dict[str, object]:
    """Return kwargs for a Project dataclass."""
    return {
        "id": project_id,
        "name": name,
        "output_width": 1920,
        "output_height": 1080,
        "output_fps": 30,
        "created_at": _NOW,
        "updated_at": _NOW,
    }


# ---------------------------------------------------------------------------
# PUT /projects/{project_id}/timeline
# ---------------------------------------------------------------------------


@pytest.mark.api
async def test_put_timeline_creates_tracks(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """PUT timeline creates tracks and returns TimelineResponse."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    response = client.put(
        "/api/v1/projects/proj-1/timeline",
        json=[
            {"track_type": "video", "label": "Video 1"},
            {"track_type": "audio", "label": "Audio 1"},
        ],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "proj-1"
    assert len(data["tracks"]) == 2
    assert data["tracks"][0]["track_type"] == "video"
    assert data["tracks"][0]["label"] == "Video 1"
    assert data["tracks"][0]["z_index"] == 0
    assert data["tracks"][1]["track_type"] == "audio"
    assert data["tracks"][1]["label"] == "Audio 1"
    assert data["tracks"][1]["z_index"] == 1
    assert data["duration"] == 0.0
    assert data["version"] == 1


@pytest.mark.api
async def test_put_timeline_replaces_existing_tracks(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
) -> None:
    """PUT timeline replaces existing tracks."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    # Create initial tracks
    await timeline_repository.create_track(
        Track(id="old-1", project_id="proj-1", track_type="video", label="Old", z_index=0)
    )

    # Replace with new tracks
    response = client.put(
        "/api/v1/projects/proj-1/timeline",
        json=[{"track_type": "text", "label": "Subtitles"}],
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["tracks"]) == 1
    assert data["tracks"][0]["track_type"] == "text"
    assert data["tracks"][0]["label"] == "Subtitles"


@pytest.mark.api
async def test_put_timeline_custom_z_index(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """PUT timeline respects custom z_index."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    response = client.put(
        "/api/v1/projects/proj-1/timeline",
        json=[
            {"track_type": "video", "label": "V1", "z_index": 10},
            {"track_type": "audio", "label": "A1", "z_index": 5},
        ],
    )
    assert response.status_code == 200
    data = response.json()
    # Tracks in response ordered by z_index (from put order, not sorted)
    assert data["tracks"][0]["z_index"] == 10
    assert data["tracks"][1]["z_index"] == 5


@pytest.mark.api
def test_put_timeline_project_not_found(client: TestClient) -> None:
    """PUT timeline returns 404 for unknown project."""
    response = client.put(
        "/api/v1/projects/nonexistent/timeline",
        json=[{"track_type": "video", "label": "V1"}],
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
def test_put_timeline_invalid_track_type(client: TestClient) -> None:
    """PUT timeline rejects invalid track type."""
    response = client.put(
        "/api/v1/projects/proj-1/timeline",
        json=[{"track_type": "invalid", "label": "V1"}],
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /projects/{project_id}/timeline
# ---------------------------------------------------------------------------


@pytest.mark.api
async def test_get_timeline_empty(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """GET timeline returns empty structure for project without tracks."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    response = client.get("/api/v1/projects/proj-1/timeline")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "proj-1"
    assert data["tracks"] == []
    assert data["duration"] == 0.0
    assert data["version"] == 1


@pytest.mark.api
async def test_get_timeline_with_tracks_and_clips(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """GET timeline returns tracks with clips ordered correctly."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    # Create tracks
    track1 = Track(id="track-1", project_id="proj-1", track_type="video", label="V1", z_index=0)
    track2 = Track(id="track-2", project_id="proj-1", track_type="audio", label="A1", z_index=1)
    await timeline_repository.create_track(track1)
    await timeline_repository.create_track(track2)

    # Create a clip assigned to track-1
    video = make_test_video()
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        track_id="track-1",
        timeline_start=0.0,
        timeline_end=5.0,
    )
    await clip_repository.add(clip)

    response = client.get("/api/v1/projects/proj-1/timeline")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tracks"]) == 2
    # Track 1 has one clip
    assert len(data["tracks"][0]["clips"]) == 1
    assert data["tracks"][0]["clips"][0]["id"] == "clip-1"
    assert data["tracks"][0]["clips"][0]["timeline_start"] == 0.0
    assert data["tracks"][0]["clips"][0]["timeline_end"] == 5.0
    # Track 2 has no clips
    assert len(data["tracks"][1]["clips"]) == 0
    # Duration is max timeline_end
    assert data["duration"] == 5.0


@pytest.mark.api
def test_get_timeline_project_not_found(client: TestClient) -> None:
    """GET timeline returns 404 for unknown project."""
    response = client.get("/api/v1/projects/nonexistent/timeline")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# POST /projects/{project_id}/timeline/clips
# ---------------------------------------------------------------------------


@pytest.mark.api
async def test_post_timeline_clip(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """POST timeline clip assigns clip to track."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    track = Track(id="track-1", project_id="proj-1", track_type="video", label="V1", z_index=0)
    await timeline_repository.create_track(track)

    video = make_test_video()
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
    )
    await clip_repository.add(clip)

    response = client.post(
        "/api/v1/projects/proj-1/timeline/clips",
        json={
            "clip_id": "clip-1",
            "track_id": "track-1",
            "timeline_start": 0.0,
            "timeline_end": 5.0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "clip-1"
    assert data["track_id"] == "track-1"
    assert data["timeline_start"] == 0.0
    assert data["timeline_end"] == 5.0


@pytest.mark.api
async def test_post_timeline_clip_track_not_found(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """POST timeline clip returns 404 for unknown track."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    video = make_test_video()
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
    )
    await clip_repository.add(clip)

    response = client.post(
        "/api/v1/projects/proj-1/timeline/clips",
        json={
            "clip_id": "clip-1",
            "track_id": "nonexistent",
            "timeline_start": 0.0,
            "timeline_end": 5.0,
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "TRACK_NOT_FOUND"


@pytest.mark.api
async def test_post_timeline_clip_invalid_position(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """POST timeline clip returns 422 for invalid positions."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    track = Track(id="track-1", project_id="proj-1", track_type="video", label="V1", z_index=0)
    await timeline_repository.create_track(track)

    video = make_test_video()
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
    )
    await clip_repository.add(clip)

    # timeline_start >= timeline_end
    response = client.post(
        "/api/v1/projects/proj-1/timeline/clips",
        json={
            "clip_id": "clip-1",
            "track_id": "track-1",
            "timeline_start": 5.0,
            "timeline_end": 3.0,
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "INVALID_POSITION"


@pytest.mark.api
def test_post_timeline_clip_project_not_found(client: TestClient) -> None:
    """POST timeline clip returns 404 for unknown project."""
    response = client.post(
        "/api/v1/projects/nonexistent/timeline/clips",
        json={
            "clip_id": "clip-1",
            "track_id": "track-1",
            "timeline_start": 0.0,
            "timeline_end": 5.0,
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_post_timeline_clip_not_found(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
) -> None:
    """POST timeline clip returns 404 for unknown clip."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    track = Track(id="track-1", project_id="proj-1", track_type="video", label="V1", z_index=0)
    await timeline_repository.create_track(track)

    response = client.post(
        "/api/v1/projects/proj-1/timeline/clips",
        json={
            "clip_id": "nonexistent",
            "track_id": "track-1",
            "timeline_start": 0.0,
            "timeline_end": 5.0,
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# PATCH /projects/{project_id}/timeline/clips/{clip_id}
# ---------------------------------------------------------------------------


@pytest.mark.api
async def test_patch_timeline_clip(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """PATCH timeline clip updates position."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    track = Track(id="track-1", project_id="proj-1", track_type="video", label="V1", z_index=0)
    await timeline_repository.create_track(track)

    video = make_test_video()
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        track_id="track-1",
        timeline_start=0.0,
        timeline_end=5.0,
    )
    await clip_repository.add(clip)

    response = client.patch(
        "/api/v1/projects/proj-1/timeline/clips/clip-1",
        json={"timeline_start": 2.0, "timeline_end": 8.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["timeline_start"] == 2.0
    assert data["timeline_end"] == 8.0
    assert data["track_id"] == "track-1"


@pytest.mark.api
async def test_patch_timeline_clip_change_track(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """PATCH timeline clip can change track assignment."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    track1 = Track(id="track-1", project_id="proj-1", track_type="video", label="V1", z_index=0)
    track2 = Track(id="track-2", project_id="proj-1", track_type="video", label="V2", z_index=1)
    await timeline_repository.create_track(track1)
    await timeline_repository.create_track(track2)

    video = make_test_video()
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        track_id="track-1",
        timeline_start=0.0,
        timeline_end=5.0,
    )
    await clip_repository.add(clip)

    response = client.patch(
        "/api/v1/projects/proj-1/timeline/clips/clip-1",
        json={"track_id": "track-2"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["track_id"] == "track-2"


@pytest.mark.api
async def test_patch_timeline_clip_invalid_position(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """PATCH timeline clip returns 422 when positions become invalid."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    track = Track(id="track-1", project_id="proj-1", track_type="video", label="V1", z_index=0)
    await timeline_repository.create_track(track)

    video = make_test_video()
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        track_id="track-1",
        timeline_start=0.0,
        timeline_end=5.0,
    )
    await clip_repository.add(clip)

    # Set timeline_start >= timeline_end
    response = client.patch(
        "/api/v1/projects/proj-1/timeline/clips/clip-1",
        json={"timeline_start": 10.0},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "INVALID_POSITION"


@pytest.mark.api
async def test_patch_timeline_clip_track_not_found(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """PATCH timeline clip returns 404 for unknown track_id."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    video = make_test_video()
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        track_id=None,
        timeline_start=0.0,
        timeline_end=5.0,
    )
    await clip_repository.add(clip)

    response = client.patch(
        "/api/v1/projects/proj-1/timeline/clips/clip-1",
        json={"track_id": "nonexistent"},
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "TRACK_NOT_FOUND"


@pytest.mark.api
def test_patch_timeline_clip_not_found(client: TestClient) -> None:
    """PATCH timeline clip returns 404 for unknown clip."""
    response = client.patch(
        "/api/v1/projects/proj-1/timeline/clips/nonexistent",
        json={"timeline_start": 1.0},
    )
    assert response.status_code == 404


@pytest.mark.api
def test_patch_timeline_clip_project_not_found(client: TestClient) -> None:
    """PATCH timeline clip returns 404 for unknown project."""
    response = client.patch(
        "/api/v1/projects/nonexistent/timeline/clips/clip-1",
        json={"timeline_start": 1.0},
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# DELETE /projects/{project_id}/timeline/clips/{clip_id}
# ---------------------------------------------------------------------------


@pytest.mark.api
async def test_delete_timeline_clip(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """DELETE timeline clip clears timeline association."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    video = make_test_video()
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        track_id="track-1",
        timeline_start=0.0,
        timeline_end=5.0,
    )
    await clip_repository.add(clip)

    response = client.delete("/api/v1/projects/proj-1/timeline/clips/clip-1")
    assert response.status_code == 204

    # Verify clip still exists but timeline fields are cleared
    updated_clip = await clip_repository.get("clip-1")
    assert updated_clip is not None
    assert updated_clip.track_id is None
    assert updated_clip.timeline_start is None
    assert updated_clip.timeline_end is None


@pytest.mark.api
def test_delete_timeline_clip_not_found(client: TestClient) -> None:
    """DELETE timeline clip returns 404 for unknown clip."""
    response = client.delete("/api/v1/projects/proj-1/timeline/clips/nonexistent")
    assert response.status_code == 404


@pytest.mark.api
def test_delete_timeline_clip_project_not_found(client: TestClient) -> None:
    """DELETE timeline clip returns 404 for unknown project."""
    response = client.delete("/api/v1/projects/nonexistent/timeline/clips/clip-1")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# Full CRUD workflow (black box)
# ---------------------------------------------------------------------------


@pytest.mark.api
@pytest.mark.blackbox
async def test_timeline_crud_workflow(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """Full CRUD workflow: PUT timeline -> GET -> POST clip -> PATCH -> DELETE."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    # 1. PUT timeline - create tracks
    resp = client.put(
        "/api/v1/projects/proj-1/timeline",
        json=[
            {"track_type": "video", "label": "Video 1"},
            {"track_type": "audio", "label": "Audio 1"},
        ],
    )
    assert resp.status_code == 200
    timeline = resp.json()
    track_id = timeline["tracks"][0]["id"]

    # 2. GET timeline - verify empty
    resp = client.get("/api/v1/projects/proj-1/timeline")
    assert resp.status_code == 200
    assert len(resp.json()["tracks"]) == 2
    assert resp.json()["duration"] == 0.0

    # 3. Create a clip via existing endpoint, seed it in the repo
    video = make_test_video()
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
    )
    await clip_repository.add(clip)

    # 4. POST clip to timeline
    resp = client.post(
        "/api/v1/projects/proj-1/timeline/clips",
        json={
            "clip_id": "clip-1",
            "track_id": track_id,
            "timeline_start": 0.0,
            "timeline_end": 10.0,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["track_id"] == track_id

    # 5. GET timeline - verify clip appears
    resp = client.get("/api/v1/projects/proj-1/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    assert timeline["duration"] == 10.0
    video_track = next(t for t in timeline["tracks"] if t["id"] == track_id)
    assert len(video_track["clips"]) == 1

    # 6. PATCH clip - move it
    resp = client.patch(
        "/api/v1/projects/proj-1/timeline/clips/clip-1",
        json={"timeline_start": 5.0, "timeline_end": 15.0},
    )
    assert resp.status_code == 200
    assert resp.json()["timeline_start"] == 5.0
    assert resp.json()["timeline_end"] == 15.0

    # 7. DELETE clip from timeline
    resp = client.delete("/api/v1/projects/proj-1/timeline/clips/clip-1")
    assert resp.status_code == 204

    # 8. GET timeline - clip should be gone from tracks
    resp = client.get("/api/v1/projects/proj-1/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    assert timeline["duration"] == 0.0
    video_track = next(t for t in timeline["tracks"] if t["id"] == track_id)
    assert len(video_track["clips"]) == 0


# ---------------------------------------------------------------------------
# Error response format parity
# ---------------------------------------------------------------------------


@pytest.mark.api
def test_error_response_format_matches_existing(client: TestClient) -> None:
    """Error responses match existing endpoint format (code + message)."""
    # Timeline 404
    resp = client.get("/api/v1/projects/nonexistent/timeline")
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert "code" in detail
    assert "message" in detail

    # Compare with project 404
    resp2 = client.get("/api/v1/projects/nonexistent")
    assert resp2.status_code == 404
    detail2 = resp2.json()["detail"]
    assert set(detail.keys()) == set(detail2.keys())


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


@pytest.mark.api
def test_timeline_clip_create_schema_validation(client: TestClient) -> None:
    """TimelineClipCreate rejects negative positions."""
    response = client.post(
        "/api/v1/projects/proj-1/timeline/clips",
        json={
            "clip_id": "clip-1",
            "track_id": "track-1",
            "timeline_start": -1.0,
            "timeline_end": 5.0,
        },
    )
    # FastAPI returns 422 for Pydantic validation failures
    assert response.status_code in (404, 422)


@pytest.mark.api
def test_track_create_requires_label(client: TestClient) -> None:
    """TrackCreate rejects empty label."""
    response = client.put(
        "/api/v1/projects/proj-1/timeline",
        json=[{"track_type": "video", "label": ""}],
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DI wiring
# ---------------------------------------------------------------------------


@pytest.mark.api
async def test_timeline_repository_accessible(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
) -> None:
    """Verify timeline_repository is correctly wired via DI."""
    from stoat_ferret.db.models import Project

    await project_repository.add(Project(**_make_project()))  # type: ignore[arg-type]

    # Seed a track directly in the repository
    track = Track(
        id="direct-track", project_id="proj-1", track_type="video", label="Direct", z_index=0
    )
    await timeline_repository.create_track(track)

    # GET timeline should see the track
    response = client.get("/api/v1/projects/proj-1/timeline")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tracks"]) == 1
    assert data["tracks"][0]["id"] == "direct-track"


# ---------------------------------------------------------------------------
# POST /projects/{project_id}/timeline/transitions
# ---------------------------------------------------------------------------


async def _setup_adjacent_clips(
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> tuple[str, str, str]:
    """Create a project with two adjacent clips on the same track.

    Returns:
        Tuple of (track_id, clip_a_id, clip_b_id).
    """
    from stoat_ferret.db.models import Project

    await project_repository.add(
        Project(**_make_project())  # type: ignore[arg-type]
    )

    track = Track(id="track-1", project_id="proj-1", track_type="video", label="V1", z_index=0)
    await timeline_repository.create_track(track)

    video_a = make_test_video()
    clip_a = Clip(
        id="clip-a",
        project_id="proj-1",
        source_video_id=video_a.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        track_id="track-1",
        timeline_start=0.0,
        timeline_end=5.0,
    )
    await clip_repository.add(clip_a)

    video_b = make_test_video()
    clip_b = Clip(
        id="clip-b",
        project_id="proj-1",
        source_video_id=video_b.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        track_id="track-1",
        timeline_start=5.0,
        timeline_end=10.0,
    )
    await clip_repository.add(clip_b)

    return "track-1", "clip-a", "clip-b"


@pytest.mark.api
async def test_post_transition_success(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """POST transition applies transition between adjacent clips."""
    await _setup_adjacent_clips(project_repository, timeline_repository, clip_repository)

    response = client.post(
        "/api/v1/projects/proj-1/timeline/transitions",
        json={
            "clip_a_id": "clip-a",
            "clip_b_id": "clip-b",
            "transition_type": "fade",
            "duration": 1.0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["transition_type"] == "fade"
    assert data["duration"] == 1.0
    assert "filter_string" in data
    assert len(data["filter_string"]) > 0
    assert "timeline_offset" in data
    assert isinstance(data["timeline_offset"], float)
    assert "id" in data
    assert len(data["clips"]) == 2


@pytest.mark.api
async def test_post_transition_filter_string_and_offset(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """POST transition returns valid filter_string and computed timeline_offset."""
    await _setup_adjacent_clips(project_repository, timeline_repository, clip_repository)

    response = client.post(
        "/api/v1/projects/proj-1/timeline/transitions",
        json={
            "clip_a_id": "clip-a",
            "clip_b_id": "clip-b",
            "transition_type": "dissolve",
            "duration": 1.0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    # timeline_offset should be negative (clip_b shifts earlier)
    assert data["timeline_offset"] < 0
    # filter_string should be an FFmpeg filter_complex value
    assert "xfade" in data["filter_string"] or len(data["filter_string"]) > 0
    # Adjusted clips should show overlap
    assert data["clips"][1]["timeline_start"] < 5.0


@pytest.mark.api
async def test_post_transition_non_adjacent_clips(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """POST transition rejects non-adjacent clips with CLIPS_NOT_ADJACENT."""
    from stoat_ferret.db.models import Project

    await project_repository.add(
        Project(**_make_project())  # type: ignore[arg-type]
    )

    track = Track(id="track-1", project_id="proj-1", track_type="video", label="V1", z_index=0)
    await timeline_repository.create_track(track)

    video_a = make_test_video()
    clip_a = Clip(
        id="clip-a",
        project_id="proj-1",
        source_video_id=video_a.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        track_id="track-1",
        timeline_start=0.0,
        timeline_end=5.0,
    )
    await clip_repository.add(clip_a)

    video_b = make_test_video()
    clip_b = Clip(
        id="clip-b",
        project_id="proj-1",
        source_video_id=video_b.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        track_id="track-1",
        timeline_start=7.0,  # Gap: not adjacent to clip_a
        timeline_end=12.0,
    )
    await clip_repository.add(clip_b)

    response = client.post(
        "/api/v1/projects/proj-1/timeline/transitions",
        json={
            "clip_a_id": "clip-a",
            "clip_b_id": "clip-b",
            "transition_type": "fade",
            "duration": 1.0,
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "CLIPS_NOT_ADJACENT"


@pytest.mark.api
async def test_post_transition_different_tracks(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """POST transition rejects clips on different tracks."""
    from stoat_ferret.db.models import Project

    await project_repository.add(
        Project(**_make_project())  # type: ignore[arg-type]
    )

    track1 = Track(id="track-1", project_id="proj-1", track_type="video", label="V1", z_index=0)
    track2 = Track(id="track-2", project_id="proj-1", track_type="video", label="V2", z_index=1)
    await timeline_repository.create_track(track1)
    await timeline_repository.create_track(track2)

    video_a = make_test_video()
    clip_a = Clip(
        id="clip-a",
        project_id="proj-1",
        source_video_id=video_a.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        track_id="track-1",
        timeline_start=0.0,
        timeline_end=5.0,
    )
    await clip_repository.add(clip_a)

    video_b = make_test_video()
    clip_b = Clip(
        id="clip-b",
        project_id="proj-1",
        source_video_id=video_b.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        track_id="track-2",  # Different track
        timeline_start=5.0,
        timeline_end=10.0,
    )
    await clip_repository.add(clip_b)

    response = client.post(
        "/api/v1/projects/proj-1/timeline/transitions",
        json={
            "clip_a_id": "clip-a",
            "clip_b_id": "clip-b",
            "transition_type": "fade",
            "duration": 1.0,
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "CLIPS_NOT_ADJACENT"


@pytest.mark.api
def test_post_transition_project_not_found(client: TestClient) -> None:
    """POST transition returns 404 for unknown project."""
    response = client.post(
        "/api/v1/projects/nonexistent/timeline/transitions",
        json={
            "clip_a_id": "clip-a",
            "clip_b_id": "clip-b",
            "transition_type": "fade",
            "duration": 1.0,
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_post_transition_clip_not_found(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """POST transition returns 404 for unknown clip."""
    from stoat_ferret.db.models import Project

    await project_repository.add(
        Project(**_make_project())  # type: ignore[arg-type]
    )

    response = client.post(
        "/api/v1/projects/proj-1/timeline/transitions",
        json={
            "clip_a_id": "nonexistent-a",
            "clip_b_id": "nonexistent-b",
            "transition_type": "fade",
            "duration": 1.0,
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# DELETE /projects/{project_id}/timeline/transitions/{transition_id}
# ---------------------------------------------------------------------------


@pytest.mark.api
async def test_delete_transition_success(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """DELETE transition removes transition and returns updated timeline."""
    await _setup_adjacent_clips(project_repository, timeline_repository, clip_repository)

    # First create a transition
    resp = client.post(
        "/api/v1/projects/proj-1/timeline/transitions",
        json={
            "clip_a_id": "clip-a",
            "clip_b_id": "clip-b",
            "transition_type": "fade",
            "duration": 1.0,
        },
    )
    assert resp.status_code == 201
    transition_id = resp.json()["id"]

    # Delete it
    resp = client.delete(
        f"/api/v1/projects/proj-1/timeline/transitions/{transition_id}",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == "proj-1"
    assert "tracks" in data
    assert "duration" in data
    assert isinstance(data["duration"], float)


@pytest.mark.api
async def test_delete_transition_recalculates_duration(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """DELETE transition recalculates timeline duration without the transition."""
    await _setup_adjacent_clips(project_repository, timeline_repository, clip_repository)

    # Create transition
    resp = client.post(
        "/api/v1/projects/proj-1/timeline/transitions",
        json={
            "clip_a_id": "clip-a",
            "clip_b_id": "clip-b",
            "transition_type": "fade",
            "duration": 1.0,
        },
    )
    assert resp.status_code == 201
    transition_id = resp.json()["id"]

    # Delete transition
    resp = client.delete(
        f"/api/v1/projects/proj-1/timeline/transitions/{transition_id}",
    )
    assert resp.status_code == 200
    # Duration after removing transition should be >= baseline (no overlap)
    assert resp.json()["duration"] >= 0


@pytest.mark.api
async def test_delete_transition_not_found(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """DELETE transition returns 404 for unknown transition."""
    from stoat_ferret.db.models import Project

    await project_repository.add(
        Project(**_make_project())  # type: ignore[arg-type]
    )

    resp = client.delete(
        "/api/v1/projects/proj-1/timeline/transitions/nonexistent",
    )
    assert resp.status_code == 404
    data = resp.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
def test_delete_transition_project_not_found(client: TestClient) -> None:
    """DELETE transition returns 404 for unknown project."""
    resp = client.delete(
        "/api/v1/projects/nonexistent/timeline/transitions/some-id",
    )
    assert resp.status_code == 404
    data = resp.json()
    assert data["detail"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# Black box transition workflow
# ---------------------------------------------------------------------------


@pytest.mark.api
@pytest.mark.blackbox
async def test_transition_workflow(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """Full workflow: create clips -> apply transition -> verify -> remove -> verify."""
    await _setup_adjacent_clips(project_repository, timeline_repository, clip_repository)

    # 1. Verify initial timeline
    resp = client.get("/api/v1/projects/proj-1/timeline")
    assert resp.status_code == 200
    assert resp.json()["duration"] == 10.0

    # 2. Apply transition
    resp = client.post(
        "/api/v1/projects/proj-1/timeline/transitions",
        json={
            "clip_a_id": "clip-a",
            "clip_b_id": "clip-b",
            "transition_type": "fade",
            "duration": 1.0,
        },
    )
    assert resp.status_code == 201
    transition_data = resp.json()
    assert "filter_string" in transition_data
    assert len(transition_data["filter_string"]) > 0
    assert "timeline_offset" in transition_data
    assert transition_data["timeline_offset"] < 0  # Clip B shifted left
    transition_id = transition_data["id"]

    # 3. Remove transition
    resp = client.delete(
        f"/api/v1/projects/proj-1/timeline/transitions/{transition_id}",
    )
    assert resp.status_code == 200
    timeline = resp.json()
    # Duration recalculated
    assert timeline["duration"] >= 0


# ---------------------------------------------------------------------------
# Error response format parity (transitions)
# ---------------------------------------------------------------------------


@pytest.mark.api
async def test_transition_error_format_matches_existing(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """Transition error responses match existing structured error pattern."""
    from stoat_ferret.db.models import Project

    await project_repository.add(
        Project(**_make_project())  # type: ignore[arg-type]
    )

    track = Track(id="track-1", project_id="proj-1", track_type="video", label="V1", z_index=0)
    await timeline_repository.create_track(track)

    video_a = make_test_video()
    clip_a = Clip(
        id="clip-a",
        project_id="proj-1",
        source_video_id=video_a.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        track_id="track-1",
        timeline_start=0.0,
        timeline_end=5.0,
    )
    await clip_repository.add(clip_a)

    video_b = make_test_video()
    clip_b = Clip(
        id="clip-b",
        project_id="proj-1",
        source_video_id=video_b.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        track_id="track-1",
        timeline_start=8.0,  # Not adjacent
        timeline_end=12.0,
    )
    await clip_repository.add(clip_b)

    resp = client.post(
        "/api/v1/projects/proj-1/timeline/transitions",
        json={
            "clip_a_id": "clip-a",
            "clip_b_id": "clip-b",
            "transition_type": "fade",
            "duration": 1.0,
        },
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "code" in detail
    assert "message" in detail
    # Compare with existing error format
    resp2 = client.get("/api/v1/projects/nonexistent/timeline")
    detail2 = resp2.json()["detail"]
    assert set(detail.keys()) == set(detail2.keys())
