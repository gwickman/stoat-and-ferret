"""Smoke tests for video library search, detail, thumbnail, and delete (UC-02).

Validates pagination with limit/offset, FTS5 full-text search, single video
retrieval, thumbnail generation, and video deletion.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from tests.smoke.conftest import scan_videos_and_wait


@pytest.mark.usefixtures("videos_dir")
async def test_uc02_library_search(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Search and paginate the video library after scanning."""
    await scan_videos_and_wait(smoke_client, videos_dir)

    # Pagination: first page of 2
    resp = await smoke_client.get("/api/v1/videos?limit=2&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 6
    assert len(body["videos"]) == 2

    # Pagination: offset past end returns empty
    resp = await smoke_client.get("/api/v1/videos?limit=2&offset=6")
    assert resp.status_code == 200
    assert len(resp.json()["videos"]) == 0

    # FTS5 search: "running" matches running1.mp4 and running2.mp4
    resp = await smoke_client.get("/api/v1/videos/search?q=running")
    assert resp.status_code == 200
    search_body = resp.json()
    assert search_body["total"] == 2
    filenames = {v["filename"] for v in search_body["videos"]}
    assert filenames == {"running1.mp4", "running2.mp4"}

    # FTS5 search: nonexistent query returns 0 results
    resp = await smoke_client.get("/api/v1/videos/search?q=nonexistent")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["videos"] == []


@pytest.mark.usefixtures("videos_dir")
async def test_video_detail(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """GET /videos/{video_id} returns 200 with full metadata (BL-121 FR-001)."""
    await scan_videos_and_wait(smoke_client, videos_dir)

    # Get a video ID from the list
    resp = await smoke_client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video_id = resp.json()["videos"][0]["id"]

    # GET detail
    resp = await smoke_client.get(f"/api/v1/videos/{video_id}")
    assert resp.status_code == 200
    body = resp.json()

    # Verify all required metadata fields are present
    required_fields = {
        "id",
        "path",
        "filename",
        "duration_frames",
        "frame_rate_numerator",
        "frame_rate_denominator",
        "width",
        "height",
        "video_codec",
        "file_size",
    }
    assert required_fields.issubset(body.keys()), f"Missing fields: {required_fields - body.keys()}"
    assert body["id"] == video_id
    assert body["duration_frames"] > 0
    assert body["width"] > 0
    assert body["height"] > 0
    assert body["file_size"] > 0


@pytest.mark.usefixtures("videos_dir")
async def test_video_detail_not_found(
    smoke_client: httpx.AsyncClient,
) -> None:
    """GET /videos/{fake_id} returns 404 (BL-121 FR-002)."""
    fake_id = str(uuid.uuid4())
    resp = await smoke_client.get(f"/api/v1/videos/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.usefixtures("videos_dir")
async def test_video_thumbnail(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """GET /videos/{video_id}/thumbnail returns JPEG image (BL-121 FR-003)."""
    await scan_videos_and_wait(smoke_client, videos_dir)

    # Get a video ID
    resp = await smoke_client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video_id = resp.json()["videos"][0]["id"]

    # GET thumbnail
    resp = await smoke_client.get(f"/api/v1/videos/{video_id}/thumbnail")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    assert len(resp.content) > 0


@pytest.mark.usefixtures("videos_dir")
async def test_video_delete(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """DELETE /videos/{video_id} returns 204, subsequent GET 404 (BL-121 FR-004/005)."""
    await scan_videos_and_wait(smoke_client, videos_dir)

    # Get list total before delete
    resp = await smoke_client.get("/api/v1/videos?limit=1&offset=0")
    assert resp.status_code == 200
    total_before = resp.json()["total"]
    assert total_before > 0

    # Pick a video to delete
    video_id = resp.json()["videos"][0]["id"]

    # DELETE (no delete_file — keep source on disk)
    resp = await smoke_client.delete(f"/api/v1/videos/{video_id}")
    assert resp.status_code == 204

    # Subsequent GET returns 404
    resp = await smoke_client.get(f"/api/v1/videos/{video_id}")
    assert resp.status_code == 404

    # List total decremented by 1
    resp = await smoke_client.get("/api/v1/videos?limit=1&offset=0")
    assert resp.status_code == 200
    assert resp.json()["total"] == total_before - 1


_STUB_VIDEO_ID = "00000000-0000-0000-0000-000000000001"


async def _ensure_stub_video(client: httpx.AsyncClient) -> str:
    """Insert a minimal stub video row and return its ID."""
    transport: httpx.ASGITransport = client._transport  # type: ignore[assignment]
    db = transport.app.state.db  # type: ignore[union-attr]
    now_str = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT OR IGNORE INTO videos "
        "(id, path, filename, duration_frames, frame_rate_numerator, frame_rate_denominator, "
        "width, height, video_codec, file_size, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            _STUB_VIDEO_ID,
            "/stub/video.mp4",
            "stub.mp4",
            100,
            30,
            1,
            1280,
            720,
            "h264",
            1000,
            now_str,
            now_str,
        ),
    )
    await db.commit()  # type: ignore[union-attr]
    return _STUB_VIDEO_ID


async def test_delete_library_resources_emit_ws_events(
    smoke_client: httpx.AsyncClient,
) -> None:
    """DELETE clip then video broadcasts clip_deleted and video_deleted WS events (BL-416, AC-1)."""
    video_id = await _ensure_stub_video(smoke_client)

    resp = await smoke_client.post("/api/v1/projects", json={"name": "WS Delete Events Test"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={"source_video_id": video_id, "in_point": 0, "out_point": 60, "timeline_position": 0},
    )
    assert resp.status_code == 201
    clip_id = resp.json()["id"]

    transport: httpx.ASGITransport = smoke_client._transport  # type: ignore[assignment]
    ws_manager = transport.app.state.ws_manager  # type: ignore[union-attr]
    captured: list[dict] = []
    original_broadcast = ws_manager.broadcast

    async def _capture(event: dict) -> None:
        captured.append(event)

    ws_manager.broadcast = _capture
    try:
        resp = await smoke_client.delete(f"/api/v1/projects/{project_id}/clips/{clip_id}")
        assert resp.status_code == 204
        clip_evts = [e for e in captured if e["type"] == "clip_deleted"]
        assert len(clip_evts) == 1, (
            f"Expected 1 clip_deleted event, got types: {[e['type'] for e in captured]}"
        )
        assert clip_evts[0]["payload"]["clip_id"] == clip_id
        assert clip_evts[0]["payload"]["project_id"] == project_id

        resp = await smoke_client.delete(f"/api/v1/videos/{video_id}")
        assert resp.status_code == 204
        video_evts = [e for e in captured if e["type"] == "video_deleted"]
        assert len(video_evts) == 1, (
            f"Expected 1 video_deleted event, got types: {[e['type'] for e in captured]}"
        )
        assert video_evts[0]["payload"]["video_id"] == video_id
    finally:
        ws_manager.broadcast = original_broadcast


async def test_render_completed_event_contains_output_path(
    smoke_client_noop: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """render_completed WS event carries a non-empty output_path field (BL-411, AC-2)."""
    transport: httpx.ASGITransport = smoke_client_noop._transport  # type: ignore[assignment]
    ws_manager = transport.app.state.ws_manager  # type: ignore[union-attr]
    ws_queue: asyncio.Queue[dict] = asyncio.Queue()
    original_broadcast = ws_manager.broadcast

    async def _capture(event: dict) -> None:
        await ws_queue.put(event)

    ws_manager.broadcast = _capture
    try:
        await scan_videos_and_wait(smoke_client_noop, videos_dir)
        resp = await smoke_client_noop.get("/api/v1/videos?limit=1")
        assert resp.status_code == 200
        video_id = resp.json()["videos"][0]["id"]

        resp = await smoke_client_noop.post(
            "/api/v1/projects", json={"name": "Render Output Path Test"}
        )
        assert resp.status_code == 201
        project_id = resp.json()["id"]

        resp = await smoke_client_noop.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "source_video_id": video_id,
                "in_point": 0,
                "out_point": 60,
                "timeline_position": 0,
            },
        )
        assert resp.status_code == 201

        resp = await smoke_client_noop.post(
            "/api/v1/render",
            json={"project_id": project_id, "render_plan": json.dumps({"total_duration": 2.0})},
        )
        assert resp.status_code == 201
        job_id = resp.json()["id"]

        completed = None
        deadline = asyncio.get_event_loop().time() + 60.0
        while asyncio.get_event_loop().time() < deadline:
            remaining = deadline - asyncio.get_event_loop().time()
            event = await asyncio.wait_for(ws_queue.get(), timeout=remaining)
            if event["type"] == "render_completed" and event["payload"].get("job_id") == job_id:
                completed = event
                break

        assert completed is not None, "render_completed event not received within 60s"
        assert completed["payload"]["output_path"], (
            "output_path must be non-empty in render_completed payload"
        )
    finally:
        ws_manager.broadcast = original_broadcast


@pytest.mark.skipif(not os.getenv("STOAT_TEST_FFMPEG"), reason="requires real FFmpeg")
async def test_concurrent_renders_have_distinct_output_paths(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Two concurrent renders produce distinct output_path values (BL-403, AC-3)."""
    transport: httpx.ASGITransport = smoke_client._transport  # type: ignore[assignment]
    ws_manager = transport.app.state.ws_manager  # type: ignore[union-attr]
    ws_queue: asyncio.Queue[dict] = asyncio.Queue()
    original_broadcast = ws_manager.broadcast

    async def _capture(event: dict) -> None:
        await ws_queue.put(event)

    ws_manager.broadcast = _capture
    try:
        await scan_videos_and_wait(smoke_client, videos_dir)
        resp = await smoke_client.get("/api/v1/videos?limit=2")
        assert resp.status_code == 200
        videos = resp.json()["videos"]
        vid_a = videos[0]["id"]
        vid_b = videos[min(1, len(videos) - 1)]["id"]

        async def _setup_project(name: str, video_id: str) -> tuple[str, float]:
            r = await smoke_client.post("/api/v1/projects", json={"name": name})
            assert r.status_code == 201
            pid = r.json()["id"]
            r = await smoke_client.post(
                f"/api/v1/projects/{pid}/clips",
                json={
                    "source_video_id": video_id,
                    "in_point": 0,
                    "out_point": 60,
                    "timeline_position": 0,
                },
            )
            assert r.status_code == 201
            # Derive timeline duration from clip length (60 frames) and video fps
            v = await smoke_client.get(f"/api/v1/videos/{video_id}")
            assert v.status_code == 200
            vdata = v.json()
            fps = vdata["frame_rate_numerator"] / vdata["frame_rate_denominator"]
            timeline_duration = 60.0 / fps
            return pid, timeline_duration

        (p1_id, tl1_duration), (p2_id, tl2_duration) = await asyncio.gather(
            _setup_project("Concurrent Render A", vid_a),
            _setup_project("Concurrent Render B", vid_b),
        )

        r1, r2 = await asyncio.gather(
            smoke_client.post(
                "/api/v1/render",
                json={
                    "project_id": p1_id,
                    "render_plan": json.dumps({"total_duration": tl1_duration, "settings": {}}),
                },
            ),
            smoke_client.post(
                "/api/v1/render",
                json={
                    "project_id": p2_id,
                    "render_plan": json.dumps({"total_duration": tl2_duration, "settings": {}}),
                },
            ),
        )
        assert r1.status_code == 201
        assert r2.status_code == 201
        job_ids = {r1.json()["id"], r2.json()["id"]}

        completed_events: list[dict] = []
        deadline = asyncio.get_event_loop().time() + 120.0
        while len(completed_events) < 2 and asyncio.get_event_loop().time() < deadline:
            remaining = deadline - asyncio.get_event_loop().time()
            event = await asyncio.wait_for(ws_queue.get(), timeout=remaining)
            if event["type"] == "render_completed" and event["payload"].get("job_id") in job_ids:
                completed_events.append(event)

        assert len(completed_events) == 2, (
            f"Expected 2 render_completed events, got {len(completed_events)}"
        )
        paths = [e["payload"]["output_path"] for e in completed_events]
        assert paths[0] != paths[1], f"Expected distinct output paths, got: {paths}"
    finally:
        ws_manager.broadcast = original_broadcast


@pytest.mark.skipif(not os.getenv("STOAT_TEST_FFMPEG"), reason="requires STOAT_TEST_FFMPEG=1")
async def test_partial_file_cancel(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Cancel mid-encode: partial_file_detected is True (BL-415-AC-3, BL-462-AC-1)."""
    await scan_videos_and_wait(smoke_client, videos_dir)
    resp = await smoke_client.get("/api/v1/videos?limit=100")
    assert resp.status_code == 200
    videos_list = resp.json()["videos"]
    clip_video = next(
        (v for v in videos_list if v["filename"] == "81872-577880797_medium.mp4"), None
    )
    assert clip_video is not None, "Expected 51s demo video not found in library"
    video_id = clip_video["id"]
    fps = clip_video["frame_rate_numerator"] / clip_video["frame_rate_denominator"]
    clip_duration = clip_video["duration_frames"] / fps

    resp = await smoke_client.post("/api/v1/projects", json={"name": "Partial File Cancel Test"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "source_video_id": video_id,
            "in_point": 0,
            "out_point": clip_video["duration_frames"],
            "timeline_position": 0,
        },
    )
    assert resp.status_code == 201

    for _attempt in range(2):
        resp = await smoke_client.post(
            "/api/v1/render",
            json={
                "project_id": project_id,
                "render_plan": json.dumps({"total_duration": clip_duration, "settings": {}}),
            },
        )
        assert resp.status_code == 201
        job_id = resp.json()["id"]

        cancelled = False
        loop = asyncio.get_running_loop()
        deadline = loop.time() + 120.0
        while loop.time() < deadline:
            r = await smoke_client.get(f"/api/v1/render/{job_id}")
            assert r.status_code == 200
            body = r.json()
            if body["status"] == "running" and 0.0 < body["progress"] < 0.2:
                cancel_resp = await smoke_client.post(f"/api/v1/render/{job_id}/cancel")
                if cancel_resp.status_code == 409:
                    break
                assert cancel_resp.status_code == 200
                cancelled = True
                break
            if body["status"] in {"completed", "failed", "cancelled"}:
                break
            await asyncio.sleep(0.5)

        if not cancelled:
            continue

        deadline = asyncio.get_running_loop().time() + 30.0
        while asyncio.get_running_loop().time() < deadline:
            r = await smoke_client.get(f"/api/v1/render/{job_id}")
            assert r.status_code == 200
            body = r.json()
            if body["status"] == "cancelled":
                assert body["partial_file_detected"] is True, (
                    "Expected partial_file_detected=True after mid-encode cancel"
                )
                return
            if body["status"] in {"completed", "failed"}:
                break
            await asyncio.sleep(0.5)

    pytest.fail("Could not achieve mid-encode cancel after 2 attempts")


@pytest.mark.skipif(not os.getenv("STOAT_TEST_FFMPEG"), reason="requires STOAT_TEST_FFMPEG=1")
async def test_render_progress_increments(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """FFmpeg progress increments over time via REST and WS (BL-394-AC-2/3, BL-462-AC-2)."""
    transport: httpx.ASGITransport = smoke_client._transport  # type: ignore[assignment]
    ws_manager = transport.app.state.ws_manager  # type: ignore[union-attr]
    ws_queue: asyncio.Queue[dict] = asyncio.Queue()
    original_broadcast = ws_manager.broadcast

    async def _capture(event: dict) -> None:
        await ws_queue.put(event)

    ws_manager.broadcast = _capture
    try:
        await scan_videos_and_wait(smoke_client, videos_dir)
        resp = await smoke_client.get("/api/v1/videos?limit=100")
        assert resp.status_code == 200
        videos_list = resp.json()["videos"]
        clip_video = next(
            (v for v in videos_list if v["filename"] == "81872-577880797_medium.mp4"), None
        )
        assert clip_video is not None, "Expected 51s demo video not found in library"
        video_id = clip_video["id"]
        fps = clip_video["frame_rate_numerator"] / clip_video["frame_rate_denominator"]
        clip_duration = clip_video["duration_frames"] / fps

        resp = await smoke_client.post(
            "/api/v1/projects", json={"name": "Render Progress Increments Test"}
        )
        assert resp.status_code == 201
        project_id = resp.json()["id"]

        resp = await smoke_client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "source_video_id": video_id,
                "in_point": 0,
                "out_point": clip_video["duration_frames"],
                "timeline_position": 0,
            },
        )
        assert resp.status_code == 201

        resp = await smoke_client.post(
            "/api/v1/render",
            json={
                "project_id": project_id,
                "render_plan": json.dumps({"total_duration": clip_duration, "settings": {}}),
            },
        )
        assert resp.status_code == 201
        job_id = resp.json()["id"]

        poll_progress_values: list[float] = []
        ws_progress_values: list[float] = []
        render_done = asyncio.Event()

        async def _poll_rest() -> None:
            terminal = {"completed", "failed", "cancelled"}
            loop = asyncio.get_running_loop()
            deadline = loop.time() + 200.0
            while loop.time() < deadline and not render_done.is_set():
                r = await smoke_client.get(f"/api/v1/render/{job_id}")
                if r.status_code == 200:
                    body = r.json()
                    poll_progress_values.append(body["progress"])
                    if body["status"] in terminal:
                        render_done.set()
                        return
                await asyncio.sleep(1.0)

        async def _collect_ws() -> None:
            loop = asyncio.get_running_loop()
            deadline = loop.time() + 200.0
            while loop.time() < deadline:
                if render_done.is_set():
                    return
                remaining = deadline - loop.time()
                try:
                    event = await asyncio.wait_for(ws_queue.get(), timeout=min(remaining, 5.0))
                except asyncio.TimeoutError:
                    if render_done.is_set():
                        return
                    continue
                if event["type"] == "render_progress" and event["payload"].get("job_id") == job_id:
                    ws_progress_values.append(event["payload"]["progress"])
                elif (
                    event["type"] == "render_completed" and event["payload"].get("job_id") == job_id
                ):
                    render_done.set()
                    return

        await asyncio.gather(_poll_rest(), _collect_ws())

        distinct_nonzero = {p for p in poll_progress_values if p > 0.0}
        assert len(distinct_nonzero) >= 2, (
            f"Expected ≥2 distinct non-zero REST progress values, got: {sorted(distinct_nonzero)}"
        )
        if ws_progress_values:
            ws_max = max(ws_progress_values)
            poll_max = max(poll_progress_values)
            assert ws_max >= poll_max, f"WS max progress {ws_max:.3f} < REST max {poll_max:.3f}"
    finally:
        ws_manager.broadcast = original_broadcast
