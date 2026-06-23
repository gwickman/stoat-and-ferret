# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for AutomationEnvelope schema and automation dispatch (BL-420).

Covers envelope validation, compile_automation dispatch, filter_preview
population, and regression assurance for scalar-only paths.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from stoat_ferret.api.app import create_app
from stoat_ferret.api.schemas.effect import AutomationEnvelope, AutomationKeyframe
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from tests.factories import make_test_video

# ---------------------------------------------------------------------------
# Schema unit tests
# ---------------------------------------------------------------------------


def test_valid_envelope_accepted() -> None:
    """Valid envelope with monotonic keyframes parses correctly."""
    env = AutomationEnvelope.model_validate(
        {
            "default": 0.5,
            "keyframes": [
                {"t": 0.0, "value": 0.2, "curve": "linear"},
                {"t": 1.0, "value": 0.8, "curve": "ease_in_out"},
            ],
        }
    )
    assert env.default == 0.5
    assert len(env.keyframes) == 2
    assert env.keyframes[0].t == 0.0
    assert env.keyframes[1].curve == "ease_in_out"


def test_valid_envelope_default_curve() -> None:
    """Keyframe curve defaults to 'linear' when omitted."""
    env = AutomationEnvelope.model_validate(
        {
            "default": 1.0,
            "keyframes": [{"t": 0.0, "value": 0.5}],
        }
    )
    assert env.keyframes[0].curve == "linear"


def test_nonmonotonic_keyframes_rejected() -> None:
    """Non-monotonic keyframe times are rejected with a validation error."""
    with pytest.raises(ValidationError, match="strictly increasing"):
        AutomationEnvelope.model_validate(
            {
                "default": 0.5,
                "keyframes": [
                    {"t": 1.0, "value": 0.2},
                    {"t": 0.5, "value": 0.8},
                ],
            }
        )


def test_equal_keyframe_times_rejected() -> None:
    """Equal keyframe times (not strictly increasing) are rejected."""
    with pytest.raises(ValidationError, match="strictly increasing"):
        AutomationEnvelope.model_validate(
            {
                "default": 0.5,
                "keyframes": [
                    {"t": 1.0, "value": 0.2},
                    {"t": 1.0, "value": 0.8},
                ],
            }
        )


def test_empty_keyframes_rejected() -> None:
    """Empty keyframes list is rejected."""
    with pytest.raises(ValidationError, match="at least one keyframe required"):
        AutomationEnvelope.model_validate({"default": 0.5, "keyframes": []})


def test_unknown_curve_kind_rejected() -> None:
    """Unknown curve kind string is rejected via Literal validation."""
    with pytest.raises(ValidationError):
        AutomationKeyframe.model_validate({"t": 0.0, "value": 0.5, "curve": "invalid_curve"})


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


def _make_app_with_fixtures() -> tuple[
    object,
    AsyncInMemoryProjectRepository,
    AsyncInMemoryClipRepository,
    AsyncInMemoryVideoRepository,
]:
    """Create a test app with in-memory repositories."""
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()
    video_repo = AsyncInMemoryVideoRepository()
    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
    )
    return app, project_repo, clip_repo, video_repo


async def _seed_project_and_clip(
    project_repo: AsyncInMemoryProjectRepository,
    clip_repo: AsyncInMemoryClipRepository,
    video_repo: AsyncInMemoryVideoRepository,
) -> None:
    """Insert a project and clip for effect application tests."""
    now = datetime.now(timezone.utc)
    await project_repo.add(
        Project(
            id="proj-1",
            name="Test",
            output_width=1920,
            output_height=1080,
            output_fps=30,
            created_at=now,
            updated_at=now,
        )
    )
    video = make_test_video()
    await video_repo.add(video)
    await clip_repo.add(
        Clip(
            id="clip-1",
            project_id="proj-1",
            source_video_id=video.id,
            in_point=0,
            out_point=100,
            timeline_position=0,
            created_at=now,
            updated_at=now,
        )
    )


