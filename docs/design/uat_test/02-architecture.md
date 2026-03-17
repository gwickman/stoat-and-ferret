# 02 — Architecture

## Entry Point

```
scripts/uat_runner.py
```

A single Python script (~1,300 lines) that orchestrates the full UAT lifecycle: build, boot, test, report, teardown.

## CLI Interface

```
python scripts/uat_runner.py --headed        # Human UAT: visible browser, pauses on failure
python scripts/uat_runner.py --headless      # CI/exploration: invisible browser, full report
python scripts/uat_runner.py --journey 4     # Run only Journey 4 (effects)
python scripts/uat_runner.py --skip-build    # Skip build/boot if server already running
python scripts/uat_runner.py --output-dir /path/to/dir   # Custom output directory
```

### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--headed` | boolean | false | Run browser in visible mode for human sign-off |
| `--headless` | boolean | true | Run browser headless for automated CI/exploration |
| `--journey N` | integer | all | Run only journey number N (1-7) |
| `--skip-build` | boolean | false | Skip build/boot steps — assumes server is already running |
| `--output-dir` | path | see below | Directory for screenshots and reports |

**Default `--output-dir`:** `C:\Users\grant\Documents\projects\auto-dev-projects\stoat-and-ferret\uat-evidence\{timestamp}\`

Where `{timestamp}` is ISO 8601 format with hyphens replacing colons, e.g. `2026-03-16T14-30-00`.

## Build/Boot Sequence

When `--skip-build` is not set, the runner executes the following steps in order:

1. **Build Rust core:** `maturin develop` — compiles Rust extensions into the Python environment
2. **Install Python package:** `pip install -e .` — ensures all Python dependencies are available
3. **Build React GUI:** `cd gui && npm ci && npm run build` — produces static frontend assets
4. **Start server:** `uvicorn stoat_ferret.api.app:create_app --port 8765` — launched as a background subprocess
5. **Health poll:** `GET /health/ready` polled at 1-second intervals with 60-second timeout
6. **Seed sample data:** `python scripts/seed_sample_project.py http://localhost:8765` — creates the Running Montage project

On teardown (after all journeys complete or on error), the server subprocess is terminated via `SIGTERM` with a 5-second grace period before `SIGKILL`.

## Screenshot Strategy

### Directory Structure

```
{output-dir}/
  01-boot/
    01_app_shell_loaded.png
    02_health_green.png
  02-scan/
    01_library_empty.png
    02_scan_modal_open.png
    03_scan_in_progress.png
    04_library_populated.png
    05_search_results.png
  03-project/
    01_project_list_empty.png
    02_create_modal.png
    ...
  04-effects/
    ...
  05-timeline/
    ...
  06-layout/
    ...
  07-sample-project/
    ...
  uat-report.json
  uat-report.md
```

### Naming Convention

```
{output-dir}/{journey-name}/{step_number}_{description}.png
```

- `journey-name`: Zero-padded number + kebab-case name (e.g., `01-boot`, `02-scan`)
- `step_number`: Zero-padded step within the journey (e.g., `01`, `02`)
- `description`: Snake_case description of the checkpoint (e.g., `app_shell_loaded`)

### Failure Prefix

Failed screenshots are prefixed with `FAIL_`:

```
02-scan/06_FAIL_grid_empty.png
```

This makes failures immediately identifiable when browsing the evidence directory.

### Screenshot Types

- **Full-page screenshots** at each checkpoint — captures the complete viewport
- **Element-specific screenshots** for bug evidence — captures the specific failing element

## Bug Report Format

### Structured JSON (`uat-report.json`)

```json
{
  "run_id": "2026-03-16T14-30-00",
  "mode": "headless",
  "started_at": "2026-03-16T14:30:00Z",
  "completed_at": "2026-03-16T14:35:42Z",
  "journeys": [
    {
      "name": "01-boot",
      "status": "pass",
      "steps_total": 8,
      "steps_passed": 8,
      "screenshots": ["01-boot/01_app_shell_loaded.png", "01-boot/02_health_green.png"],
      "issues": []
    },
    {
      "name": "02-scan",
      "status": "fail",
      "steps_total": 9,
      "steps_passed": 5,
      "screenshots": ["02-scan/01_library_empty.png", "..."],
      "issues": [
        {
          "id": "UAT-001",
          "journey": "02-scan",
          "step": 6,
          "severity": "high",
          "summary": "Video grid does not populate after scan completes",
          "expected": "Grid shows thumbnails for scanned videos",
          "actual": "Grid remains empty despite scan job showing 'complete'",
          "screenshot": "02-scan/06_FAIL_grid_empty.png",
          "console_errors": ["TypeError: Cannot read property 'map' of undefined"],
          "api_responses": {"GET /videos": {"status": 200, "body": "..."}},
          "timestamp": "2026-03-16T14:32:15Z"
        }
      ]
    }
  ],
  "summary": {
    "total_journeys": 7,
    "passed": 6,
    "failed": 1,
    "total_issues": 1
  }
}
```

### Human-Readable Markdown (`uat-report.md`)

Generated from the JSON report. Contains:
- Run metadata (timestamp, mode, duration)
- Per-journey pass/fail summary table
- Detailed issue descriptions with inline screenshot references
- Console error excerpts and API response snippets for failures

## Two-Tier Model

### Tier 1 — Headless (Automated/CI)

- Runs during version closure or CI
- Browser invisible (headless Chromium)
- All 7 journeys executed
- Structured JSON + markdown reports generated
- Screenshots captured at every checkpoint
- Failures flagged for Tier 2 human review

### Tier 2 — Headed (Human Sign-Off)

- Developer runs locally with `--headed` flag
- Browser visible on screen
- Same journeys and assertions as Tier 1
- On failure: browser pauses so developer can inspect
- Used when Tier 1 reports failures or for final release sign-off

## Component Breakdown

| Component | Estimated Lines | Responsibility |
|-----------|----------------|----------------|
| Process management (build/boot/teardown) | ~200 | Subprocess lifecycle, health polling, cleanup |
| Journey scripts (7 × ~30 steps) | ~800 | Playwright page interactions and assertions |
| Screenshot + report infrastructure | ~200 | Naming, collection, JSON/markdown generation |
| CLI interface + config | ~100 | argparse, headed/headless, journey selection |
| **Total** | **~1,300** | |
