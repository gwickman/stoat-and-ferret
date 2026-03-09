# Smoke Test Case Specifications

All 12 test cases are specified below. Each test is self-contained — it performs its own setup (scan, project creation, etc.) within the test body using the helper functions from `conftest.py`. No test depends on state from another test.

**Important:** Clip `in_point`, `out_point`, and `timeline_position` are **integer frame counts**, not floating-point seconds. The API schemas (`ClipCreate`, `ClipUpdate`, `ClipResponse`) define these as `int` fields with `ge=0` constraints.

---

## UC-1: Scan a Video Directory

**Test function:** `test_uc01_scan_video_directory`
**File:** `test_scan_workflow.py`

**Setup:** `smoke_client`, `videos_dir` fixtures

**Steps:**

1. Submit scan:
   - `POST /api/v1/videos/scan`
   - Body: `{"path": "<videos_dir>", "recursive": true}`
   - Assert: status 202
   - Assert: response has `job_id` (non-empty string)

2. Poll until terminal:
   - `GET /api/v1/jobs/{job_id}` (via `poll_job_until_terminal` helper)
   - Assert: final `status` is `"complete"`

3. List scanned videos:
   - `GET /api/v1/videos?limit=100`
   - Assert: status 200
   - Assert: `total` == 6
   - Assert: `videos` list has length 6
   - For each video, assert:
     - `filename` is one of the 6 expected filenames in `EXPECTED_VIDEOS`
     - `width` and `height` match expected values
     - `video_codec` == `"h264"`
     - `audio_codec` == `"aac"`
     - `duration_frames` > 0
     - `frame_rate_numerator` and `frame_rate_denominator` match expected `fps_num` / `fps_den`
     - `file_size` > 0
     - `id` is a non-empty string
     - `path` ends with the filename

**Dependency ordering:** None — this is a root test.

---

## UC-2: Search and Browse the Video Library

**Test function:** `test_uc02_search_browse_library`
**File:** `test_library.py`

**Setup:** `smoke_client`, `videos_dir`. Scan runs within the test body.

**Steps:**

1. Setup scan:
   - `scan_videos_and_wait(client, videos_dir)`

2. Browse all:
   - `GET /api/v1/videos?limit=20&offset=0`
   - Assert: status 200
   - Assert: `total` == 6
   - Assert: `limit` == 20, `offset` == 0
   - Assert: `videos` has length 6

3. Pagination (page 1):
   - `GET /api/v1/videos?limit=2&offset=0`
   - Assert: `videos` has length 2
   - Assert: `total` == 6

4. Pagination (page 2):
   - `GET /api/v1/videos?limit=2&offset=2`
   - Assert: `videos` has length 2
   - Assert: no overlap with page 1 video IDs

5. Search by name:
   - `GET /api/v1/videos/search?q=running&limit=100`
   - Assert: status 200
   - Assert: `total` == 2
   - Assert: both filenames contain the substring `"running"`

6. Search with no results:
   - `GET /api/v1/videos/search?q=nonexistent_xyz&limit=100`
   - Assert: `total` == 0
   - Assert: `videos` is empty list

---

## UC-3: Create a New Project

**Test function:** `test_uc03_create_new_project`
**File:** `test_project_workflow.py`

**Setup:** `smoke_client`

**Steps:**

1. Create with defaults:
   - `POST /api/v1/projects`
   - Body: `{"name": "Smoke Test Project"}`
   - Assert: status 201
   - Assert: `name` == `"Smoke Test Project"`
   - Assert: `output_width` == 1920 (default)
   - Assert: `output_height` == 1080 (default)
   - Assert: `output_fps` == 30 (default)
   - Assert: `id` is a non-empty string
   - Assert: `created_at` and `updated_at` are present

2. Create with custom settings:
   - `POST /api/v1/projects`
   - Body: `{"name": "Custom Output", "output_width": 1280, "output_height": 720, "output_fps": 60}`
   - Assert: status 201
   - Assert: `output_width` == 1280, `output_height` == 720, `output_fps` == 60

3. List projects:
   - `GET /api/v1/projects`
   - Assert: `total` == 2

4. Get by ID:
   - `GET /api/v1/projects/{id}` (using ID from step 1)
   - Assert: status 200
   - Assert: response matches step 1 response

5. Validation — empty name:
   - `POST /api/v1/projects`
   - Body: `{"name": ""}`
   - Assert: status 422 (pydantic validation: `min_length=1` on `name` field)

---

## UC-4: Add Clips to a Project