async def test_filter_preview_populated_for_envelope() -> None:
    """POST /effects with AutomationEnvelope returns non-null filter_preview."""
    app, project_repo, clip_repo, video_repo = _make_app_with_fixtures()
    await _seed_project_and_clip(project_repo, clip_repo, video_repo)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects/proj-1/clips/clip-1/effects",
            json={
                "effect_type": "volume",
                "parameters": {
                    "volume": {
                        "default": 0.8,
                        "keyframes": [
                            {"t": 0.0, "value": 0.2, "curve": "linear"},
                            {"t": 2.0, "value": 0.8, "curve": "linear"},
                        ],
                    }
                },
            },
        )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["filter_preview"] is not None
    assert "if(lt(t," in data["filter_preview"]
    assert data["filter_string"]  # scalar default still produced


async def test_filter_preview_none_for_scalar() -> None:
    """POST /effects with scalar parameter returns null filter_preview."""
    app, project_repo, clip_repo, video_repo = _make_app_with_fixtures()
    await _seed_project_and_clip(project_repo, clip_repo, video_repo)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects/proj-1/clips/clip-1/effects",
            json={
                "effect_type": "volume",
                "parameters": {"volume": 1.5},
            },
        )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["filter_preview"] is None


async def test_non_automatable_parameter_rejected() -> None:
    """Envelope on a non-automatable parameter is rejected with a 400 error."""
    app, project_repo, clip_repo, video_repo = _make_app_with_fixtures()
    await _seed_project_and_clip(project_repo, clip_repo, video_repo)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects/proj-1/clips/clip-1/effects",
            json={
                "effect_type": "volume",
                "parameters": {
                    "precision": {
                        "default": 0.5,
                        "keyframes": [{"t": 0.0, "value": 0.5}],
                    }
                },
            },
        )
    assert response.status_code == 400
    data = response.json()
    assert "not automatable" in data["detail"]["message"]


async def test_empty_keyframes_api_rejected() -> None:
    """Empty keyframes list via API returns 400."""
    app, project_repo, clip_repo, video_repo = _make_app_with_fixtures()
    await _seed_project_and_clip(project_repo, clip_repo, video_repo)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects/proj-1/clips/clip-1/effects",
            json={
                "effect_type": "volume",
                "parameters": {
                    "volume": {
                        "default": 0.8,
                        "keyframes": [],
                    }
                },
            },
        )
    assert response.status_code == 400
    data = response.json()
    assert "at least one keyframe required" in data["detail"]["message"]


async def test_nonmonotonic_keyframes_api_rejected() -> None:
    """Non-monotonic keyframe times via API return 400."""
    app, project_repo, clip_repo, video_repo = _make_app_with_fixtures()
    await _seed_project_and_clip(project_repo, clip_repo, video_repo)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects/proj-1/clips/clip-1/effects",
            json={
                "effect_type": "volume",
                "parameters": {
                    "volume": {
                        "default": 0.8,
                        "keyframes": [
                            {"t": 2.0, "value": 0.8},
                            {"t": 0.5, "value": 0.2},
                        ],
                    }
                },
            },
        )
    assert response.status_code == 400
    data = response.json()
    assert "strictly increasing" in data["detail"]["message"]


async def test_unknown_curve_api_rejected() -> None:
    """Unknown curve kind string via API returns 400."""
    app, project_repo, clip_repo, video_repo = _make_app_with_fixtures()
    await _seed_project_and_clip(project_repo, clip_repo, video_repo)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects/proj-1/clips/clip-1/effects",
            json={
                "effect_type": "volume",
                "parameters": {
                    "volume": {
                        "default": 0.8,
                        "keyframes": [{"t": 0.0, "value": 0.5, "curve": "bogus"}],
                    }
                },
            },
        )
    assert response.status_code == 400
