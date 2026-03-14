# Smoke Test Maintenance

## Trigger Table

When a change matches one of the triggers below, the corresponding smoke test update is required:

| Trigger | Required Action |
|---------|----------------|
| New API endpoint added in `src/stoat_ferret/api/routers/` | Add smoke test covering the endpoint, or document why it is excluded |
| Endpoint request/response schema changes in `src/stoat_ferret/api/schemas/` | Update assertions in the affected test(s) to match new field names, types, or constraints |
| New effect type registered in `EffectRegistry` via `src/stoat_ferret/effects/definitions.py` | Add preview + apply assertions in `test_effects.py` |
| New job type added to the job queue system | Add polling test similar to scan workflow in `test_scan_workflow.py` |
| Video files in `/videos/` added, removed, or replaced | Update `EXPECTED_VIDEOS` dict in `tests/smoke/conftest.py` |
| Video files change metadata (re-encoded with different codec/resolution) | Update `EXPECTED_VIDEOS` dict values for affected files |
| Clip schema fields change (new required field, renamed field) | Update clip creation/assertion code in `test_clip_workflow.py` and helpers |
| Health check adds new check (e.g., Redis check) | Update `test_health.py` assertions to verify the new check key |
| WebSocket event types change | Update WebSocket tests when implemented (Phase 3 Playwright) |
| Effect parameter schema changes (renamed param, new required param) | Update effect test bodies that reference specific parameter names/values |
| Timeline track schema changes (new track types, field renames) | Update `test_timeline.py` and `create_adjacent_clips_timeline()` helper |
| Timeline clip CRUD endpoint changes (PUT/POST/PATCH/DELETE) | Update `test_timeline.py` assertions and conftest helper |
| Filesystem endpoint changes (`/api/v1/filesystem/`) | Update `test_filesystem.py` assertions |
| Video detail/thumbnail/delete endpoint changes | Update `test_library.py` (video detail, thumbnail, delete tests) |
| Version restore endpoint changes (`/versions/{id}/restore`) | Update `test_versions.py` and `create_version_repo()` factory |
| Composition preset schema changes | Update `test_compose.py` assertions |
| Audio mix endpoint changes | Update `test_audio.py` assertions |
| Batch endpoint changes | Update `test_batch.py` assertions |

## Keeping `EXPECTED_VIDEOS` in Sync

The `EXPECTED_VIDEOS` dictionary in `tests/smoke/conftest.py` is the single source of truth for video file metadata used in smoke test assertions. It contains per-file entries with:

- `duration_seconds` — approximate duration for reference
- `width`, `height` — pixel dimensions
- `fps_num`, `fps_den` — rational frame rate (numerator/denominator)
- `video_codec`, `audio_codec` — codec identifiers
- `frames` — total frame count

### When `/videos/` Changes

If video files in the `/videos/` directory are added, removed, or replaced:

1. Run `ffprobe` on each changed video to get updated metadata:
   ```bash
   ffprobe -v quiet -print_format json -show_streams -show_format <video_file>
   ```
2. Update the corresponding entry in `EXPECTED_VIDEOS`
3. If a video was removed, remove its entry
4. If a video was added, add a new entry
5. Update the video metadata table in `docs/design/smoke_test/01-background.md`
6. Update the sample project definition if it references affected videos

### Detection

The "Test Video Fixture Assumptions" impact assessment check (see below) flags changes to the `/videos/` directory during design review.

## What Happens When a New API Endpoint Is Added

Convention: when a new API endpoint is added or an existing endpoint's contract changes:

1. **If the endpoint corresponds to an existing use case:** Update the relevant smoke test in the appropriate test file. Refer to the endpoint coverage map in `03-test-cases.md` to identify which file(s) cover the endpoint.
2. **If the endpoint introduces new functionality:** Add a new smoke test function in the appropriate file, or create a new test file if the domain is new.
3. **Document in the PR:** Include a note: "Smoke test updated for [endpoint]" or "Smoke test added for [endpoint]" or "No smoke test needed: [reason]".

## Impact Assessment Checks

The following three checks are designed for the project's impact assessment process. They flag design-time issues that could cause smoke test failures or sample project staleness.

### 1. Smoke Test Coverage Gaps

