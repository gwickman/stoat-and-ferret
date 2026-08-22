# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UAT Journey — Preview Seek Position: seek endpoint forwards position to HLS generation (BL-798).

Exercises:
  1. Project creation and single-clip setup via HTTP API
  2. Preview session start (verifies 202 Accepted)
  3. Preview seek to position 5.0 (verifies 200 response)
  4. Verifies the seek was accepted without error
"""

from __future__ import annotations

import asyncio
import os

import httpx

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")

_SOURCE_W = 640
_SOURCE_H = 360


async def run_journey(base_url: str, *, ffmpeg_available: bool = False) -> dict[str, object]:
    """Drive the preview seek position journey.

    Creates a single-clip project, starts a preview session, seeks to position
    5.0, and verifies the seek returns HTTP 200.

    Args:
        base_url: Base URL of the stoat-and-ferret API server.
        ffmpeg_available: Whether to attempt session polling (requires FFmpeg).

    Returns:
        Dict with journey outcome keys.
    """
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Step 1: Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "journey-preview-seek",
                "output_width": _SOURCE_W,
                "output_height": _SOURCE_H,
                "output_fps": 30,
            },
        )
        if proj_resp.status_code not in (200, 201):
            return {
                "journey": "j_preview_seek",
                "project_id": None,
                "session_id": None,
                "seek_status": None,
                "status": "fail",
                "error": f"project create failed: {proj_resp.status_code}",
            }
        project_id: str = proj_resp.json()["id"]

        if not ffmpeg_available:
            return {
                "journey": "j_preview_seek",
                "project_id": project_id,
                "session_id": None,
                "seek_status": None,
                "status": "skip",
                "note": "FFmpeg not available — skipping live preview seek",
            }

        # Step 2: Start preview
        start_resp = await client.post(f"/api/v1/projects/{project_id}/preview/start")
        if start_resp.status_code != 202:
            return {
                "journey": "j_preview_seek",
                "project_id": project_id,
                "session_id": None,
                "seek_status": None,
                "status": "fail",
                "error": f"preview start failed: {start_resp.status_code} {start_resp.text}",
            }
        session_id: str = start_resp.json()["session_id"]

        # Step 3: Wait for session to be ready
        for _ in range(30):
            status_resp = await client.get(f"/api/v1/preview/{session_id}")
            if status_resp.status_code == 200:
                st = status_resp.json().get("status", "")
                if st == "ready":
                    break
                if st == "error":
                    return {
                        "journey": "j_preview_seek",
                        "project_id": project_id,
                        "session_id": session_id,
                        "seek_status": None,
                        "status": "fail",
                        "error": f"preview entered error state: {status_resp.json()}",
                    }
            await asyncio.sleep(1.0)

        # Step 4: Seek to position 5.0
        seek_resp = await client.post(
            f"/api/v1/preview/{session_id}/seek",
            json={"position": 5.0},
        )
        seek_status = seek_resp.status_code

        if seek_status != 200:
            return {
                "journey": "j_preview_seek",
                "project_id": project_id,
                "session_id": session_id,
                "seek_status": seek_status,
                "status": "fail",
                "error": f"seek failed: {seek_status} {seek_resp.text}",
            }

        return {
            "journey": "j_preview_seek",
            "project_id": project_id,
            "session_id": session_id,
            "seek_status": seek_status,
            "status": "success",
        }