**Test function:** `test_uc04_add_clips_to_project`
**File:** `test_clip_workflow.py`

**Setup:** `smoke_client`, `videos_dir`. Scan and project creation run within the test body.

**Steps:**

1. Scan: `scan_videos_and_wait(client, videos_dir)`

2. Get video IDs:
   - `GET /api/v1/videos?limit=100`
   - Extract two video IDs (first two from the response list)

3. Create project:
   - `POST /api/v1/projects`
   - Body: `{"name": "Clip Test"}`

4. Add clip 1:
   - `POST /api/v1/projects/{project_id}/clips`
   - Body: `{"source_video_id": "<video_id_1>", "in_point": 0, "out_point": 150, "timeline_position": 0}`
   - Assert: status 201
   - Assert: `source_video_id` matches
   - Assert: `in_point` == 0, `out_point` == 150, `timeline_position` == 0
   - Assert: `id` is non-empty string
   - Assert: `project_id` matches

5. Add clip 2:
   - `POST /api/v1/projects/{project_id}/clips`
   - Body: `{"source_video_id": "<video_id_2>", "in_point": 30, "out_point": 300, "timeline_position": 150}`
   - Assert: status 201
   - Assert: `timeline_position` == 150

6. List clips:
   - `GET /api/v1/projects/{project_id}/clips`
   - Assert: status 200
   - Assert: `clips` list has length 2
   - Assert: `total` == 2

7. Invalid clip (out_point beyond video duration):
   - `POST /api/v1/projects/{project_id}/clips`
   - Body: `{"source_video_id": "<video_id_1>", "in_point": 0, "out_point": 999999, "timeline_position": 500}`
   - Assert: status 400 (Rust core validation error: `VALIDATION_ERROR`)

---

## UC-5: Apply a Video Effect

**Test function:** `test_uc05_apply_video_effect`
**File:** `test_effects.py`

**Setup:** `smoke_client`, `videos_dir`. Scan, project creation, and clip addition run within the test body.

**Steps:**

1. Setup: Scan videos, create project "Effect Test", add one clip (in_point=0, out_point=300, timeline_position=0)

2. List effects catalog:
   - `GET /api/v1/effects`
   - Assert: status 200
   - Assert: `total` > 0
   - Assert: response contains an effect where `effect_type` == `"drawtext"`
   - Assert: each effect has `name`, `description`, `parameter_schema`, `ai_hints`, `filter_preview`

3. Preview effect:
   - `POST /api/v1/effects/preview`
   - Body: `{"effect_type": "drawtext", "parameters": {"text": "Hello Smoke Test", "fontsize": 48, "fontcolor": "white"}}`
   - Assert: status 200
   - Assert: `filter_string` contains `"drawtext"`
   - Assert: `filter_string` contains `"Hello Smoke Test"` (possibly with escaping)
   - Assert: `effect_type` == `"drawtext"`

4. Apply effect:
   - `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects`
   - Body: `{"effect_type": "drawtext", "parameters": {"text": "Title Card", "fontsize": 64, "fontcolor": "yellow"}}`
   - Assert: status 201
   - Assert: `effect_type` == `"drawtext"`
   - Assert: `filter_string` contains `"drawtext"`
   - Assert: `filter_string` contains `"Title Card"` (possibly with escaping)
   - Assert: `parameters` matches input

5. Verify on clip:
   - `GET /api/v1/projects/{project_id}/clips`
   - Assert: clip's `effects` list has length 1

---

## UC-6: Edit and Remove an Effect

**Test function:** `test_uc06_edit_and_remove_effect`
**File:** `test_effects.py`

**Setup:** `smoke_client`, `videos_dir`. Same setup as UC-5 through step 4 (clip with one drawtext effect).

**Steps:**

1. Setup: Scan, create project, add clip, apply drawtext effect (reuse pattern from UC-5)

2. Update effect:
   - `PATCH /api/v1/projects/{project_id}/clips/{clip_id}/effects/0`
   - Body: `{"parameters": {"text": "Updated Title", "fontsize": 72, "fontcolor": "red"}}`
   - Assert: status 200
   - Assert: `filter_string` contains `"Updated Title"`
   - Assert: `filter_string` contains `"drawtext"`

3. Delete effect:
   - `DELETE /api/v1/projects/{project_id}/clips/{clip_id}/effects/0`
   - Assert: status 200
   - Assert: `index` == 0
   - Assert: `deleted_effect_type` == `"drawtext"`

