"""Regression smoke test for the Running Montage sample project (BL-128, BL-239).

Validates that the complete sample project structure — project metadata,
clip frame values, and effect-to-clip mappings — matches canonical definitions,
and that a render job can be queued for the sample project.
"""

from __future__ import annotations

from typing import Any

import httpx

from tests.smoke.conftest import SAMPLE_EFFECT_DEFS


async def test_sample_project_structure(
    smoke_client: httpx.AsyncClient,
    sample_project: dict[str, Any],
) -> None:
    """Verify the Running Montage sample project matches canonical definitions.

    Asserts project metadata (name, output settings), clip count and frame
    values, source video associations, effect-to-clip mappings, and render
    job queueing (BL-239).
    """
    client = smoke_client
    project_id = sample_project["project_id"]
    project = sample_project["project"]

    # --- FR-002: Project metadata ---
    assert project["name"] == "Running Montage"
    assert project["output_width"] == 1280
    assert project["output_height"] == 720
    assert project["output_fps"] == 30

    # --- FR-003 & FR-004: Clip assertions ---
    resp = await client.get(f"/api/v1/projects/{project_id}/clips")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 4

    # Sort clips by timeline_position for deterministic ordering
    clips = sorted(body["clips"], key=lambda c: c["timeline_position"])

    # Canonical frame values: (video_index, in_point, out_point, timeline_position)
    expected_frame_values = [
        (0, 60, 300, 0),
        (1, 90, 540, 300),
        (2, 30, 360, 750),
        (3, 150, 450, 1080),
    ]

    expected_videos = [
        "78888-568004778_medium.mp4",
        "running1.mp4",
        "running2.mp4",
        "81872-577880797_medium.mp4",
    ]

    # Map video IDs to filenames for source video assertions
    resp = await client.get("/api/v1/videos?limit=100")
    videos = resp.json()["videos"]
    id_to_filename = {v["id"]: v["filename"] for v in videos}

    for i, clip in enumerate(clips):
        vid_idx, in_pt, out_pt, tl_pos = expected_frame_values[i]

        assert clip["in_point"] == in_pt, (
            f"Clip {i} in_point: expected {in_pt}, got {clip['in_point']}"
        )
        assert clip["out_point"] == out_pt, (
            f"Clip {i} out_point: expected {out_pt}, got {clip['out_point']}"
        )
        assert clip["timeline_position"] == tl_pos, (
            f"Clip {i} timeline_position: expected {tl_pos}, got {clip['timeline_position']}"
        )

        # Source video association
        filename = id_to_filename[clip["source_video_id"]]
        assert filename == expected_videos[vid_idx], (
            f"Clip {i} source video: expected {expected_videos[vid_idx]}, got {filename}"
        )

    # --- FR-005: Effect assertions ---
    # Build expected effect map: clip_index -> list of (effect_type, key params)
    expected_effects: dict[int, list[tuple[str, dict[str, Any]]]] = {}
    for clip_idx, effect_type, params in SAMPLE_EFFECT_DEFS:
        expected_effects.setdefault(clip_idx, []).append((effect_type, params))

    for i, clip in enumerate(clips):
        clip_effects = clip.get("effects") or []
        if i in expected_effects:
            expected = expected_effects[i]
            assert len(clip_effects) == len(expected), (
                f"Clip {i}: expected {len(expected)} effects, got {len(clip_effects)}"
            )
            # Sort both by effect_type for stable comparison
            actual_sorted = sorted(clip_effects, key=lambda e: e["effect_type"])
            expected_sorted = sorted(expected, key=lambda e: e[0])
            for actual, (exp_type, _exp_params) in zip(actual_sorted, expected_sorted, strict=True):
                assert actual["effect_type"] == exp_type, (
                    f"Clip {i}: expected effect {exp_type}, got {actual['effect_type']}"
                )
        else:
            assert len(clip_effects) == 0, f"Clip {i}: expected no effects, got {len(clip_effects)}"

    # --- BL-239: Render job queueing ---
    # Asserts status=="queued" only — the render background worker
    # (RenderQueue.dequeue) is not wired to FastAPI lifespan, so jobs remain
    # queued indefinitely in test mode. Output file existence is not asserted.
    # See BL-239 design investigation (comms/outbox/versions/design/v034/).
    render_resp = await client.post(
        "/api/v1/render",
        json={"project_id": project_id},
    )
    assert render_resp.status_code == 201
    render_data = render_resp.json()
    assert render_data["status"] == "queued"
    assert render_data["id"]  # non-empty string
