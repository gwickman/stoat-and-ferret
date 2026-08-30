# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UAT Journey 721 — Split Preserve: clip split retains effects with migration_report.

Exercises:
  1. Project creation via HTTP API
  2. Generator clip creation and effect application via API
  3. Split with copy_full_stack policy via POST /clips/{id}/split
  4. Assertion that both children carry parent effects and migration_report entries
  5. Assertion that split frame boundaries are correct
"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
from playwright.async_api import Page


async def run(page: Page, base_url: str) -> None:
    """J714: Split a clip with effects, assert children retain effects and migration_report.

    Creates a project and a generator clip, applies a reverse effect, splits with
    copy_full_stack policy, and verifies both children carry the full effect stack
    plus a migration_report entry per effect with disposition=copied.
    """
    parsed = urlparse(base_url)
    api_base = f"{parsed.scheme}://{parsed.netloc}"

    async with httpx.AsyncClient(base_url=api_base, timeout=30.0) as client:
        # Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "J714 Split Preserve",
                "output_width": 1920,
                "output_height": 1080,
                "output_fps": 30,
            },
        )
        assert proj_resp.status_code == 201, (
            f"Project creation failed: {proj_resp.status_code} {proj_resp.text}"
        )
        project_id = proj_resp.json()["id"]

        # Create generator clip (no video source required)
        clip_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "clip_type": "generator",
                "generator_params": {"type": "tone", "frequency": 440.0, "duration": 4.0},
                "in_point": 0,
                "out_point": 120,
                "timeline_position": 0,
                "timeline_start": 0.0,
                "timeline_end": 4.0,
            },
        )
        assert clip_resp.status_code == 201, (
            f"Clip creation failed: {clip_resp.status_code} {clip_resp.text}"
        )
        clip_id = clip_resp.json()["id"]

        # Apply reverse effect
        fx_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
            json={"effect_type": "reverse", "parameters": {}},
        )
        assert fx_resp.status_code == 201, (
            f"Effect apply failed: {fx_resp.status_code} {fx_resp.text}"
        )

        # Split at frame 60 with default policy (copy_full_stack)
        split_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/split",
            json={"split_frame": 60},
        )
        assert split_resp.status_code == 200, (
            f"Split failed: {split_resp.status_code} {split_resp.text}"
        )
        data = split_resp.json()

        # Both children must carry parent's full effect stack
        assert data["clip_a"]["effects"], "clip_a has no effects after split"
        assert data["clip_b"]["effects"], "clip_b has no effects after split"
        assert data["clip_a"]["effects"][0]["effect_type"] == "reverse", (
            f"clip_a effect_type mismatch: {data['clip_a']['effects']}"
        )
        assert data["clip_b"]["effects"][0]["effect_type"] == "reverse", (
            f"clip_b effect_type mismatch: {data['clip_b']['effects']}"
        )

        # migration_report must have one entry for the reverse effect
        report = data["migration_report"]
        assert len(report) >= 1, f"migration_report empty: {report}"
        assert report[0]["disposition"] == "copied", f"unexpected disposition: {report[0]}"
        assert report[0]["target"] == "both", f"unexpected target: {report[0]}"

        # Frame boundaries must be correct
        assert data["clip_a"]["in_point"] == 0
        assert data["clip_a"]["out_point"] == 60
        assert data["clip_b"]["in_point"] == 60
        assert data["clip_b"]["out_point"] == 120
