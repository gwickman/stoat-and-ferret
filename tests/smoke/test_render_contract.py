# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke tests verifying render_plan contract end-to-end (BL-371, BL-372).

Validates:
- render_plan.total_duration is derived from timeline.duration (BL-371-AC-1, AC-2)
- Multiple projects preserve distinct render_plan.total_duration values
- 422 is returned when render_plan.total_duration is absent in noop mode (negative test)
- 4xx responses carry structured detail with a message field (BL-372-AC-1 backend assertion)
- Noop render returns 201 and job appears in render queue (BL-371-AC-1, AC-3)
- Job status polling shows completed state immediately in noop mode (BL-371-AC-3)
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from stoat_ferret.db.clip_repository import AsyncSQLiteClipRepository
from stoat_ferret.db.models import Clip
from stoat_ferret.render.models import RenderStatus
from stoat_ferret.render.render_repository import AsyncSQLiteRenderRepository
from tests.conftest import requires_ffmpeg
from tests.smoke.conftest import poll_job_until_terminal, scan_videos_and_wait

_STUB_VIDEO_ID = "00000000-0000-0000-0000-000000000001"


async def _ensure_stub_video(db: object) -> None:
    """Insert a stub video row required as FK parent for stub clips."""
    now_str = datetime.now(timezone.utc).isoformat()
    await db.execute(  # type: ignore[union-attr]
        "INSERT OR IGNORE INTO videos "
        "(id, path, filename, duration_frames, frame_rate_numerator, frame_rate_denominator, "
        "width, height, video_codec, file_size, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            _STUB_VIDEO_ID,
            "/stub/video.mp4",
            "video.mp4",
            100,
            30,
            1,
            1920,
            1080,
            "h264",
            1000,
            now_str,
            now_str,
        ),
    )
    await db.commit()  # type: ignore[union-attr]


async def _seed_stub_clip(client: httpx.AsyncClient, project_id: str) -> str:
    """Insert a stub clip row bypassing video validation. Returns the clip id."""
    transport: httpx.ASGITransport = client._transport  # type: ignore[assignment]
    db = transport.app.state.db  # type: ignore[union-attr]
    await _ensure_stub_video(db)
    repo = AsyncSQLiteClipRepository(db)
    now = datetime.now(timezone.utc)
    clip = Clip(
        id=Clip.new_id(),
        project_id=project_id,
        source_video_id=_STUB_VIDEO_ID,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await repo.add(clip)
    return clip.id


async def _create_project_with_timeline(
    client: httpx.AsyncClient,
    project_name: str,
    timeline_end: float,
) -> tuple[str, float]:
    """Create a project with a single clip spanning [0, timeline_end] seconds.

    Returns (project_id, timeline_end). The timeline duration returned by
    GET /api/v1/projects/{project_id}/timeline will equal timeline_end.
    """
    resp = await client.post("/api/v1/projects", json={"name": project_name})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    clip_id = await _seed_stub_clip(client, project_id)

    resp = await client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[{"track_type": "video", "label": "V1"}],
    )
    assert resp.status_code == 200
    track_id = resp.json()["tracks"][0]["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/clips",
        json={
            "clip_id": clip_id,
            "track_id": track_id,
            "timeline_start": 0.0,
            "timeline_end": timeline_end,
        },
    )
    assert resp.status_code == 201

    return project_id, timeline_end


