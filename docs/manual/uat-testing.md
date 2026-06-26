# UAT Testing Guide

## What is UAT testing?

The UAT (User Acceptance Testing) framework validates complete user journeys through the stoat-and-ferret application by driving a real browser against a live server instance. Unlike API-level smoke tests that exercise individual endpoints, UAT tests simulate what an actual user does: navigating pages, clicking buttons, filling forms, and verifying that the GUI renders the correct data.

Each UAT test is a **journey script** — a Playwright-based Python script that walks through a specific user workflow end-to-end. The framework captures screenshots at each step, collects browser console errors, and generates structured pass/fail reports.

## Prerequisites

### 1. Install UAT dependencies

The UAT dependencies (Playwright) are declared as an optional dependency group:

```bash
uv pip install -e ".[uat]"
```

### 2. Install the Chromium browser binary

Playwright requires a browser binary. Install Chromium via uv (do not call `playwright` directly — it is inside uv's virtual environment and won't be on your PATH):

```bash
uv run playwright install chromium
```

### 3. Build the application

The UAT runner can build everything automatically, but if you want to run against an already-running server you need:

- **Rust core** built (`maturin develop` from project root)
- **Python package** installed (`pip install -e .`)
- **GUI** built (`cd gui && npm ci && npm run build`)
- **Server running** on `http://localhost:8765`

## Running UAT tests interactively (headed mode)

Headed mode opens a visible browser window so you can watch each journey execute step by step. This is useful for debugging failures or understanding what a journey does.

### Full build-boot-test cycle

This builds everything, starts the server, seeds sample data, runs all journeys, then tears down:

```bash
uv run python scripts/uat_runner.py --headed
```

### Against a running server

If the server is already running on port 8765, skip the build/boot phases:

```bash
uv run python scripts/uat_runner.py --headed --skip-build
```

### Run a single journey

To run only one journey (e.g. journey 201):

```bash
uv run python scripts/uat_runner.py --headed --journey 201
```

Combine with `--skip-build` if the server is already up:

```bash
uv run python scripts/uat_runner.py --headed --journey 201 --skip-build
```

## Running UAT tests headlessly

Headless mode runs the browser without a visible window. Use this for CI pipelines or quick validation.

### Full build-boot-test cycle

```bash
uv run python scripts/uat_runner.py --headless
```

### Pre-built artifacts (CI mode)

If you have already built the Rust module, installed Python packages, and built the GUI, use `--no-build` to skip those steps while still having the runner start and manage the server for you:

```bash
uv run python scripts/uat_runner.py --headless --no-build
```

This is the mode used by the CI UAT job. CI pre-builds everything in explicit steps, then calls the runner with `--no-build` so the full budget is available for the server and journeys.

### Against a running server

```bash
uv run python scripts/uat_runner.py --headless --skip-build
```

### Custom output directory

By default, results are written to `testing-evidence/uat-evidence/` in the project root. Override with:

```bash
uv run python scripts/uat_runner.py --headless --output-dir ./my-results
```

## Understanding the results

### Output directory structure

Each run creates a timestamped subdirectory under the output base:

```
testing-evidence/uat-evidence/
└── 20260318_143022/          # Timestamped run directory
    ├── uat-report.json       # Machine-readable structured report
    ├── uat-report.md         # Human-readable markdown report
    ├── scan-library/         # Journey 201 screenshots
    │   ├── 01_initial_page.png
    │   ├── 02_scan_triggered.png
    │   └── ...
    ├── project-clip/         # Journey 202 screenshots
    │   └── ...
    ├── effects-timeline/     # Journey 203 screenshots
    │   └── ...
    └── export-render/        # Journey 204 screenshots
        └── ...
```

### Report files

**`uat-report.json`** contains structured data for each journey:

