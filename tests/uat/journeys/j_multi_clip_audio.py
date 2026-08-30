# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UAT Journey 712 — Multi-Clip Audio: multi-clip render with audio-capable clips.

Exercises:
  1. Project creation and multi-clip setup via HTTP API
  2. Multi-clip render submission and poll to completion
  3. Audio stream presence and A/V alignment oracle assertion (STOAT_TEST_FFMPEG=1 required)
  4. Render page navigation and screenshot
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from playwright.async_api import Page, expect

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")


def _gen_audio_video_fixture(path: Path, duration: int = 5, timeout: int = 60) -> None:
    """Generate an audio+video MP4 using the amerge stereo pattern from AGENTS.md."""
    r = subprocess.run(  # noqa: ASYNC221
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=320x240:rate=30:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=880:duration={duration}",
            "-filter_complex",
            "amerge=inputs=2",
            "-ac",
            "2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-y",
            str(path),
        ],
        capture_output=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg fixture generation failed: {r.stderr.decode()[-800:]}")


async def _poll_render_job(
    client: httpx.AsyncClient,
    job_id: str,
    timeout: float = 120.0,
    interval: float = 2.0,
) -> dict:
    """Poll render job until terminal; return final job info dict."""
    terminal = {"completed", "failed", "cancelled", "qc_failed"}
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        resp = await client.get(f"/api/v1/render/{job_id}")
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") in terminal:
            return data  # type: ignore[return-value]
        await asyncio.sleep(interval)
    raise asyncio.TimeoutError(f"Render job {job_id} did not complete within {timeout}s")


async def run(page: Page, base_url: str) -> None:
    """Multi-clip audio UAT journey: two audio-capable clips, render, assert audio present.

    When STOAT_TEST_FFMPEG=1: generates two audio+video fixtures using the amerge stereo
    pattern, creates a two-clip project via the HTTP API, submits a render, polls to
    completion, and asserts audio stream presence and A/V alignment via the render-output
    oracle.
    Without STOAT_TEST_FFMPEG: navigates to the render page and verifies the UI surface.
    """
    parsed = urlparse(base_url)
    api_base = f"{parsed.scheme}://{parsed.netloc}"

    if STOAT_TEST_FFMPEG:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            clip_a = tmp_path / "clip_a.mp4"
            clip_b = tmp_path / "clip_b.mp4"

            _gen_audio_video_fixture(clip_a, duration=5)
            _gen_audio_video_fixture(clip_b, duration=5)

            async with httpx.AsyncClient(base_url=api_base, timeout=60.0) as client:
                # Scan source directory into the library
                scan_resp = await client.post(
                    "/api/v1/videos/scan",
                    json={"path": str(tmp_path), "recursive": False},
                )
                assert scan_resp.status_code == 202, (
                    f"Scan failed: {scan_resp.status_code} {scan_resp.text}"
                )
                scan_job_id = scan_resp.json()["job_id"]

                # Poll scan job to completion
                deadline = asyncio.get_running_loop().time() + 30.0
                while asyncio.get_running_loop().time() < deadline:
                    sj = await client.get(f"/api/v1/jobs/{scan_job_id}")
                    if sj.json()["status"].lower() in {"completed", "failed"}:
                        break
                    await asyncio.sleep(0.5)

                # Resolve video IDs for the scanned files
                vids_resp = await client.get("/api/v1/videos?limit=100")
                vids_resp.raise_for_status()
                videos = vids_resp.json()["videos"]
                video_id_a = next(v["id"] for v in videos if v["filename"] == clip_a.name)
                video_id_b = next(v["id"] for v in videos if v["filename"] == clip_b.name)

                # Create project
                proj_resp = await client.post(
                    "/api/v1/projects",
                    json={
                        "name": "j_multi_clip_audio UAT",
                        "output_width": 320,
                        "output_height": 240,
                        "output_fps": 30,
                    },
                )
                assert proj_resp.status_code == 201, (
                    f"Create project failed: {proj_resp.status_code} {proj_resp.text}"
                )
                project_id = proj_resp.json()["id"]

                fps = 30
                clip_frames = 5 * fps  # 150 frames = 5s

                # clip_a: full 5s at timeline position 0
                resp_a = await client.post(
                    f"/api/v1/projects/{project_id}/clips",
                    json={
                        "source_video_id": video_id_a,
                        "in_point": 0,
                        "out_point": clip_frames,
                        "timeline_position": 0,
                    },
                )
                assert resp_a.status_code == 201, (
                    f"Create clip_a failed: {resp_a.status_code} {resp_a.text}"
                )

                # clip_b: full 5s, positioned after clip_a
                resp_b = await client.post(
                    f"/api/v1/projects/{project_id}/clips",
                    json={
                        "source_video_id": video_id_b,
                        "in_point": 0,
                        "out_point": clip_frames,
                        "timeline_position": clip_frames,
                    },
                )
                assert resp_b.status_code == 201, (
                    f"Create clip_b failed: {resp_b.status_code} {resp_b.text}"
                )

                # clip_a=5s + clip_b=5s - xfade=1s = 9s total
                render_plan = json.dumps(
                    {
                        "total_duration": 9.0,
                        "settings": {
                            "codec": "libx264",
                            "fps": 30.0,
                            "width": 320,
                            "height": 240,
                            "quality_preset": "standard",
                        },
                    }
                )
                render_resp = await client.post(
                    "/api/v1/render",
                    json={"project_id": project_id, "render_plan": render_plan},
                )
                assert render_resp.status_code == 201, (
                    f"Render submit failed: {render_resp.status_code} {render_resp.text}"
                )
                job_id = render_resp.json()["id"]

                job_info = await _poll_render_job(client, job_id)
                assert job_info["status"] == "completed", (
                    f"Render ended with status '{job_info['status']}' — check server logs"
                )

                output_path = Path(job_info["output_path"])
                assert output_path.exists(), f"Render output not found at {output_path}"

                from tests.render_oracle import (
                    assert_av_duration_alignment,
                    assert_stream_inventory,
                )

                await assert_stream_inventory(output_path, video=True, audio=True)
                await assert_av_duration_alignment(output_path)

    # Navigate to render page for browser screenshot evidence (always runs)
    await page.goto(base_url + "render")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='render-page']")).to_be_visible()
    await page.screenshot(path="j_multi_clip_audio.png")
