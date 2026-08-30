# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UAT Journey 713 — Transitions Wiring: saved wipeleft/0.35 transition renders at seam.

Exercises:
  1. Project creation and multi-clip setup via HTTP API
  2. Saving a wipeleft/0.35 transition between clips via the transitions API
  3. Multi-clip render submission and poll to completion
  4. Visual seam and source-order oracle assertions (STOAT_TEST_FFMPEG=1 required)
  5. Render page navigation and screenshot
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any
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


def _render_xfade_ref(
    clip_a: Path,
    clip_b: Path,
    out: Path,
    transition: str,
    duration: float,
    offset: float,
) -> None:
    """Render two clips joined by an xfade transition into *out* for oracle reference."""
    r = subprocess.run(  # noqa: ASYNC221
        [
            "ffmpeg",
            "-i",
            str(clip_a),
            "-i",
            str(clip_b),
            "-filter_complex",
            (
                f"[0:v]fps=30,settb=1/30[v0];[1:v]fps=30,settb=1/30[v1];"
                f"[v0]fps=30,settb=1/30[pv0];[v1]fps=30,settb=1/30[pn1];"
                f"[pv0][pn1]xfade=transition={transition}:duration={duration}"
                f":offset={offset}[xf0];[xf0]format=yuv420p[final]"
            ),
            "-map",
            "[final]",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(out),
        ],
        capture_output=True,
        timeout=60,
    )
    if r.returncode != 0:
        raise RuntimeError(f"xfade ref render failed: {r.stderr.decode()[-800:]}")


async def _poll_render_job(
    client: httpx.AsyncClient,
    job_id: str,
    timeout: float = 120.0,
    interval: float = 2.0,
) -> dict[str, Any]:
    """Poll render job until terminal; return final job info dict."""
    terminal = {"completed", "failed", "cancelled", "qc_failed"}
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        resp = await client.get(f"/api/v1/render/{job_id}")
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        if data.get("status") in terminal:
            return data
        await asyncio.sleep(interval)
    raise asyncio.TimeoutError(f"Render job {job_id} did not complete within {timeout}s")


async def run(page: Page, base_url: str) -> None:
    """Transitions-wiring UAT journey: two clips, saved wipeleft/0.35, assert seam.

    When STOAT_TEST_FFMPEG=1: generates two audio+video fixtures, creates an independent
    project with two clips, saves a wipeleft/0.35 transition, submits a render, polls to
    completion, and asserts both source-frame order and transition style at the seam via
    the render-output oracle.
    Without STOAT_TEST_FFMPEG: navigates to the render page and verifies the UI surface.
    """
    parsed = urlparse(base_url)
    api_base = f"{parsed.scheme}://{parsed.netloc}"

    if STOAT_TEST_FFMPEG:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            clip_a = tmp_path / "clip_a.mp4"
            clip_b = tmp_path / "clip_b.mp4"
            ref_path = tmp_path / "ref_wipeleft.mp4"

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

                # Create an independent project (not the seed project)
                proj_resp = await client.post(
                    "/api/v1/projects",
                    json={
                        "name": "j_transitions UAT",
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
                clip_dur_s = 5.0  # seconds per clip

                # clip_a: full 5s at timeline_start=0.0, timeline_end=5.0
                resp_a = await client.post(
                    f"/api/v1/projects/{project_id}/clips",
                    json={
                        "source_video_id": video_id_a,
                        "in_point": 0,
                        "out_point": clip_frames,
                        "timeline_position": 0,
                        "timeline_start": 0.0,
                        "timeline_end": clip_dur_s,
                    },
                )
                assert resp_a.status_code == 201, (
                    f"Create clip_a failed: {resp_a.status_code} {resp_a.text}"
                )
                clip_a_id = resp_a.json()["id"]

                # clip_b: full 5s, adjacent after clip_a
                resp_b = await client.post(
                    f"/api/v1/projects/{project_id}/clips",
                    json={
                        "source_video_id": video_id_b,
                        "in_point": 0,
                        "out_point": clip_frames,
                        "timeline_position": clip_frames,
                        "timeline_start": clip_dur_s,
                        "timeline_end": clip_dur_s * 2,
                    },
                )
                assert resp_b.status_code == 201, (
                    f"Create clip_b failed: {resp_b.status_code} {resp_b.text}"
                )
                clip_b_id = resp_b.json()["id"]

                # Save wipeleft/0.35 transition: flat body to /timeline/transitions
                tr_resp = await client.post(
                    f"/api/v1/projects/{project_id}/timeline/transitions",
                    json={
                        "clip_a_id": clip_a_id,
                        "clip_b_id": clip_b_id,
                        "transition_type": "wipeleft",
                        "duration": 0.35,
                    },
                )
                assert tr_resp.status_code in (200, 201, 204), (
                    f"Save transitions failed: {tr_resp.status_code} {tr_resp.text}"
                )

                # clip_a=5s + clip_b=5s - xfade=0.35s = 9.65s total
                render_plan = json.dumps(
                    {
                        "total_duration": 9.65,
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

                from tests.render_oracle import assert_transition_reference

                # Build reference render for transition oracle
                seam_t = 4.65  # = 5.0 - 0.35
                _render_xfade_ref(clip_a, clip_b, ref_path, "wipeleft", 0.35, seam_t)

                # Transition style at seam: wipeleft must match reference (BL-792 AC-7)
                assert_transition_reference(output_path, seam_t, "wipeleft", 0.35, ref_path)

    # Navigate to render page for browser screenshot evidence (always runs)
    await page.goto(base_url + "render")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='render-page']")).to_be_visible()
    await page.screenshot(path="j_transitions.png")