```json
{
  "timestamp": "2026-03-18T14:30:22+00:00",
  "mode": "headless",
  "duration_seconds": 45.3,
  "overall_status": "pass",
  "journeys": [
    {
      "name": "scan-library",
      "journey_id": 201,
      "status": "passed",
      "steps_total": 5,
      "steps_passed": 5,
      "steps_failed": 0,
      "console_errors": [],
      "issues": []
    }
  ]
}
```

**`uat-report.md`** is a human-readable summary with a table of journey results and details for any failures.

### Interpreting pass/fail

- **passed** — All steps in the journey completed and assertions held.
- **failed** — At least one step failed an assertion or threw an error. Check the journey's screenshot directory and the report for details.
- **skipped** — The journey was skipped because a prerequisite journey failed. Journeys have a dependency chain: 201 → 202 → 203 (journey 204 is independent). If 201 fails, 202 and 203 are automatically skipped.

### Known Failure Registry

Some UAT journeys may fail due to environment-specific issues, backend flakiness, or pre-existing bugs tracked separately. Rather than rediscovering these failures in each test run, the project maintains a registry of known failures.

**Registry Location**: `tests/fixtures/baseline-uat-failures.json`

**Registry Schema**:

```json
{
  "failures": [
    {
      "journey_id": 501,
      "reason": "Human-readable description of why this failure is known",
      "tracking_reference": "e.g., v035-BL-350-journey-501 or GitHub issue #123"
    }
  ]
}
```

**Annotation Behavior**:

- **KNOWN_FAILURE**: Journey ID is in the registry and the journey failed. Expected; not a regression.
- **UNEXPECTED_PASS**: Journey ID is in the registry but the journey passed. The failure may be resolved; consider removing the entry.
- **FAIL**: Journey ID is not in the registry and the journey failed. Unexpected failure — investigate whether it is a regression.
- **PASS**: Journey ID is not in the registry and the journey passed. Normal success.

Annotations are output-only labels. They do not change the exit code: the runner exits with `1` if any journey failed (regardless of annotation), `0` if all passed.

**Maintenance Workflow**:

1. If a journey fails and is not in the registry, investigate whether it is environment-specific or a regression.
2. If it is a known issue, add it to `tests/fixtures/baseline-uat-failures.json` with a `reason` and `tracking_reference`.
3. If a registered journey consistently passes (UNEXPECTED_PASS), the underlying issue is likely resolved — remove the entry from the registry.
4. The `tracking_reference` field should link to a backlog item or issue (e.g., `v035-BL-350-journey-501`) so reviewers can find context.

**Missing or malformed registry**: If the registry file is missing, the runner continues normally with all failures annotated as `FAIL`. If the registry contains malformed JSON, the runner prints a descriptive error and exits before running any journeys.

### Screenshots and the FAIL_ prefix

Screenshots are numbered by step within each journey directory:

- `01_initial_page.png` — normal step screenshot
- `03_FAIL_assertion_check.png` — screenshot captured at the point of failure

A `FAIL_` prefix in the filename means that step did not pass. The screenshot shows the browser state at the moment the failure was detected, which is the most useful artifact for diagnosing what went wrong.

### Journey result JSON

Each journey script also writes a `journey_result.json` file in its screenshot directory with step counts, console errors, and identified issues. The runner aggregates these into the top-level reports.

## What to do when a journey fails

### 1. Read the report

Open `uat-report.md` in the timestamped output directory. The **Failed Journeys** section lists each failure with its error message and any browser console errors captured during execution.

### 2. Check the screenshots

Navigate to the failing journey's screenshot directory. Look at the `FAIL_`-prefixed screenshot to see the browser state at the point of failure. Compare it with the preceding step screenshots to understand what changed.

### 3. Correlate with application behaviour

A UAT failure means the application did not behave as a user would expect. Common causes:

- **Missing or wrong data rendered** — the API returned unexpected data, or the GUI failed to display it. Check the API response and the frontend rendering logic.
- **Element not found** — the GUI layout changed and Playwright couldn't locate the expected element. Check for CSS/component changes.
- **Console errors** — JavaScript runtime errors may indicate a frontend bug. The report lists captured console errors (with benign patterns like favicon 404s already filtered out).

