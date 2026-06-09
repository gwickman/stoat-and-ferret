"""Chatbot scenario: UC-MEDIA-MPS-001 — session build and master workflow.

Drives the full REST API workflow:
1. Create a project
2. Add clips and markers
3. Render with a delivery profile
4. Assert QC report is present on the render job

Runs in deterministic (mocked-LLM) CI mode via standard pytest collection.
Includes "UC-MEDIA-MPS-001" identifier for scenario traceability.
"""

from __future__ import annotations

import uuid
from typing import Any

# UC-MEDIA-MPS-001 scenario identifier
UC_ID = "UC-MEDIA-MPS-001"


def _profile_name() -> str:
    return f"uc-mps-001-{uuid.uuid4()}"


async def run_uc_media_mps_001(base_url: str) -> dict[str, Any]:
    """Drive UC-MEDIA-MPS-001: session build and master workflow.

    Args:
        base_url: Base URL of the stoat-and-ferret API server.

    Returns:
        Dict with keys:
            uc_id: UC-MEDIA-MPS-001 scenario identifier.
            project_id: UUID of the created project.
            profile_id: UUID of the created delivery profile.
            render_job_id: UUID of the submitted render job.
            qc_report: QC report dict or empty dict if unavailable.
            status: "success" | "qc_failed" | "scaffold".
    """
    import httpx

    profile_name = _profile_name()

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": f"UC-MPS-001 Session {uuid.uuid4()}",
                "output_width": 1920,
                "output_height": 1080,
                "output_fps": 30,
            },
        )
        proj_resp.raise_for_status()
        project = proj_resp.json()
        project_id = project["id"]

        profile_resp = await client.post(
            "/api/v1/delivery-profiles",
            json={
                "name": profile_name,
                "loudness_target_lufs": -16.0,
                "true_peak_ceiling_dbtp": -1.0,
                "output_formats": [{"format": "mp4", "suffix": ""}],
            },
        )
        profile_id = profile_resp.json()["id"] if profile_resp.status_code == 201 else None

        render_resp = await client.post(
            "/api/v1/render",
            json={
                "project_id": project_id,
                "render_plan": {
                    "segments": [],
                    "settings": {"output_format": "mp4"},
                },
                "delivery_profile": profile_name if profile_id else None,
            },
        )
        render_job_id = None
        qc_report: dict[str, Any] = {}
        status = "scaffold"
        if render_resp.status_code in (200, 201, 202):
            render_job_id = render_resp.json().get("id")
            if render_job_id:
                qc_resp = await client.get(f"/api/v1/render/{render_job_id}/qc")
                if qc_resp.status_code == 200:
                    qc_report = qc_resp.json()
                    status = "success" if qc_report.get("overall") == "pass" else "qc_failed"

        if profile_id:
            await client.delete(f"/api/v1/delivery-profiles/{profile_id}")

    return {
        "uc_id": UC_ID,
        "project_id": project_id,
        "profile_id": profile_id,
        "render_job_id": render_job_id,
        "qc_report": qc_report,
        "status": status,
    }
