"""Smoke tests for batch render submission and polling.

Validates submitting a batch render job and polling for terminal
status through the full HTTP stack with real Rust core.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest


async def _noop_render_handler(project_id: str, output_path: str, quality: str) -> None:
    """No-op render handler for smoke testing batch infrastructure."""


@pytest.fixture()
async def batch_client(smoke_client: httpx.AsyncClient) -> httpx.AsyncClient:
    """Smoke client with a batch render handler injected.

    Injects a no-op render handler into app.state so batch jobs
    complete successfully through the handler path.

    Args:
        smoke_client: The base smoke test client.

    Returns:
        The same client with batch handler configured.
    """
    transport = smoke_client._transport
    assert isinstance(transport, httpx.ASGITransport)
    transport.app.state.batch_render_handler = _noop_render_handler  # type: ignore[union-attr]
    return smoke_client


async def test_batch_submit_and_poll(batch_client: httpx.AsyncClient) -> None:
    """Submit a batch render job and poll until terminal status."""
    client = batch_client

    # Create a project for the batch job
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Batch Smoke Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Submit batch render
    resp = await client.post(
        "/api/v1/render/batch",
        json={
            "jobs": [
                {
                    "project_id": project_id,
                    "output_path": "/tmp/smoke_render.mp4",
                    "quality": "medium",
                },
            ],
        },
    )
    assert resp.status_code == 202
    body = resp.json()
    batch_id = body["batch_id"]
    assert body["jobs_queued"] == 1
    assert body["status"] == "accepted"

    # Poll for terminal status with 60s timeout
    terminal_statuses = {"complete", "failed"}
    deadline = asyncio.get_event_loop().time() + 60.0

    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"/api/v1/render/batch/{batch_id}")
        assert resp.status_code == 200
        progress = resp.json()
        assert progress["total_jobs"] == 1

        # Check if all jobs reached terminal status
        all_terminal = all(j["status"] in terminal_statuses for j in progress["jobs"])
        if all_terminal:
            assert progress["completed_jobs"] + progress["failed_jobs"] == 1
            # With no-op handler, job should complete successfully
            assert progress["completed_jobs"] == 1
            assert progress["overall_progress"] == pytest.approx(1.0)
            return

        await asyncio.sleep(0.25)

    raise asyncio.TimeoutError(f"Batch {batch_id} did not reach terminal status within 60s")