### 4. Raise an issue

When a UAT failure reveals a bug:

1. Create a backlog item or bug report describing the failure.
2. Reference the UAT evidence path (e.g. `testing-evidence/uat-evidence/20260318_143022/scan-library/03_FAIL_search_results.png`) so reviewers can see exactly what happened.
3. Include the relevant section from `uat-report.md` in the issue description.

### 5. Re-run after fixing

After fixing the underlying issue, re-run the relevant journey to confirm:

```bash
uv run python scripts/uat_runner.py --headless --skip-build --journey 201
```

## Available journey scripts

| Journey | Script | Description |
|---------|--------|-------------|
| 201 | `uat_journey_201.py` | **Scan Library** — Navigates to the Library tab, triggers a directory scan, verifies video grid population with metadata, and exercises FTS5 full-text search. |
| 202 | `uat_journey_202.py` | **Project Clip** — Creates a project, adds 3 clips with in/out points and timeline positions, then verifies all clips render correctly in the clips table. Depends on journey 201. |
| 203 | `uat_journey_203.py` | **Effects-Timeline** — Applies, edits, and removes effects on clips, verifies the timeline canvas with zoom and scroll, and selects layout presets with preview verification. Depends on journey 202. |
| 204 | `uat_journey_204.py` | **Export-Render** — Seeds the Running Montage sample project and validates that all clips (4), effects (5), and transitions (1) render correctly across the project detail, effects, and timeline pages. Independent of journeys 201–203. |
| 205 | `uat_journey_205.py` | **Preview Playback** — Navigates to the Preview page via the navigation tab, verifies the player component renders (or a no-content placeholder), checks that controls are visible and interactive, and confirms the quality selector is present. Independent of journeys 201–204. |
| 401 | `uat_journey_401.py` | **Preview Playback (Full)** — Starts a preview session, waits for generation, plays the video, seeks to 50% via the progress bar, pauses, and checks the quality indicator. Depends on journey 205. |
| 402 | `uat_journey_402.py` | **Proxy Management** — Navigates to the Library, verifies proxy status badges on video cards, waits for proxy generation, then starts a preview with proxy. Depends on journey 201. |
| 403 | `uat_journey_403.py` | **Theater Mode** — Enters Theater Mode, verifies HUD auto-hide after 3 seconds, re-shows HUD on mouse move, tests keyboard shortcuts (Space, Escape), and exits. Independent. |
| 404 | `uat_journey_404.py` | **Timeline Sync** — Plays the preview, verifies the playhead moves with playback, clicks a timeline position, and verifies the video seeks to match. Independent. |
| 501 | `uat_journey_501.py` | **Render Export Journey** — Navigates to the Timeline page to trigger project auto-selection, then navigates to /gui/render. Opens the Start Render modal, verifies format and quality defaults are populated, submits the render job, and verifies the job appears in the queue with an expected status badge. Independent. |
| 502 | `uat_journey_502.py` | **Render Queue Journey** — Submits multiple render jobs to fill the queue, verifies queue ordering and concurrency limits, and checks that pending jobs are visible in the queue. Depends on journey 501. |
| 503 | `uat_journey_503.py` | **Render Settings Journey** — Opens the Start Render modal and validates format, quality, and encoder selector options, verifies the FFmpeg command preview updates when settings change, and checks all available format/quality combinations. Depends on journey 501. |
| 504 | `uat_journey_504.py` | **Render Failure Journey** — Creates a project with a clip pointing to a nonexistent source file, starts a render, and verifies the job transitions to failed status with an error message visible in the job card. Tests the retry button interaction. Depends on journey 501. |
| 604 | `uat_journey_604.py` | **Keyboard Navigation via npx** — Validates keyboard-only navigation through the application by wrapping `gui/e2e/keyboard-navigation.spec.ts` via Playwright CLI. Resolves `npx` using `shutil.which()` for cross-platform compatibility (Windows `.cmd` shim support). Checks that all interactive elements are Tab-reachable, focus order is correct, and no focus traps exist. Independent. |
| 605 | `uat_journey_605.py` | **Screen Reader Audit** — Validates WCAG AA compliance across all workspace routes (`/gui/`, `/gui/library`, `/gui/render`, `/gui/dashboard`, `/gui/preview`, `/gui/projects`, `/gui/timeline`) using axe-core. Injects axe-core and reports critical/serious violations per route. Journey passes when 0 critical and 0 serious violations are found across all routes. Independent. |
| 701 | `tests/uat/journeys/j_markers.py` | **R2 Markers** — Navigates to the project timeline, creates section markers, and verifies that marker regions are displayed. Part of Release 2 test layer (v076). Independent. |
| 702 | `tests/uat/journeys/j_mastering.py` | **R2 Mastering** — Navigates to delivery profiles, creates a profile with loudness and true-peak targets, triggers a QC-gated render, and verifies the QC report is visible. Depends on journey 701. |
| 703 | `tests/uat/journeys/j_qc_fail.py` | **R2 QC Failure** — Navigates to a project in QC-failed state, asserts the failure state is visible in the QC panel, and verifies the re-master flow is accessible (`qc_fail` token in page content). Depends on journey 702. |
| 704 | `tests/uat/journeys/j_automation.py` | **R2 Automation (stub)** — Placeholder for Release 2 automation envelope journey. Passes headlessly. Independent. |
| 705 | `tests/uat/journeys/j_reverse_split.py` | **R2 Reverse/Split (stub)** — Placeholder for Release 2 reverse and split capability journey. Passes headlessly. Independent. |
| 706 | `tests/uat/journeys/j_grade.py` | **R2 Grade (stub)** — Placeholder for Release 2 color grading capability journey. Passes headlessly. Independent. |

