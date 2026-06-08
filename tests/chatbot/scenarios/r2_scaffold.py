"""Chatbot scenario runner hook for Release 2 scaffold.

Delegates to uc_cap_master for the full delivery profile mastering scenario.
"""

from __future__ import annotations

import httpx


async def run_r2_scenario(base_url: str) -> dict:
    """Chatbot scenario runner hook for Release 2 scaffold.

    Drives the REST API: creates a project and returns a structured response.
    Delegates QC-capable mastering to uc_cap_master.run_uc_cap_master().
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
        # Return scaffold result; full scenario is in uc_cap_master.run_uc_cap_master()
        return {"project_id": project["id"], "qc_report": {}, "status": "scaffold"}
