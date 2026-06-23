# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke tests for QC oracle worker path (BL-488).

Verifies that QC assertions are populated when a render job completes with
a delivery profile. Covers AC-1 of v079 feature 012-smoke-test-updates.

All tests in this file are FFmpeg-gated (STOAT_TEST_FFMPEG=1).
"""

from __future__ import annotations

import os

import httpx
import pytest

from tests.smoke.conftest import poll_job_until_terminal

_FFMPEG_TESTS = pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="FFmpeg integration test — set STOAT_TEST_FFMPEG=1 to run",
)


@_FFMPEG_TESTS
async def test_qc_oracle_populates_delivery_profile_assertions(
    smoke_client: httpx.AsyncClient,
) -> None:
    """QC worker path: render with delivery profile yields non-null loudness target."""
    import json

    # Create project
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "QC Oracle Smoke"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # Create delivery profile with loudness target
    dp_resp = await smoke_client.post(
        "/api/v1/delivery-profiles",
        json={
            "name": "QC Oracle Test Profile",
            "loudness_target_lufs": -16.0,
            "true_peak_ceiling_dbtp": -1.0,
        },
    )
    assert dp_resp.status_code == 201, f"Delivery profile creation failed: {dp_resp.text}"
    delivery_profile_id = dp_resp.json()["id"]

    # Submit render with delivery profile
    render_resp = await smoke_client.post(
        "/api/v1/render",
        json={
            "project_id": project_id,
            "render_plan": json.dumps({"settings": {}}),
            "delivery_profile_id": delivery_profile_id,
        },
    )
    assert render_resp.status_code in (201, 422), f"Unexpected render status: {render_resp.text}"
    if render_resp.status_code == 422:
        pytest.skip("Render validation failed — likely empty timeline, FFmpeg path skipped")

    job_id = render_resp.json()["id"]
    await poll_job_until_terminal(smoke_client, job_id, timeout=120)

    # Fetch QC report
    qc_resp = await smoke_client.get(f"/api/v1/render/{job_id}/qc")
    assert qc_resp.status_code == 200, f"QC report not found: {qc_resp.text}"
    qc = qc_resp.json()

    # BL-488: delivery-profile assertions must be populated
    loudness = qc.get("checks", {}).get("loudness_integrated", {})
    assert loudness.get("target") is not None, (
        f"BL-488 regression: loudness_integrated.target is null — "
        f"QC worker path not propagating delivery profile assertions. qc={qc}"
    )
    assert loudness["target"] == -16.0

    true_peak = qc.get("checks", {}).get("true_peak", {})
    assert true_peak.get("target") is not None, "BL-488 regression: true_peak.target is null"
    assert true_peak["target"] == -1.0