### Dependency graph

```
201 (scan-library)
 ├─▶ 202 (project-clip)
 │    └─▶ 203 (effects-timeline)
 └─▶ 402 (proxy-management)

204 (export-render)      ← independent
205 (preview-playback)   ← independent
 └─▶ 401 (preview-playback-full)

403 (theater-mode)       ← independent
404 (timeline-sync)      ← independent
501 (render-export-journey) ← independent
 ├─▶ 502 (render-queue-journey)
 ├─▶ 503 (render-settings)
 └─▶ 504 (render-failure-journey)

604 (keyboard-navigation)   ← independent
605 (screen-reader-audit)   ← independent

701 (r2-markers)            ← independent
 └─▶ 702 (r2-mastering)
      └─▶ 703 (r2-qc-fail)
704 (r2-automation)         ← independent
705 (r2-reverse-split)      ← independent
706 (r2-grade)              ← independent
```

If journey 201 fails, journeys 202, 203, and 402 are skipped automatically. If journey 205 fails, journey 401 is skipped. Journeys 204, 403, 404, and 501 always run regardless of other journey results. If journey 501 fails, journeys 502, 503, and 504 are skipped automatically. Journeys 604 and 605 always run regardless of other journey results. If journey 701 fails, journeys 702 and 703 are skipped. Journeys 704, 705, and 706 always run regardless of other journey results.

## Manual GUI Verification Steps

These steps require a running snf GUI in a headed environment and cannot be automated in headless CI.

### Source Compliance Link (AGPL §13 Affordance)

**Requires:** Running snf GUI (headed environment)

1. Open the workspace shell in a browser.
2. Look at the right side of the footer status bar.
3. Verify a link with text **"Source"** is visible.
4. Click the link — it should open the configured `STOAT_SOURCE_URL` in a new tab.
   - Default: `https://github.com/gwickman/stoat-and-ferret`
   - If `STOAT_SOURCE_URL` is set in the deployment environment, it should open that URL instead.