4. Verify removal:
   - `GET /api/v1/projects/{project_id}/clips`
   - Assert: clip's `effects` list is empty (length 0) or `null`

---

## UC-7: Apply a Transition Between Clips

**Test function:** `test_uc07_apply_transition`
**File:** `test_transitions.py`

**Setup:** `smoke_client`, `videos_dir`. Scan, project creation, and two clip additions run within the test body.

**Steps:**

1. Setup: Scan videos, create project "Transition Test", add two adjacent clips:
   - Clip 1: in_point=0, out_point=150, timeline_position=0
   - Clip 2: in_point=0, out_point=150, timeline_position=150

2. Apply crossfade transition:
   - `POST /api/v1/projects/{project_id}/effects/transition`
   - Body:
     ```json
     {
       "source_clip_id": "<clip_id_1>",
       "target_clip_id": "<clip_id_2>",
       "transition_type": "fade",
       "parameters": {"duration": 1.0}
     }
     ```
   - Assert: status 201
   - Assert: `source_clip_id` == clip_id_1
   - Assert: `target_clip_id` == clip_id_2
   - Assert: `transition_type` == `"fade"`
   - Assert: `filter_string` is a non-empty string
   - Assert: `filter_string` contains `"xfade"` (the FFmpeg crossfade filter)

---

## UC-8: Monitor System Health

**Test function:** `test_uc08_monitor_system_health`
**File:** `test_health.py`

**Setup:** `smoke_client`

**Steps:**

1. Liveness probe:
   - `GET /health/live`
   - Assert: status 200
   - Assert: body == `{"status": "ok"}`

2. Readiness probe:
   - `GET /health/ready`
   - Assert: status 200
   - Assert: `status` == `"ok"`
   - Assert: `checks` has key `"database"`
   - Assert: `checks` has key `"ffmpeg"`
   - Assert: `checks.database.status` == `"ok"`
   - Assert: `checks.database.latency_ms` is a number >= 0
   - Assert: `checks.ffmpeg.status` == `"ok"`
   - Assert: `checks.ffmpeg.version` is a non-empty string

**Note:** Health endpoints use the `/health/` prefix (not `/api/v1/health/`). This matches the router configuration in `src/stoat_ferret/api/routers/health.py`.

---

## UC-9: Delete a Project

**Test function:** `test_uc09_delete_project`
**File:** `test_project_workflow.py`

**Setup:** `smoke_client`

**Steps:**

1. Create project:
   - `POST /api/v1/projects`
   - Body: `{"name": "To Be Deleted"}`
   - Assert: status 201
   - Record `project_id`

2. Verify exists:
   - `GET /api/v1/projects/{project_id}`
   - Assert: status 200

3. Delete:
   - `DELETE /api/v1/projects/{project_id}`
   - Assert: status 204

4. Verify deleted:
   - `GET /api/v1/projects/{project_id}`
   - Assert: status 404

5. Double delete (idempotency check):
   - `DELETE /api/v1/projects/{project_id}`
   - Assert: status 404

---

## UC-10: Modify Clip Timing

**Test function:** `test_uc10_modify_clip_timing`
**File:** `test_clip_workflow.py`

**Setup:** `smoke_client`, `videos_dir`. Scan, project creation, and clip addition run within the test body.

**Steps:**

1. Setup: Scan videos, create project, add clip with in_point=0, out_point=300, timeline_position=0

2. Update in/out points:
   - `PATCH /api/v1/projects/{project_id}/clips/{clip_id}`
   - Body: `{"in_point": 30, "out_point": 200}`
   - Assert: status 200
   - Assert: `in_point` == 30
   - Assert: `out_point` == 200
   - Assert: `timeline_position` == 0 (unchanged)

3. Update timeline position:
   - `PATCH /api/v1/projects/{project_id}/clips/{clip_id}`
   - Body: `{"timeline_position": 50}`
   - Assert: status 200
   - Assert: `timeline_position` == 50
   - Assert: `in_point` == 30 (unchanged from step 2)

4. Delete clip:
   - `DELETE /api/v1/projects/{project_id}/clips/{clip_id}`
   - Assert: status 204

5. Verify deleted:
   - `GET /api/v1/projects/{project_id}/clips`
   - Assert: `clips` list is empty, `total` == 0

---

## UC-11: Speed Control Effect

**Test function:** `test_uc11_speed_control_effect`
**File:** `test_effects.py`

**Setup:** `smoke_client`, `videos_dir`. Scan, project creation, and clip addition run within the test body.

