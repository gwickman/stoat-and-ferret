# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UAT Journey — Audio Effect Dispatch: single-clip render with volume=2.0 audio effect.

Exercises:
  1. Project creation and single-clip setup via HTTP API with a volume audio effect
  2. Render submission and poll to completion
  3. Audio RMS oracle assertion (STOAT_TEST_FFMPEG=1 required for full oracle path)
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
    assert_audio_rms_changed,
    assert_stream_inventory,
    measure_audio_rms_db,
)

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")


def _gen_lavfi_audio_video(path: Path, duration: int = 3, timeout: int = 60) -> None:
    """Generate a test video with stereo audio using the amerge pattern."""
    r = subprocess.run(  # noqa: ASYNC221
        [
            "ffmpeg",
            "-y",
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
            str(path),
        ],
        capture_output=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(
            f"ffmpeg lavfi audio+video generation failed: {r.stderr.decode()[-800:]}"
        )


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
    """Audio effect dispatch UAT journey: single-clip render with volume=2.0 audio effect.

    When STOAT_TEST_FFMPEG=1: generates a stereo audio+video fixture, scans it, creates a
    project with a volume=2.0 audio effect, renders baseline (no effect) and with-effect, then
    asserts audio RMS changed by >= 5 dB.
    Without STOAT_TEST_FFMPEG: navigates to the render page and verifies the UI surface.
    """
    parsed = urlparse(base_url)
    api_base = f"{parsed.scheme}://{parsed.netloc}"

    if STOAT_TEST_FFMPEG:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            src = tmp_path / "audio_video_3s.mp4"

            _gen_lavfi_audio_video(src, duration=3)

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

                render_plan_base = json.dumps(
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

                # --- Baseline render: no effect, measure RMS ---
                proj_base = await client.post(
                    "/api/v1/projects",
                    json={
                        "name": "j_audio_effect UAT baseline",
                        "output_width": 320,
                        "output_height": 240,
                        "output_fps": 30,
                    },
                )
                assert proj_base.status_code == 201
                base_proj_id = proj_base.json()["id"]
                resp_base_clip = await client.post(
                    f"/api/v1/projects/{base_proj_id}/clips",
                    json={
                        "source_video_id": video_id,
                        "in_point": 0,
                        "out_point": 90,
                        "timeline_position": 0,
                    },
                )
                assert resp_base_clip.status_code == 201
                render_base_resp = await client.post(
                    "/api/v1/render",
                    json={"project_id": base_proj_id, "render_plan": render_plan_base},
                )
                assert render_base_resp.status_code == 201
                base_job = await _poll_render_job(client, render_base_resp.json()["id"])
                assert base_job["status"] == "completed", (
                    f"Baseline render ended '{base_job['status']}'"
                )
                base_output = Path(base_job["output_path"])
                assert base_output.exists()
                await assert_stream_inventory(base_output, video=True, audio=True)
                baseline_rms_db = await measure_audio_rms_db(base_output)

                # --- Effect render: volume=2.0, measure RMS ---
                proj_eff = await client.post(
                    "/api/v1/projects",
                    json={
                        "name": "j_audio_effect UAT with-effect",
                        "output_width": 320,
                        "output_height": 240,
                        "output_fps": 30,
                    },
                )
                assert proj_eff.status_code == 201
                eff_proj_id = proj_eff.json()["id"]
                resp_eff_clip = await client.post(
                    f"/api/v1/projects/{eff_proj_id}/clips",
                    json={
                        "source_video_id": video_id,
                        "in_point": 0,
                        "out_point": 90,
                        "timeline_position": 0,
                    },
                )
                assert resp_eff_clip.status_code == 201
                eff_clip_id = resp_eff_clip.json()["id"]
                eff_resp = await client.post(
                    f"/api/v1/projects/{eff_proj_id}/clips/{eff_clip_id}/effects",
                    json={"effect_type": "volume", "parameters": {"volume": 2.0}},
                )
                assert eff_resp.status_code in (200, 201), (
                    f"Add effect failed: {eff_resp.status_code} {eff_resp.text}"
                )
                render_eff_resp = await client.post(
                    "/api/v1/render",
                    json={"project_id": eff_proj_id, "render_plan": render_plan_base},
                )
                assert render_eff_resp.status_code == 201
                eff_job = await _poll_render_job(client, render_eff_resp.json()["id"])
                assert eff_job["status"] == "completed", (
                    f"Effect render ended '{eff_job['status']}'"
                )
                eff_output = Path(eff_job["output_path"])
                assert eff_output.exists()
                await assert_stream_inventory(eff_output, video=True, audio=True)
                effect_rms_db = await measure_audio_rms_db(eff_output)

                # volume=2.0 ≈ +6 dB; threshold=5 dB
                assert_audio_rms_changed(effect_rms_db, baseline_rms_db, min_delta_db=5.0)

    # Navigate to render page for browser screenshot evidence (always runs)
    await page.goto(base_url + "render")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='render-page']")).to_be_visible()
    await page.screenshot(path="j_audio_effect.png")