5. To verify the fallback: if the API is unreachable, the link should still be present and point to the default URL.

**data-testid:** `source-code-link` (usable with Playwright for automated headed UAT)

## v087 UAT Journeys (Multi-Clip Render, Preflight Validation, Evidence API)

These journeys validate the v087 feature set: multi-clip rendering via `RenderGraphTranslator` (BL-505), preflight validation warnings (BL-551), and the evidence API (BL-554). They are API-level journeys exercised via `curl` or the smoke test harness — not browser journeys. Browser-specific steps are marked as deferred.

### J-MULTICL-01: Multi-Clip Render — API Acceptance

**Feature:** BL-505 — RenderGraphTranslator integration

**Pre-conditions:**
- Server running on `http://localhost:8765`
- At least one video file has been scanned into the library (needed for `source_video_id`)

**Steps:**

1. Create a project:
   ```bash
   curl -s -X POST http://localhost:8765/api/v1/projects \
     -H 'Content-Type: application/json' \
     -d '{"name": "Multi-Clip UAT"}' | jq .
   ```
   Note the returned `id` as `PROJECT_ID`.

2. Add two clips to the project (replace `VIDEO_ID` with a valid `source_video_id` from `GET /api/v1/library`):
   ```bash
   # Clip 1 — timeline_position=0
   curl -s -X POST "http://localhost:8765/api/v1/projects/$PROJECT_ID/clips" \
     -H 'Content-Type: application/json' \
     -d '{"source_video_id": "VIDEO_ID", "in_point": 0, "out_point": 90, "timeline_position": 0}' | jq .

   # Clip 2 — timeline_position=90
   curl -s -X POST "http://localhost:8765/api/v1/projects/$PROJECT_ID/clips" \
     -H 'Content-Type: application/json' \
     -d '{"source_video_id": "VIDEO_ID", "in_point": 0, "out_point": 90, "timeline_position": 90}' | jq .
   ```

3. Submit a render job:
   ```bash
   curl -s -X POST http://localhost:8765/api/v1/render \
     -H 'Content-Type: application/json' \
     -d "{\"project_id\": \"$PROJECT_ID\", \"render_plan\": \"{\\\"total_duration\\\": 6.0, \\\"settings\\\": {}}\"}" | jq .
   ```

**Expected outcome:**
- HTTP **201** — multi-clip projects are accepted (BL-505 removed the previous single-clip restriction)
- Response body includes `"status": "queued"` or `"running"`
- `warnings` field is `null` or absent when no per-clip effects are set

**Note on previous behavior:** Before BL-505, a multi-clip project was rejected at `POST /render` with HTTP 422 and error code `MULTI_CLIP_NOT_SUPPORTED`. That rejection no longer exists. If you observe a 422 with that code, the BL-505 integration did not deploy correctly.

---

### J-MULTICL-02: Multi-Clip Render — SSIM Visual Verification (FFmpeg-gated, deferred)

**Feature:** BL-505 — render output content verification

**Pre-conditions:** FFmpeg available (`STOAT_TEST_FFMPEG=1`); real video source files accessible to the server.

**Steps:**

1. Complete J-MULTICL-01 and poll until `status == "completed"`:
   ```bash
   curl -s "http://localhost:8765/api/v1/render/$JOB_ID" | jq .status
   ```

2. Read `output_path` from the job response.

3. Extract a frame from the first clip's time region and the second clip's time region:
   ```bash
   ffmpeg -ss 1.5 -i "$OUTPUT_PATH" -vframes 1 -q:v 2 /tmp/frame_clip1.jpg
   ffmpeg -ss 4.5 -i "$OUTPUT_PATH" -vframes 1 -q:v 2 /tmp/frame_clip2.jpg
   ```

4. Visually verify that `frame_clip1.jpg` shows content from the first source clip and `frame_clip2.jpg` shows content from the second source clip.