**Steps:**

1. Setup: Scan videos, create project "Speed Test", add clip (in_point=0, out_point=300, timeline_position=0)

2. Preview speed effect:
   - `POST /api/v1/effects/preview`
   - Body: `{"effect_type": "speed", "parameters": {"factor": 0.5}}`
   - Assert: status 200
   - Assert: `filter_string` contains `"setpts"` (the FFmpeg speed filter for video)
   - Assert: `filter_string` contains `"PTS"` (part of the setpts expression)

3. Apply speed effect:
   - `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects`
   - Body: `{"effect_type": "speed", "parameters": {"factor": 0.75}}`
   - Assert: status 201
   - Assert: `effect_type` == `"speed"`
   - Assert: `filter_string` contains `"setpts"`

4. Apply a second effect (drawtext) to same clip:
   - `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects`
   - Body: `{"effect_type": "drawtext", "parameters": {"text": "Slow Motion", "fontsize": 36, "fontcolor": "white"}}`
   - Assert: status 201

5. Verify multiple effects:
   - `GET /api/v1/projects/{project_id}/clips`
   - Assert: clip's `effects` list has length 2

---

## UC-12: Cancel a Running Scan

**Test function:** `test_uc12_cancel_running_scan`
**File:** `test_scan_workflow.py`

**Setup:** `smoke_client`, `videos_dir`

**Steps:**

1. Submit scan:
   - `POST /api/v1/videos/scan`
   - Body: `{"path": "<videos_dir>", "recursive": true}`
   - Assert: status 202
   - Record `job_id`

2. Immediately attempt cancel:
   - `POST /api/v1/jobs/{job_id}/cancel`
   - Assert: status 200 **OR** status 409
   - If 200: job was cancelled successfully (it was still running when cancel arrived)
   - If 409: job already reached a terminal state before cancel was processed (race condition by design — the 6 small videos scan quickly)

3. If status was 200 (cancelled):
   - `GET /api/v1/jobs/{job_id}`
   - Assert: `status` is a terminal status (`"cancelled"` or `"complete"`)

4. Re-cancel (already terminal):
   - `POST /api/v1/jobs/{job_id}/cancel`
   - Assert: status 409 (`ALREADY_TERMINAL`)

5. Cancel non-existent job:
   - `POST /api/v1/jobs/nonexistent-id/cancel`
   - Assert: status 404

**Note:** This test explicitly handles the race condition between scan completion and cancellation. With only 6 small videos (~45 MB total), the scan often completes before the cancel request is processed. The test accepts either outcome. The key assertions are: (a) cancellation returns 200 when the job is still running, (b) re-cancellation of a terminal job returns 409, (c) cancelling a non-existent job returns 404.

---

## Dependency Ordering Summary

Each test is self-contained and creates its own data. No test depends on another test's state.

```
test_uc08 (health)          — no dependencies (can run first)
test_uc03 (create project)  — no dependencies
test_uc09 (delete project)  — no dependencies
test_uc12 (cancel scan)     — no dependencies
test_uc01 (scan)            — no dependencies
test_uc02 (library)         — scan runs within test body
test_uc04 (clips)           — scan + project within test body
test_uc10 (clip timing)     — scan + project + clip within test body
test_uc05 (effects)         — scan + project + clip within test body
test_uc06 (edit/remove fx)  — scan + project + clip + effect within test body
test_uc07 (transitions)     — scan + project + 2 clips within test body
test_uc11 (speed control)   — scan + project + clip within test body
```

| Test | Scan | Project | Clips | Effects | Notes |
|------|------|---------|-------|---------|-------|
| UC-1 | Within test | — | — | — | Root: validates scan |
| UC-2 | Within test | — | — | — | Depends on scan data |
| UC-3 | — | Within test | — | — | Root: validates project CRUD |
| UC-4 | Within test | Within test | Within test | — | Validates clip CRUD |
| UC-5 | Within test | Within test | Within test | Within test | Validates effect apply |
| UC-6 | Within test | Within test | Within test | Within test | Validates effect edit/remove |
| UC-7 | Within test | Within test | Within test (2) | — | Validates transitions |
| UC-8 | — | — | — | — | Root: no setup needed |
| UC-9 | — | Within test | — | — | Validates project delete |
| UC-10 | Within test | Within test | Within test | — | Validates clip update/delete |
| UC-11 | Within test | Within test | Within test | Within test | Validates speed + stacking |
| UC-12 | Within test | — | — | — | Validates cancel race |
