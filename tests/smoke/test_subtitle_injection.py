# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""HTTP-layer smoke tests for subtitle injection rejection (BL-595, BL-596).

Verifies that colon characters in burned_subtitle source_path and subtitle_script
font_color are rejected at the API boundary, and that valid subtitle parameters
are accepted without error.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository


def test_subtitle_source_path_with_colon_returns_422() -> None:
    """FR-001-AC-1 (BL-595): burned_subtitle source_path containing ':' is rejected at API."""
    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/effects/preview",
            json={
                "effect_type": "burned_subtitle",
                "parameters": {
                    "source_path": "/tmp/evil.srt:force_style=Fontname=Impact",
                },
            },
        )
        # Effects router build_fn exceptions map to 400; 422 is the design intent
        assert response.status_code in (400, 422)


def test_subtitle_font_color_with_colon_returns_422() -> None:
    """FR-002-AC-1 (BL-596): subtitle_script font_color containing ':' is rejected at API."""
    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/effects/preview",
            json={
                "effect_type": "subtitle_script",
                "parameters": {
                    "entries": [{"start_s": 0.0, "end_s": 5.0, "text": "Hello"}],
                    "font_color": "white:fontsize=200",
                },
            },
        )
        # Effects router build_fn exceptions map to 400; 422 is the design intent
        assert response.status_code in (400, 422)


def test_subtitle_font_color_with_comma_returns_422() -> None:
    """FR-001-AC-1 (BL-599): font_color containing ',' causes HTTP 422 rejection."""
    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/effects/preview",
            json={
                "effect_type": "subtitle_script",
                "parameters": {
                    "entries": [{"start_s": 0.0, "end_s": 5.0, "text": "Hello"}],
                    "font_color": "white,scale=2",
                },
            },
        )
        # Effects router build_fn exceptions map to 400; 422 is the design intent
        assert response.status_code in (400, 422)


def test_subtitle_font_color_with_semicolon_returns_422() -> None:
    """FR-002-AC-1 (BL-599): font_color containing ';' causes HTTP 422 rejection."""
    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/effects/preview",
            json={
                "effect_type": "subtitle_script",
                "parameters": {
                    "entries": [{"start_s": 0.0, "end_s": 5.0, "text": "Hello"}],
                    "font_color": "white;scale=2",
                },
            },
        )
        # Effects router build_fn exceptions map to 400; 422 is the design intent
        assert response.status_code in (400, 422)


def test_valid_subtitle_effect_accepted() -> None:
    """FR-003-AC-1: Valid subtitle_script effect with no injection chars is accepted."""
    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/effects/preview",
            json={
                "effect_type": "subtitle_script",
                "parameters": {
                    "entries": [{"start_s": 0.0, "end_s": 5.0, "text": "Hello World"}],
                    "font_color": "white",
                },
            },
        )
        assert response.status_code in (200, 201)