**Expected outcome:**
- Frame at ~1.5 s shows clip 1 source content
- Frame at ~4.5 s shows clip 2 source content
- Total output duration is approximately 6.0 s

**Discharge status:** Deferred — requires FFmpeg and real video sources. Discharge via `STOAT_TEST_FFMPEG=1` smoke run post-release.

---

### J-PREFLIGHT-01: Preflight — Multi-Clip Project Accepted (Post-BL-505)

**Feature:** BL-551 preflight layer + BL-505

Prior to BL-505, `POST /render` rejected multi-clip projects with HTTP 422 `MULTI_CLIP_NOT_SUPPORTED`. After BL-505 the rejection is gone; the preflight layer no longer blocks on clip count.

**Steps:** See J-MULTICL-01. Submit a project with 2+ clips.

**Expected outcome:** HTTP **201**, not 422.

---

### J-PREFLIGHT-02: Preflight — Single-Clip with Per-Clip Effects Accepted (BL-553)

**Feature:** BL-551-AC-2, BL-553

**Pre-conditions:** Server running; a project with exactly one clip exists.

**Steps:**

1. Create a project and add one clip (see J-MULTICL-01 steps 1–2, but add only one clip).

2. Add a per-clip effect:
   ```bash
   curl -s -X POST "http://localhost:8765/api/v1/projects/$PROJECT_ID/clips/$CLIP_ID/effects" \
     -H 'Content-Type: application/json' \
     -d '{"effect_type": "blur", "parameters": {"radius": 5}}' | jq .
   ```

3. Submit a render job:
   ```bash
   curl -s -X POST http://localhost:8765/api/v1/render \
     -H 'Content-Type: application/json' \
     -d "{\"project_id\": \"$PROJECT_ID\", \"render_plan\": \"{\\\"total_duration\\\": 5.0, \\\"settings\\\": {}}\"}" \
     | jq '{status}'
   ```

**Expected outcome:**
- HTTP **201**
- No `"Per-clip effects detected; effects will be applied in a future release"` warning (BL-553 removed this placeholder — per-clip effects are now applied via the Rust translator for multi-clip projects)
- Single-clip projects use the `settings.filter_graph` path; multi-clip projects use the translator

**Note on v087 behavior:** Before BL-553, the render router emitted a preflight warning whenever a clip had effects. That warning was removed in v088 (BL-553) because the render worker now calls the Rust translator with real per-clip effects for multi-clip projects.

---

### J-PREFLIGHT-03: Preflight — Zero-Byte FFmpeg Output Marks Job FAILED (FFmpeg-gated, deferred)

**Feature:** BL-551-AC-3

**Pre-conditions:** FFmpeg available (`STOAT_TEST_FFMPEG=1`); a source file that causes FFmpeg to produce zero-byte output (e.g., a truncated or header-only file).

**Steps:**

1. Scan a corrupted/truncated video file into the library.

2. Add it as a clip to a project and submit a render job.

3. Poll the job until it reaches a terminal state:
   ```bash
   curl -s "http://localhost:8765/api/v1/render/$JOB_ID" | jq '{status, error_message}'
   ```

**Expected outcome:**
- `status: "failed"`
- `error_message` describes the zero-byte output condition

**Discharge status:** Deferred — requires FFmpeg and a controlled corrupted-input scenario. Discharge via `STOAT_TEST_FFMPEG=1` post-release.

---

### J-EVIDENCE-01: Evidence API — Access Denied Without Flag

**Feature:** BL-554

**Pre-conditions:** Server running with `STOAT_RENDER_EVIDENCE_FULL_ACCESS` unset or `false` (the default).

**Steps:**

1. Submit a render job (see J-MULTICL-01 steps 1–3).

2. Call the evidence endpoint:
   ```bash
   curl -s "http://localhost:8765/api/v1/render/$JOB_ID/evidence" | jq .
   ```

