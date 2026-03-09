# Sample Project — Smoke Test Integration

## Integration Strategy

The smoke test suite and the sample project are related but serve different purposes:

- **Smoke tests (UC-1 through UC-12):** Each test creates its own minimal, isolated data to verify a specific API behavior. Tests are independent and can run in any order.
- **Sample project (`sample_project` fixture):** Creates the full "Running Montage" project with all 4 clips, 5 effects, and 1 transition. Available as an optional fixture for tests that need a realistic, fully-configured project.

## The `sample_project` Fixture

Defined in `tests/smoke/conftest.py`, this async fixture mirrors the seed script constants exactly:

```python
@pytest.fixture()
async def sample_project(smoke_client, videos_dir):
    """
    Create the full 'Running Montage' sample project.
    Returns a dict with project, clips, video_ids for complex test scenarios.
    """
    client = smoke_client

    # Scan videos
    await scan_videos_and_wait(client, videos_dir)

    # Resolve video IDs
    resp = await client.get("/api/v1/videos?limit=100")
    videos = resp.json()["videos"]
    name_to_id = {v["filename"]: v["id"] for v in videos}

    sample_videos = [
        "78888-568004778_medium.mp4",
        "running1.mp4",
        "running2.mp4",
        "81872-577880797_medium.mp4",
    ]
    video_ids = [name_to_id[fn] for fn in sample_videos]

    # Create project at 1280x720 @ 30fps
    resp = await client.post("/api/v1/projects", json={
        "name": "Running Montage",
        "output_width": 1280,
        "output_height": 720,
        "output_fps": 30,
    })
    project = resp.json()
    project_id = project["id"]

    # Add 4 clips (values are integer frame counts)
    clip_defs = [
        (0, 60, 300, 0),
        (1, 90, 540, 300),
        (2, 30, 360, 750),
        (3, 150, 450, 1080),
    ]
    clip_ids = []
    for vid_idx, in_pt, out_pt, tl_pos in clip_defs:
        resp = await client.post(f"/api/v1/projects/{project_id}/clips", json={
            "source_video_id": video_ids[vid_idx],
            "in_point": in_pt,
            "out_point": out_pt,
            "timeline_position": tl_pos,
        })
        clip_ids.append(resp.json()["id"])

    # Apply 5 effects
    effect_defs = [
        (0, "fade", {"type": "in", "start_time": 0.0, "duration": 1.0}),
        (0, "drawtext", {"text": "Running Montage", "fontsize": 64, "fontcolor": "white"}),
        (1, "speed", {"factor": 0.75}),
        (3, "drawtext", {"text": "The End", "fontsize": 48, "fontcolor": "white"}),
        (3, "fade", {"type": "out", "start_time": 8.0, "duration": 2.0}),
    ]
    for clip_idx, effect_type, params in effect_defs:
        await client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_ids[clip_idx]}/effects",
            json={"effect_type": effect_type, "parameters": params},
        )

    # Apply 1 transition (Clip 2 → Clip 3)
    await client.post(f"/api/v1/projects/{project_id}/effects/transition", json={
        "source_clip_id": clip_ids[1],
        "target_clip_id": clip_ids[2],
        "transition_type": "fade",
        "parameters": {"duration": 1.0},
    })

    return {
        "project": project,
        "project_id": project_id,
        "video_ids": video_ids,
        "clip_ids": clip_ids,
    }
```

## Decision: Independent Data for UC-1 through UC-12

The 12 smoke test cases (UC-1 through UC-12) each create their own data independently. They do **not** use the `sample_project` fixture.

### Rationale

1. **Isolation prevents cascading failures.** If the scan step fails, only scan-dependent tests fail — not every test in the suite. With a shared sample project, a single failure in project creation would cascade to all 12 tests.

2. **Each test's setup is visible in its body.** A developer reading `test_uc05_apply_video_effect` can see exactly what data it creates and what it depends on. There is no hidden state from fixtures that must be traced to understand the test.

3. **Parallel execution is safe.** Independent tests can run in parallel (e.g., via `pytest-xdist`) without coordination. Each test has its own database via `tmp_path`.

4. **Minimal data per test.** UC-8 (health check) needs no data at all. UC-3 (create project) needs only a project. Using the full sample project for every test would waste time on unnecessary setup.

## When to Use the `sample_project` Fixture

The `sample_project` fixture is reserved for tests that genuinely need a fully-configured project:

| Test Category | Approach | Rationale |
|--------------|----------|-----------|
| UC-1 through UC-12 | Independent data per test | Each test verifies a specific behavior; minimal setup needed |
| Future render tests | `sample_project` fixture | Render requires a complete project with clips, effects, transitions |
| Future export tests | `sample_project` fixture | Export requires a realistic composition |
| Regression tests | `sample_project` fixture | Verify the full project structure matches the canonical definition |
| Performance benchmarks | `sample_project` fixture | Need a realistic workload for timing measurements |

## Keeping the Fixture in Sync

The `sample_project` fixture must use the exact same constants as the seed script (`scripts/seed_sample_project.py`). When the project definition changes:

1. Update `CLIP_DEFS`, `EFFECT_DEFS`, and `TRANSITION_DEFS` in the seed script
2. Update the corresponding values in the `sample_project` fixture
3. Update the project definition document (`docs/design/sample_project/01-project-definition.md`)

The "Sample Project Compatibility" impact assessment check (defined in `docs/design/smoke_test/05-maintenance.md`) flags changes that might affect this synchronization.
