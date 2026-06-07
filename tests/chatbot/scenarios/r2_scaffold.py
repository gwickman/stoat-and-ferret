"""Chatbot scenario runner hook for Release 2 scaffold."""

from __future__ import annotations

import httpx


async def run_r2_scenario(base_url: str) -> dict:
    """Chatbot scenario runner hook for Release 2 scaffold.

    Drives the REST API: creates a project, triggers a QC-capable operation,
    captures and returns the structured response.
    """
    async with httpx.AsyncClient(base_url=base_url) as client:
        resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "R2 Scaffold Scenario",
                "output_width": 1920,
                "output_height": 1080,
                "output_fps": 30,
            },
        )
        resp.raise_for_status()
        project = resp.json()
        # Return stub QC report dict (QCService does not exist in v075)
        return {"project_id": project["id"], "qc_report": {}, "status": "scaffold"}