**Expected outcome:**
- HTTP **403**
- Response body:
  ```json
  {
    "detail": {
      "code": "EVIDENCE_ACCESS_DISABLED",
      "message": "Full evidence access is disabled. Set STOAT_RENDER_EVIDENCE_FULL_ACCESS=true to enable."
    }
  }
  ```

---

### J-EVIDENCE-02: Evidence API — Full Evidence When Flag Enabled (FFmpeg-gated)

**Feature:** BL-554

**Pre-conditions:** Server started with `STOAT_RENDER_EVIDENCE_FULL_ACCESS=true`. FFmpeg available for render completion.

**Steps:**

1. Start the server with the evidence flag:
   ```bash
   STOAT_RENDER_EVIDENCE_FULL_ACCESS=true uv run python -m stoat_ferret.api.app
   ```

2. Create a project, add a clip, and submit a render job.

3. Poll `GET /api/v1/render/{job_id}` until `status == "completed"`.

4. Fetch the evidence:
   ```bash
   curl -s "http://localhost:8765/api/v1/render/$JOB_ID/evidence" | jq .
   ```

**Expected outcome:**
- HTTP **200**
- Response includes all fields: `job_id`, `command_args` (list), `exit_code` (integer), `stderr_tail` (string), `output_path` (string), `output_size_bytes` (integer or null), `filter_script_path` (string or null)
- `exit_code` is `0` for a successful render

**Discharge status:** Requires FFmpeg for a real completed render. Smoke test `test_evidence_endpoint_200_when_enabled` provides partial headless coverage with synthetic evidence.

---

### J-EVIDENCE-03: Evidence API — Sensitive Values Are Redacted

**Feature:** BL-554 — command_args redaction

**Pre-conditions:** Server running with `STOAT_RENDER_EVIDENCE_FULL_ACCESS=true`. A render job has completed and evidence has been persisted.

**Steps:**

1. Start the server with the evidence flag and any `STOAT_*` env vars you want to verify are redacted (e.g., a fake `STOAT_SECRET_VALUE=super-secret`).

2. Submit and complete a render job.

3. Fetch evidence:
   ```bash
   curl -s "http://localhost:8765/api/v1/render/$JOB_ID/evidence" | jq .command_args
   ```

4. Verify the output:
   - Scan `command_args` for any `sk-or-v1-*` token patterns — all must be replaced with `"[REDACTED]"`
   - Scan `command_args` for the literal value of any `STOAT_*` env vars — all must be replaced with `"[REDACTED]"`

**Expected outcome:** No raw API keys or `STOAT_*` env var values appear in `command_args`. Each redacted position contains the string `"[REDACTED]"`.

---

### J-EVIDENCE-04: GUI Evidence Inspector (Windows Headed — Deferred)

**Feature:** BL-554 — GUI integration

**Discharge status:** Deferred — requires Windows headed browser environment.

**Discharge procedure:** Manual UAT on Windows post-release. Navigate to the Render page (`/gui/render`), open a completed job's details panel, and verify the Evidence tab is populated with `command_args`, `exit_code`, `stderr_tail`, `output_path`, and `output_size_bytes`.

---

## Deferred UAT Items (v087)

The following UAT scenarios require a Windows headed environment or FFmpeg and are deferred to the post-v087 discharge window:

| Journey | Reason | Discharge Procedure |
|---------|--------|---------------------|
| J-EVIDENCE-04 (GUI evidence inspector) | Requires Windows headed browser | Manual UAT on Windows post-release |
| J-MULTICL-02 (SSIM visual verification) | Requires FFmpeg + real video sources | `STOAT_TEST_FFMPEG=1` smoke run post-release |
| J-PREFLIGHT-03 (zero-byte output detection) | Requires FFmpeg + controlled corrupted input | `STOAT_TEST_FFMPEG=1` with truncated source file |
| J-EVIDENCE-02 (full evidence with real FFmpeg) | Requires FFmpeg for completed render | `STOAT_TEST_FFMPEG=1` smoke run post-release |