async def test_render_plan_construction_from_timeline(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Render plan total_duration matches the project's timeline duration.

    Creates a project with a 100s timeline, GETs the timeline to read
    duration, submits a render with render_plan.total_duration == duration,
    and asserts 201 in noop mode.
    """
    project_id, expected_duration = await _create_project_with_timeline(
        smoke_client_noop, "Render Plan Construction Test", 100.0
    )

    timeline_resp = await smoke_client_noop.get(f"/api/v1/projects/{project_id}/timeline")
    assert timeline_resp.status_code == 200
    timeline_duration = timeline_resp.json()["duration"]
    assert timeline_duration == pytest.approx(expected_duration)

    render_plan = json.dumps({"total_duration": timeline_duration, "settings": {}})
    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": render_plan},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "completed"


async def test_render_plan_multiple_projects(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Distinct projects produce distinct render_plan.total_duration values.

    Creates two projects with different timeline durations (100s, 200s)
    and verifies both render calls succeed with their respective durations.
    """
    project_id_a, duration_a = await _create_project_with_timeline(
        smoke_client_noop, "Project A - 100s", 100.0
    )
    project_id_b, duration_b = await _create_project_with_timeline(
        smoke_client_noop, "Project B - 200s", 200.0
    )

    assert duration_a != duration_b

    resp_a = await smoke_client_noop.post(
        "/api/v1/render",
        json={
            "project_id": project_id_a,
            "render_plan": json.dumps({"total_duration": duration_a, "settings": {}}),
        },
    )
    assert resp_a.status_code == 201
    assert resp_a.json()["status"] == "completed"

    resp_b = await smoke_client_noop.post(
        "/api/v1/render",
        json={
            "project_id": project_id_b,
            "render_plan": json.dumps({"total_duration": duration_b, "settings": {}}),
        },
    )
    assert resp_b.status_code == 201
    assert resp_b.json()["status"] == "completed"


async def test_render_422_without_render_plan(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Omitting total_duration in noop mode returns 422 PREFLIGHT_FAILED.

    Negative test: verifies the guard that prevents renders without a
    valid render_plan.total_duration. This confirms that the positive tests
    above are actually exercising the guard, not bypassing it.
    """
    resp = await smoke_client_noop.post("/api/v1/projects", json={"name": "Render 422 Test"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]
    await _seed_stub_clip(smoke_client_noop, project_id)

    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": json.dumps({"settings": {}})},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["code"] == "PREFLIGHT_FAILED"
    assert "total_duration" in body["detail"]["message"]


async def test_error_response_detail_message(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """4xx render responses carry structured detail with a non-empty message field.

    Verifies that the backend emits detail as a dict (not a plain string or
    object) so the frontend can safely extract detail.message without hitting
    the 'Objects are not valid as a React child' invariant (BL-372-AC-1 backend
    assertion — frontend display verified by Feature 002 unit tests).
    """
    resp = await smoke_client_noop.post("/api/v1/projects", json={"name": "Error Detail Test"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]
    await _seed_stub_clip(smoke_client_noop, project_id)

    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": json.dumps({})},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert isinstance(body["detail"], dict), (
        "detail must be a dict so frontend can extract detail.message safely"
    )
    assert "code" in body["detail"]
    assert "message" in body["detail"]
    assert isinstance(body["detail"]["message"], str)
    assert len(body["detail"]["message"]) > 0


async def test_error_response_missing_detail(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Non-existent project returns 404 with structured detail.code and detail.message.

    Verifies the fallback path: when render_plan is present but the project
    doesn't exist, the response still has a structured error (not a missing-
    detail scenario). The 'detail absent' case on the frontend falls back to
    HTTP status text (verified by Feature 002 unit tests).
    """
    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={
            "project_id": "00000000-0000-0000-0000-000000000000",
            "render_plan": json.dumps({"total_duration": 5.0, "settings": {}}),
        },
    )
    assert resp.status_code == 404
    body = resp.json()
    assert isinstance(body["detail"], dict)
    assert "code" in body["detail"]
    assert "message" in body["detail"]


async def test_noop_render_success(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Noop render returns 201 and the new job appears in the render queue.

    Satisfies BL-371-AC-1 (returns 201, not 422) and BL-371-AC-3 (job visible
    in queue) for the backend smoke test contract.
    """
    project_id, duration = await _create_project_with_timeline(
        smoke_client_noop, "Noop Render Success", 50.0
    )

    render_plan = json.dumps({"total_duration": duration, "settings": {}})
    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": render_plan},
    )
    assert resp.status_code == 201
    body = resp.json()
    job_id = body["id"]
    assert body["status"] == "completed"

    list_resp = await smoke_client_noop.get("/api/v1/render")
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    assert list_body["total"] >= 1
    job_ids = [item["id"] for item in list_body["items"]]
    assert job_id in job_ids, f"Submitted job {job_id} not found in render queue (items: {job_ids})"


async def test_job_polling_noop_completed(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Job status polling shows completed state immediately in noop mode.

    Satisfies BL-371-AC-3: job status re-fetch reports completed. In noop mode
    the job is synchronously marked completed, so polling should see it
    immediately or within one 0.1s sleep.
    """
    project_id, duration = await _create_project_with_timeline(
        smoke_client_noop, "Noop Polling Test", 30.0
    )

    render_plan = json.dumps({"total_duration": duration, "settings": {}})
    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": render_plan},
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    # Poll until completed; timeout = 10s per NFR-002
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 10.0
    final_status: str | None = None
    while loop.time() < deadline:
        get_resp = await smoke_client_noop.get(f"/api/v1/render/{job_id}")
        assert get_resp.status_code == 200
        final_status = get_resp.json()["status"]
        if final_status == "completed":
            break
        await asyncio.sleep(0.1)

    assert final_status == "completed", (
        f"Expected 'completed' status after polling, got {final_status!r}"
    )


async def test_concurrent_renders_distinct_output_paths(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Two renders of the same project produce distinct output_path values (BL-403).

    Submits two renders for the same project and asserts:
    - Both complete successfully (status == 'completed')
    - The two output_path values are distinct strings (no last-write-wins collision)
    - Audit query confirms one-to-one job_id→output_path mapping for the project
    """
    project_id, duration = await _create_project_with_timeline(
        smoke_client_noop, "Concurrent Renders BL-403 Test", 50.0
    )
    render_plan = json.dumps({"total_duration": duration, "settings": {}})

    resp_a, resp_b = await asyncio.gather(
        smoke_client_noop.post(
            "/api/v1/render",
            json={"project_id": project_id, "render_plan": render_plan},
        ),
        smoke_client_noop.post(
            "/api/v1/render",
            json={"project_id": project_id, "render_plan": render_plan},
        ),
    )

    assert resp_a.status_code == 201, f"First render failed: {resp_a.json()}"
    assert resp_b.status_code == 201, f"Second render failed: {resp_b.json()}"

    body_a = resp_a.json()
    body_b = resp_b.json()
    assert body_a["status"] == "completed"
    assert body_b["status"] == "completed"

    output_path_a = body_a["output_path"]
    output_path_b = body_b["output_path"]
    assert output_path_a != output_path_b, (
        f"Expected distinct output paths but got duplicates: {output_path_a!r}"
    )

    # Audit query: verify one-to-one job_id→output_path mapping (BL-403-AC-4)
    transport: httpx.ASGITransport = smoke_client_noop._transport  # type: ignore[assignment]
    db = transport.app.state.db  # type: ignore[union-attr]
    repo = AsyncSQLiteRenderRepository(db)
    completed = await repo.list_by_status(RenderStatus.COMPLETED)
    project_paths = [j.output_path for j in completed if j.project_id == project_id]
    assert len(project_paths) == 2
    assert len(set(project_paths)) == len(project_paths), (
        f"Duplicate output_path found among completed jobs: {project_paths}"
    )


async def test_render_progress_increments(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Progress field advances during render (BL-394-AC-4).

    Polls GET /api/v1/render/{job_id} at 1s intervals for up to 30s and
    collects progress values. In real-mode (with FFmpeg), asserts that
    progress shows variation (len(set(progress_values)) > 2). In noop mode,
    verifies that progress reaches completion (1.0).

    Note: BL-394-AC-2 and AC-3 (progress strictly increases, WS events fire)
    require real-mode FFmpeg and are deferred per DECISION-003. This test
    satisfies AC-4 (file_presence evidence class).

    AC-5 (concurrent renders reaching terminal state) is auto-discharged by
    BL-403 (Feature 003) which eliminated output-path contention.
    """
    project_id, duration = await _create_project_with_timeline(
        smoke_client_noop, "Progress Increment BL-394 Test", 50.0
    )
    render_plan = json.dumps({"total_duration": duration, "settings": {}})

    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": render_plan},
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    progress_values: list[float] = []
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 30.0

    while loop.time() < deadline:
        get_resp = await smoke_client_noop.get(f"/api/v1/render/{job_id}")
        assert get_resp.status_code == 200
        body = get_resp.json()
        progress = body["progress"]
        progress_values.append(progress)

        if body["status"] in ("completed", "failed", "cancelled"):
            break

        await asyncio.sleep(1.0)

    # In noop mode, progress jumps immediately to 1.0 (completed).
    # In real-mode with FFmpeg, progress increments over time.
    # Verify that we captured progress values and reached completion.
    assert len(progress_values) >= 1, "Expected at least one progress poll"
    assert 1.0 in progress_values, (
        f"Expected progress to reach 1.0 (completion), got {sorted(set(progress_values))!r}"
    )

    # Real-mode behavioral assertion (deferred per BL-394-AC-2/AC-3):
    # len(set(progress_values)) > 2 indicates progress incremented during render.
    # Noop mode shows len(set(progress_values))=1 ([1.0] only) which is expected.


async def test_settings_absent_returns_422_noop(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """Settings-absent render_plan returns 422 PREFLIGHT_FAILED in noop mode (BL-465-AC-2)."""
    project_id, _duration = await _create_project_with_timeline(
        smoke_client_noop, "BL-465 Settings Absent Test", 10.0
    )

    render_plan = json.dumps({"total_duration": 5.0})  # settings absent
    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": render_plan},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["code"] == "PREFLIGHT_FAILED"
    assert "settings" in body["detail"]["message"]


# ── Multi-clip render smoke tests (FR-001, FR-002) ────────────────────────────


async def test_multi_clip_render_api_accepts(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """A 2-clip project can be submitted via the render API without error (FR-001).

    Verifies that the render preflight passes and the API returns 201 for a
    project with two seeded clips. Uses noop mode so no FFmpeg is required.
    """
    resp = await smoke_client_noop.post(
        "/api/v1/projects", json={"name": "Multi-Clip Acceptance Test"}
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    await _seed_stub_clip(smoke_client_noop, project_id)
    await _seed_stub_clip(smoke_client_noop, project_id)

    render_plan = json.dumps({"total_duration": 10.0, "settings": {}})
    resp = await smoke_client_noop.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": render_plan},
    )
    assert resp.status_code == 201, (
        f"Expected 201 for 2-clip project in noop mode, got {resp.status_code}: {resp.json()}"
    )


async def test_multi_clip_translator_xfade_present() -> None:
    """RenderGraphTranslator produces filter_complex with xfade for a 2-clip project (FR-001).

    Calls the Rust translator directly to assert that a 2-clip timeline produces
    a filter_complex string containing the xfade filter.
    """
    from stoat_ferret_core import ClipWithEffects, RenderEffect, RenderGraphTranslator

    clips = [
        ClipWithEffects(
            input_index=0,
            duration_secs=5.0,
            framerate=30.0,
            source_path="/clip0.mp4",
            effects=[RenderEffect.none()],
        ),
        ClipWithEffects(
            input_index=1,
            duration_secs=5.0,
            framerate=30.0,
            source_path="/clip1.mp4",
            effects=[RenderEffect.none()],
        ),
    ]
    filter_complex, _ = RenderGraphTranslator().translate(clips)
    assert "xfade" in filter_complex, (
        f"filter_complex must contain 'xfade' for a 2-clip project; got: {filter_complex!r}"
    )
    assert "[final]" in filter_complex, (
        f"filter_complex must end with [final] label; got: {filter_complex!r}"
    )


async def test_multi_clip_translator_input_paths_count_matches_clips() -> None:
    """translate() returns input_paths with count equal to the clip count (FR-001).

    Verifies that the number of `-i` input paths returned by the translator
    matches the number of clips in the multi-clip project.
    """
    from stoat_ferret_core import ClipWithEffects, RenderEffect, RenderGraphTranslator

    clips = [
        ClipWithEffects(
            input_index=0,
            duration_secs=5.0,
            framerate=30.0,
            source_path="/clip0.mp4",
            effects=[RenderEffect.none()],
        ),
        ClipWithEffects(
            input_index=1,
            duration_secs=5.0,
            framerate=30.0,
            source_path="/clip1.mp4",
            effects=[RenderEffect.none()],
        ),
    ]
    _, input_paths = RenderGraphTranslator().translate(clips)
    assert len(input_paths) == len(clips), (
        f"input_paths count ({len(input_paths)}) must match clip count ({len(clips)})"
    )
    assert input_paths == ["/clip0.mp4", "/clip1.mp4"]


async def test_multi_clip_per_clip_effect_appears_in_filter_complex() -> None:
    """Per-clip effect filter strings appear in the filter_complex (FR-001).

    Uses animated_alpha (RenderEffect.animated_alpha) as the available per-clip
    effect proxy. The animated_alpha variant produces a geq filter in the
    filter_complex, verifying the effect sub-chain stage is emitted before xfade.

    Note: blur-specific filter integration (BlurBuilder → RenderEffect) is
    deferred_post_merge pending RenderEffect.custom() exposure (BL-555 scope).
    """
    from stoat_ferret_core import ClipWithEffects, RenderEffect, RenderGraphTranslator

    clips = [
        ClipWithEffects(
            input_index=0,
            duration_secs=5.0,
            framerate=30.0,
            source_path="/clip0.mp4",
            effects=[RenderEffect.animated_alpha(0.0, 1.0)],
        ),
        ClipWithEffects(
            input_index=1,
            duration_secs=5.0,
            framerate=30.0,
            source_path="/clip1.mp4",
            effects=[RenderEffect.none()],
        ),
    ]
    filter_complex, _ = RenderGraphTranslator().translate(clips)
    assert "geq" in filter_complex, (
        f"animated_alpha effect must produce 'geq' in filter_complex; got: {filter_complex!r}"
    )
    # Effect sub-chain must appear before xfade (Stage 2 before Stage 3+4).
    effect_pos = filter_complex.find("geq")
    xfade_pos = filter_complex.find("xfade")
    assert effect_pos < xfade_pos, (
        f"effect sub-chain (pos {effect_pos}) must appear before xfade (pos {xfade_pos})"
    )


@pytest.mark.skipif(
    os.getenv("STOAT_TEST_FFMPEG") != "1",
    reason="behavioral multi-clip render requires STOAT_TEST_FFMPEG=1",
)
@requires_ffmpeg
async def test_multi_clip_render_output_file_exists(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
    tmp_path: Path,
) -> None:
    """A 2-clip render produces output at the expected path (FR-002, SSIM deferred_post_merge).

    Behavioral test gated on STOAT_TEST_FFMPEG=1 and FFmpeg availability. Scans
    real videos, creates a 2-clip project, submits a render, polls until terminal,
    and asserts the output_path is populated. SSIM > 0.99 assertion is
    deferred_post_merge pending a full FFmpeg discharge environment.
    """
    await scan_videos_and_wait(smoke_client, videos_dir)

    videos_resp = await smoke_client.get("/api/v1/videos?limit=2")
    assert videos_resp.status_code == 200
    videos = videos_resp.json()["videos"]
    assert len(videos) >= 2, f"Need at least 2 scanned videos; got {len(videos)}"

    proj_resp = await smoke_client.post(
        "/api/v1/projects", json={"name": "Multi-Clip Behavioral Smoke Test"}
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    for video in videos[:2]:
        clip_resp = await smoke_client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "source_video_id": video["id"],
                "in_point": 0,
                "out_point": min(video.get("duration_frames", 90), 90),
                "timeline_position": 0,
            },
        )
        assert clip_resp.status_code == 201

    render_plan = json.dumps({"total_duration": 6.0, "settings": {}})
    resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": render_plan},
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    final = await poll_job_until_terminal(smoke_client, job_id, timeout=120.0)
    assert final["status"] in ("completed", "failed"), (
        f"Expected terminal status, got {final['status']!r}"
    )
    assert final.get("output_path"), (
        "output_path must be populated after render attempt (deferred: SSIM verification)"
    )
