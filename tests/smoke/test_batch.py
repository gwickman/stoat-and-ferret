"""Smoke tests for batch render submission and polling.

Validates submitting a batch render job and polling for terminal
status through the full HTTP stack with real Rust core.
Also verifies batch state survives a simulated server restart.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import httpx
import pytest

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.api.settings import get_settings


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
    terminal_statuses = {"completed", "failed"}
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


async def test_batch_persists_across_restart(tmp_path: Path) -> None:
    """Batch state survives a simulated server restart.

    Submits a batch job via the first app instance, shuts it down,
    then boots a fresh app instance against the same database and
    verifies the batch state is retrievable.
    """
    db_path = tmp_path / "restart_test.db"

    orig_db = os.environ.get("STOAT_DATABASE_PATH")
    orig_thumb = os.environ.get("STOAT_THUMBNAIL_DIR")

    os.environ["STOAT_DATABASE_PATH"] = str(db_path)
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")
    get_settings.cache_clear()

    # --- First app instance: submit batch ---
    app1 = create_app()
    async with lifespan(app1):
        app1.state.batch_render_handler = _noop_render_handler
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app1),
            base_url="http://testserver",
        ) as client1:
            # Create project
            resp = await client1.post(
                "/api/v1/projects",
                json={"name": "Restart Test Project"},
            )
            assert resp.status_code == 201
            project_id = resp.json()["id"]

            # Submit batch
            resp = await client1.post(
                "/api/v1/render/batch",
                json={
                    "jobs": [
                        {
                            "project_id": project_id,
                            "output_path": "/tmp/restart_test.mp4",
                            "quality": "high",
                        },
                    ],
                },
            )
            assert resp.status_code == 202
            batch_id = resp.json()["batch_id"]

            # Wait for job to complete
            deadline = asyncio.get_event_loop().time() + 30.0
            while asyncio.get_event_loop().time() < deadline:
                resp = await client1.get(f"/api/v1/render/batch/{batch_id}")
                assert resp.status_code == 200
                progress = resp.json()
                if all(j["status"] in ("completed", "failed") for j in progress["jobs"]):
                    break
                await asyncio.sleep(0.1)

    # --- Second app instance: verify batch survives restart ---
    get_settings.cache_clear()
    app2 = create_app()
    async with (
        lifespan(app2),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app2),
            base_url="http://testserver",
        ) as client2,
    ):
        resp = await client2.get(f"/api/v1/render/batch/{batch_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["batch_id"] == batch_id
        assert data["total_jobs"] == 1
        assert data["jobs"][0]["project_id"] == project_id
        assert data["jobs"][0]["status"] == "completed"
        assert data["jobs"][0]["progress"] == pytest.approx(1.0)

    # Restore env
    if orig_db is None:
        os.environ.pop("STOAT_DATABASE_PATH", None)
    else:
        os.environ["STOAT_DATABASE_PATH"] = orig_db

    if orig_thumb is None:
        os.environ.pop("STOAT_THUMBNAIL_DIR", None)
    else:
        os.environ["STOAT_THUMBNAIL_DIR"] = orig_thumb

    get_settings.cache_clear()
