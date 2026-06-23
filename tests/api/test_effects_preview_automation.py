# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Behavioral tests for preview endpoint automation envelope support (BL-482)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository

_VOLUME_ENVELOPE = {
    "keyframes": [
        {"t": 0.0, "value": 1.0, "curve": "linear"},
        {"t": 5.0, "value": 0.5, "curve": "linear"},
    ],
    "default": 1.0,
}


@pytest.fixture
def client() -> TestClient:
    """Minimal app with in-memory repositories for preview endpoint tests."""
    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
    )
    return TestClient(app)


@pytest.mark.api
def test_preview_accepts_volume_automation_envelope(client: TestClient) -> None:
    """POST /effects/preview with volume automation envelope returns 200 (BL-482-AC-1)."""
    response = client.post(
        "/api/v1/effects/preview",
        json={"effect_type": "volume", "parameters": {"volume": _VOLUME_ENVELOPE}},
    )
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.json()}"
    )


@pytest.mark.api
def test_preview_returns_filter_string_with_eval_frame(client: TestClient) -> None:
    """POST /effects/preview with volume automation returns filter_string with :eval=frame.

    BL-482-AC-2.
    """
    response = client.post(
        "/api/v1/effects/preview",
        json={"effect_type": "volume", "parameters": {"volume": _VOLUME_ENVELOPE}},
    )
    assert response.status_code == 200
    data = response.json()
    assert "filter_string" in data, f"Response missing filter_string: {data}"
    assert "eval=frame" in data["filter_string"], (
        f"Expected 'eval=frame' in filter_string: {data['filter_string']}"
    )


@pytest.mark.api
def test_preview_non_automatable_parameter_with_envelope_returns_400(client: TestClient) -> None:
    """POST /effects/preview with envelope on non-automatable param returns 400 (BL-482-AC-3)."""
    response = client.post(
        "/api/v1/effects/preview",
        json={
            "effect_type": "speed_control",
            "parameters": {
                "factor": {
                    "keyframes": [
                        {"t": 0.0, "value": 1.0, "curve": "linear"},
                        {"t": 5.0, "value": 2.0, "curve": "linear"},
                    ],
                    "default": 1.0,
                }
            },
        },
    )
    assert response.status_code == 400, (
        f"Expected 400 for non-automatable param, got {response.status_code}: {response.json()}"
    )
    detail = response.json()["detail"]
    assert detail["code"] == "INVALID_EFFECT_PARAMS"


@pytest.mark.api
def test_thumbnail_preview_accepts_volume_automation_envelope(tmp_path: Path) -> None:
    """POST /effects/preview/thumbnail with volume automation envelope returns 200 (BL-482-AC-1)."""
    from stoat_ferret.ffmpeg.executor import ExecutionResult

    class FakeExecutor:
        """FFmpeg executor that writes a fake JPEG for testing."""

        def run(
            self,
            args: list[str],
            *,
            stdin: bytes | None = None,
            timeout: float | None = None,
        ) -> ExecutionResult:
            output_path = args[-1]
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(b"\xff\xd8\xff\xe0fake_jpeg")
            return ExecutionResult(
                returncode=0,
                stdout=b"",
                stderr=b"",
                command=["ffmpeg", *args],
                duration_seconds=0.1,
            )

    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        ffmpeg_executor=FakeExecutor(),
    )
    # Create a fake video file so the path-exists check passes
    fake_video = tmp_path / "fake_video.mp4"
    fake_video.write_bytes(b"fake_mp4_data")

    with TestClient(app) as c:
        response = c.post(
            "/api/v1/effects/preview/thumbnail",
            json={
                "effect_type": "volume",
                "video_path": str(fake_video),
                "parameters": {"volume": _VOLUME_ENVELOPE},
            },
        )
    ct = response.headers.get("content-type", "")
    body = response.json() if "application/json" in ct else "(binary)"
    assert response.status_code == 200, (
        f"Expected 200 (thumbnail with automation envelope), got {response.status_code}: {body}"
    )
