# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UAT Journey — Crop Effect: single-clip render with crop effect (BL-796).

Exercises:
  1. Project creation and single-clip setup via HTTP API with a crop effect
  2. Render submission and poll to completion
  3. Output dimension assertion via ffprobe (STOAT_TEST_FFMPEG=1 required for full oracle path)
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

_CROP_W = 640
_CROP_H = 360
_CROP_X = 100
_CROP_Y = 50
_SOURCE_W = 1280
_SOURCE_H = 720


def _gen_video_only_fixture(path: Path, duration: int = 3, timeout: int = 60) -> None:
    """Generate a video-only test fixture."""
    r = subprocess.run(  # noqa: ASYNC221
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size={_SOURCE_W}x{_SOURCE_H}:rate=30:duration={duration}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        capture_output=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg fixture generation failed: {r.stderr.decode()[-800:]}")


def _ffprobe_dimensions(path: Path) -> tuple[int, int]:
    """Return (width, height) of the first video stream."""
    r = subprocess.run(  # noqa: ASYNC221
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "v:0",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if r.returncode != 0:
        raise AssertionError(f"ffprobe failed: {r.stderr[-400:]}")
    data = json.loads(r.stdout)
    streams = data.get("streams", [])
    if not streams:
        raise AssertionError(f"No video stream found in {path}")
    return int(streams[0]["width"]), int(streams[0]["height"])


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
    """Crop effect UAT journey: single-clip render with crop=640:360:100:50.

    When STOAT_TEST_FFMPEG=1: generates a 1280x720 fixture, creates a project with a
    crop effect, renders it, then asserts output dimensions are 640x360 via ffprobe.
    Without STOAT_TEST_FFMPEG: navigates to the render page and verifies the UI surface.
    """
    parsed = urlparse(base_url)
    api_base = f"{parsed.scheme}://{parsed.netloc}"

    if STOAT_TEST_FFMPEG:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            src = tmp_path / "video_1280x720_3s.mp4"

            _gen_video_only_fixture(src, duration=3)

            async with httpx.AsyncClient(base_url=api_base, timeout=60.0) as client:
                # Scan source video into the library
                scan_resp = await client.post(
                    "/api/v1/videos/scan",
                    json={"path": str(tmp_path), "recursive": False},
                )
                assert scan_resp.status_code == 202, (
                    f"Scan failed: {scan_resp.status_code} {scan_resp.text}"
                )
                scan_job_id = scan_resp.json()["job_id"]

                deadline = asyncio.get_running_loop().time() + 30.0
                while asyncio.get_running_loop().time() < deadline:
                    sj = await client.get(f"/api/v1/jobs/{scan_job_id}")
                    if sj.json()["status"].lower() in {"completed", "failed"}:
                        break
                    await asyncio.sleep(0.5)

                vids_resp = await client.get("/api/v1/videos?limit=100")
                vids_resp.raise_for_status()
                src_name = src.name
                video_id = next(
                    v["id"] for v in vids_resp.json()["videos"] if v["filename"] == src_name
                )

                render_plan = json.dumps(
                    {
                        "total_duration": 3.0,
                        "settings": {
                            "codec": "libx264",
                            "fps": 30.0,
                            "width": _SOURCE_W,
                            "height": _SOURCE_H,
                            "quality_preset": "standard",
                        },
                    }
                )

                proj_resp = await client.post(
                    "/api/v1/projects",
                    json={
                        "name": "j_crop UAT crop-effect",
                        "output_width": _SOURCE_W,
                        "output_height": _SOURCE_H,
                        "output_fps": 30,
                    },
                )
                assert proj_resp.status_code == 201
                proj_id = proj_resp.json()["id"]

                clip_resp = await client.post(
                    f"/api/v1/projects/{proj_id}/clips",
                    json={
                        "source_video_id": video_id,
                        "in_point": 0,
                        "out_point": 90,
                        "timeline_position": 0,
                    },
                )
                assert clip_resp.status_code == 201
                clip_id: str = clip_resp.json()["id"]
                effect_resp = await client.post(
                    f"/api/v1/projects/{proj_id}/clips/{clip_id}/effects",
                    json={
                        "effect_type": "crop",
                        "parameters": {
                            "width": _CROP_W,
                            "height": _CROP_H,
                            "x": _CROP_X,
                            "y": _CROP_Y,
                        },
                    },
                )
                assert effect_resp.status_code == 201

                render_resp = await client.post(
                    "/api/v1/render",
                    json={"project_id": proj_id, "render_plan": render_plan},
                )
                assert render_resp.status_code == 201
                job = await _poll_render_job(client, render_resp.json()["id"])
                assert job["status"] == "completed", f"Crop render ended '{job['status']}'"

                out_path = Path(job["output_path"])
                assert out_path.exists()
                out_w, out_h = _ffprobe_dimensions(out_path)
                assert out_w == _CROP_W, f"Expected width={_CROP_W}, got {out_w}"
                assert out_h == _CROP_H, f"Expected height={_CROP_H}, got {out_h}"

    # Navigate to render page for browser screenshot evidence (always runs)
    await page.goto(base_url + "render")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='render-page']")).to_be_visible()
    await page.screenshot(path="j_crop.png")
