# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UAT Journey — In-Point Trim: multi-clip render with non-zero in_point, assert frame identity.

Exercises:
  1. Project creation and multi-clip setup via HTTP API
  2. Non-zero in_point clip render submission and poll to completion
  3. Frame identity oracle assertion (STOAT_TEST_FFMPEG=1 required for full oracle path)
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

from tests.render_oracle import (
    assert_inpoint_identity,
    assert_stream_inventory,
)

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")


def _gen_lavfi_video(path: Path, lavfi_expr: str, timeout: int = 60) -> None:
    """Generate a test video from a lavfi source expression."""
    r = subprocess.run(  # noqa: ASYNC221
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            lavfi_expr,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(path),
        ],
        capture_output=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg lavfi generation failed: {r.stderr.decode()[-800:]}")


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
    """In-point trim UAT journey: multi-clip render with non-zero in_point.

    When STOAT_TEST_FFMPEG=1: generates a testsrc2 source, scans it, creates a two-clip
    project where clip_b has in_point=90 (3s offset), renders, and asserts frame identity.
    Without STOAT_TEST_FFMPEG: navigates to the render page and verifies the UI surface.
    """
    parsed = urlparse(base_url)
    api_base = f"{parsed.scheme}://{parsed.netloc}"

    if STOAT_TEST_FFMPEG:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            src = tmp_path / "testsrc2_10s.mp4"

            # Generate time-varying source (not solid color) so SSIM is meaningful
            _gen_lavfi_video(src, "testsrc2=size=320x240:rate=30:duration=10")

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

                # Poll scan job to completion
                deadline = asyncio.get_running_loop().time() + 30.0
                while asyncio.get_running_loop().time() < deadline:
                    sj = await client.get(f"/api/v1/jobs/{scan_job_id}")
                    if sj.json()["status"].lower() in {"completed", "failed"}:
                        break
                    await asyncio.sleep(0.5)

                # Resolve video ID for the scanned file
                vids_resp = await client.get("/api/v1/videos?limit=100")
                vids_resp.raise_for_status()
                src_name = src.name
                video_id = next(
                    v["id"] for v in vids_resp.json()["videos"] if v["filename"] == src_name
                )

                # Create project
                proj_resp = await client.post(
                    "/api/v1/projects",
                    json={
                        "name": "j_in_point_trim UAT",
                        "output_width": 320,
                        "output_height": 240,
                        "output_fps": 30,
                    },
                )
                assert proj_resp.status_code == 201, (
                    f"Create project failed: {proj_resp.status_code} {proj_resp.text}"
                )
                project_id = proj_resp.json()["id"]

                # clip_a: in_point=0, out_point=60 (2s at 30fps) — zero inpoint
                resp_a = await client.post(
                    f"/api/v1/projects/{project_id}/clips",
                    json={
                        "source_video_id": video_id,
                        "in_point": 0,
                        "out_point": 60,
                        "timeline_position": 0,
                    },
                )
                assert resp_a.status_code == 201, (
                    f"Create clip_a failed: {resp_a.status_code} {resp_a.text}"
                )

                # clip_b: in_point=90, out_point=150 (2s at 30fps, 3s source offset) — non-zero
                resp_b = await client.post(
                    f"/api/v1/projects/{project_id}/clips",
                    json={
                        "source_video_id": video_id,
                        "in_point": 90,
                        "out_point": 150,
                        "timeline_position": 60,
                    },
                )
                assert resp_b.status_code == 201, (
                    f"Create clip_b failed: {resp_b.status_code} {resp_b.text}"
                )

                # clip_a=2s + clip_b=2s - xfade=1s = 3s total
                render_plan = json.dumps(
                    {
                        "total_duration": 3.0,
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

                # clip_b starts at output_t ≈ 2s - 1s xfade = 1.0s; midpoint of clip_b ≈ 2.0s
                # source_start=3.0s (in_point=90/30), source_end=5.0s (out_point=150/30)
                assert_inpoint_identity(
                    output_path,
                    output_t=2.0,
                    source=src,
                    source_start=3.0,
                    source_end=5.0,
                    threshold=0.9,
                )
                await assert_stream_inventory(output_path, video=True, audio=False)

    # Navigate to render page for browser screenshot evidence (always runs)
    await page.goto(base_url + "render")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='render-page']")).to_be_visible()
    await page.screenshot(path="j_in_point_trim.png")
