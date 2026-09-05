# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_generator_preview — generator clip preview (BL-851).

Verifies that a generator-only project (clip_type=generator) can start a preview
session that reaches ready with a valid HLS manifest and at least one .ts segment.

All tests are FFmpeg-gated (STOAT_TEST_FFMPEG=1).
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

pytestmark = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)


@pytest.mark.asyncio
async def test_generator_only_preview_starts_and_reaches_ready(tmp_path: Path) -> None:
    """Generator-only project starts preview (202), reaches ready, manifest has .ts segments.

    Verifies BL-851-AC-1 (FR-004-AC-1): start_preview handles generator clips,
    returning 202 and eventually status=ready with a valid manifest.
    """
    from httpx import ASGITransport, AsyncClient

    from stoat_ferret.api.app import create_app
    from stoat_ferret.api.websocket.manager import ConnectionManager
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
    from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
    from stoat_ferret.db.preview_repository import InMemoryPreviewRepository
    from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
    from stoat_ferret.ffmpeg.async_executor import RealAsyncFFmpegExecutor
    from stoat_ferret.preview.hls_generator import HLSGenerator
    from stoat_ferret.preview.manager import PreviewManager
    from tests.test_api.conftest import InMemoryAssetRepository

    # Build a real preview manager with real FFmpeg executor
    preview_repo = InMemoryPreviewRepository()
    executor = RealAsyncFFmpegExecutor()
    hls_generator = HLSGenerator(
        async_executor=executor,
        output_base_dir=str(tmp_path / "hls"),
    )

    # Mock ws_manager so broadcast calls are no-ops
    mock_ws = MagicMock(spec=ConnectionManager)
    mock_ws.broadcast = AsyncMock(return_value=None)

    preview_manager = PreviewManager(
        repository=preview_repo,
        generator=hls_generator,
        ws_manager=mock_ws,
    )

    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()
    video_repo = AsyncInMemoryVideoRepository()

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        preview_manager=preview_manager,
        asset_repository=InMemoryAssetRepository(),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "generator-preview-test",
                "output_width": 320,
                "output_height": 240,
                "output_fps": 25,
            },
        )
        assert proj_resp.status_code == 201, proj_resp.text
        project_id = proj_resp.json()["id"]

        # Create a generator clip (5-second red color via lavfi)
        clip_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "clip_type": "generator",
                "generator_params": {"lavfi_string": "color=c=red:s=320x240:r=25:d=5"},
                "in_point": 0,
                "out_point": 0,
                "timeline_position": 0,
                "timeline_start": 0.0,
                "timeline_end": 5.0,
            },
        )
        assert clip_resp.status_code == 201, clip_resp.text

        # Start preview
        start_resp = await client.post(f"/api/v1/projects/{project_id}/preview/start")
        assert start_resp.status_code == 202, start_resp.text
        session_id = start_resp.json()["session_id"]

        # Poll until ready (up to 30s)
        final_status = None
        for _ in range(60):
            status_resp = await client.get(f"/api/v1/preview/{session_id}")
            assert status_resp.status_code == 200, status_resp.text
            data = status_resp.json()
            if data["status"] in ("ready", "error"):
                final_status = data
                break
            await asyncio.sleep(0.5)

        assert final_status is not None, "Preview session never reached ready or error"
        assert final_status["status"] == "ready", (
            f"Preview ended in unexpected state: {final_status!r}"
        )
        assert final_status.get("manifest_url") is not None, (
            "manifest_url should be set when status=ready"
        )

        # Verify at least one .ts segment was generated
        hls_dirs = list((tmp_path / "hls").iterdir()) if (tmp_path / "hls").exists() else []
        ts_files = [
            f
            for hls_dir in hls_dirs
            if hls_dir.is_dir()
            for f in hls_dir.iterdir()
            if f.suffix == ".ts"
        ]
        assert len(ts_files) >= 1, (
            f"Expected at least one .ts segment, found {ts_files!r}"
        )