**What to look for:**
Versions that add or modify API endpoint routes in `src/stoat_ferret/api/routers/`. When a new endpoint is implemented, verify that a corresponding smoke test exists in `tests/smoke/` or is explicitly planned in a backlog item.

**Grep patterns:**
- `@router\.(get|post|put|patch|delete)\(` in `src/stoat_ferret/api/routers/`
- `async def test_` in `tests/smoke/`

**Cross-reference:** For each route path found in the routers, check if a smoke test makes an HTTP call to that path. If no smoke test references the path, flag it as a coverage gap.

**Why it matters:**
Smoke tests are the project's primary API-level regression safety net. If a new endpoint is added without a corresponding smoke test, regressions in that endpoint will not be caught until manual testing or user-reported bugs. The cost of adding a smoke test at implementation time is low; the cost of a missed regression in production is high.

**Concrete example:**
Suppose a future version adds `POST /api/v1/projects/{project_id}/render` for render queue functionality. Without this check, the endpoint could ship with unit tests but no smoke test. A later version might change the job queue behavior, breaking the render endpoint in a way that unit tests (which use mocked job queues) don't catch. This check would flag: "New route `/api/v1/projects/{project_id}/render` has no corresponding smoke test in `tests/smoke/`."

### 2. Sample Project Compatibility

**What to look for:**
Versions that add new effect types to the EffectRegistry, new clip operations (e.g., trim, split), new project fields, or new transition types. When identified, verify that:
1. The sample project seed script (`scripts/seed_sample_project.py`) is updated to demonstrate the new feature, OR a decision is documented for why the sample project should not include it.
2. The sample project guide (`docs/setup/guides/sample-project.md`) is updated if the sample project changes.

**Grep patterns:**
- New entries in effect registry: `register\(` or `EffectType\.` in `src/stoat_ferret/`
- New clip fields: changes to `ClipCreate`, `ClipUpdate`, `ClipResponse` schemas in `src/stoat_ferret/api/schemas/`
- New project fields: changes to `ProjectCreate`, `ProjectResponse` schemas
- New transition types: additions to `TransitionType` enum in the Rust core

**Why it matters:**
The sample project is the canonical example of what stoat-and-ferret can do. If a new effect type is added but the sample project doesn't showcase it, new developers won't discover the feature through the standard onboarding flow. Keeping the sample project up-to-date ensures it remains a comprehensive, living reference.

**Concrete example:**
Suppose a version adds a new `color_grade` effect type with parameters for brightness, contrast, and saturation. Without this check, the EffectRegistry gains a new entry, the API endpoint works, but the sample project seed script still only demonstrates `drawtext`, `fade`, and `speed`. A developer onboarding to the project would never see `color_grade` in action without reading the API docs. This check would flag: "New effect type `color_grade` registered — consider adding it to the sample project seed script."

### 3. Test Video Fixture Assumptions

**What to look for:**
Code in `tests/smoke/` or `scripts/seed_sample_project.py` that makes assertions or assumptions about specific video file properties: duration, resolution, frame count, frame rate, codec, or file size. Also check if any video files in `/videos/` have been added, removed, or replaced.

**Grep patterns:**
- Hardcoded video metadata: `duration`, `width`, `height`, `frames`, `fps` followed by numeric literals in `tests/smoke/conftest.py`
- Video filename references: literal `.mp4` filenames in `tests/smoke/` and `scripts/`
- Changes to `/videos/` directory: `git diff --name-only` showing additions/deletions in `videos/`

**Why it matters:**
Smoke tests and the seed script encode specific assumptions about video file metadata (e.g., `running1.mp4` has 888 frames at 30fps and is 960x540). If a video file is replaced with a different version (different duration, resolution, or codec), tests will fail with confusing assertion errors that appear unrelated to the actual change.

**Concrete example:**
Suppose a developer replaces `running1.mp4` with a higher-quality version that is 1920x1080 at 60fps instead of 960x540 at 30fps. The smoke test `EXPECTED_VIDEOS` dict still says `"width": 960, "height": 540, "frames": 888`. The scan test passes (scanning succeeds), but the metadata assertion `assert video["width"] == 960` fails. Without this check, the developer must trace the failure back to the changed video file. With this check, the design review flags: "Video file `running1.mp4` changed — verify that `EXPECTED_VIDEOS` in `tests/smoke/conftest.py` and clip definitions in `scripts/seed_sample_project.py` are updated to match the new metadata."
