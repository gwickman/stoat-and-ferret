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

### Against a running server

```bash
uv run python scripts/uat_runner.py --headless --skip-build
```

### Custom output directory

By default, results are written to `uat-evidence/` in the project root. Override with:

```bash
uv run python scripts/uat_runner.py --headless --output-dir ./my-results
```

## Understanding the results

### Output directory structure

Each run creates a timestamped subdirectory under the output base:

```
uat-evidence/
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
2. Reference the UAT evidence path (e.g. `uat-evidence/20260318_143022/scan-library/03_FAIL_search_results.png`) so reviewers can see exactly what happened.
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
```

If journey 201 fails, journeys 202, 203, and 402 are skipped automatically. If journey 205 fails, journey 401 is skipped. Journeys 204, 403, and 404 always run regardless of other journey results.
