# Version Closure — UAT Integration

This document defines the user acceptance testing (UAT) process for version closure.
UAT validates end-to-end user journeys in a real browser before a version is
considered complete, bridging the gap between CI test suites and manual verification.

---

## Prerequisites

### Bootstrap Commands

Install the UAT Python dependencies and the Chromium browser binary:

```bash
uv pip install -e ".[uat]"
playwright install chromium
```

**Cache sharing:** Python and TypeScript Playwright share the Chromium binary
cache at `~/.cache/ms-playwright/`. If the GUI's TypeScript E2E tests have
already installed a compatible version (`>=1.58,<2.0`), the second command
may be a no-op.

---

## Tier 1: Automated UAT (Headless)

Run headless Playwright journeys as part of version closure. This is the
primary validation path.

### Against a Running Server

If the API server and GUI dev server are already running (e.g., during
development or exploration):

```bash
python scripts/uat_runner.py --headless --skip-build
```

### Full Build-Boot-Test Cycle

Build the GUI, start the server, run journeys, and tear down automatically:

```bash
python scripts/uat_runner.py --headless
```

### Running a Single Journey

To run a specific journey by ID (e.g., 201 — scan-library):

```bash
python scripts/uat_runner.py --headless --journey 201
```

### Evidence Output

Each run produces a timestamped evidence directory:

```
uat-evidence/{YYYYMMDD_HHMMSS}/
├── screenshots/
│   ├── 201-scan-library/
│   │   ├── step_01_*.png
│   │   └── ...
│   └── ...
└── report.json
```

The `report.json` file contains per-journey pass/fail status, step counts,
console errors, and issue summaries.

---

## Tier 2: Manual Fallback (Headed)

When automated UAT is unavailable or a failure needs manual investigation,
run in headed mode to see the browser:

```bash
python scripts/uat_runner.py --headed
```

### Manual Verification Checklist

If Playwright cannot run at all (e.g., no display server, restricted
environment), verify these journeys manually:

1. **Scan Library (Journey 201):** Open the app, trigger a library scan,
   confirm media files appear in the library panel.
2. **Preview Clip (Journey 202):** Select a clip from the library, confirm
   the preview panel shows the clip and playback controls work.
3. **Timeline Edit (Journey 203):** Add a clip to the timeline, verify it
   appears and can be repositioned.
4. **Export Project (Journey 204):** Start an export, confirm the export
   completes or progress is shown.

Record results (pass/fail + screenshots) in the `uat-evidence/` directory.

---

## Known Limitations

### Display Server

On headless Linux environments without a display server, Playwright's headless
Chromium works out of the box. For non-standard environments that require a
virtual framebuffer:

```bash
xvfb-run python scripts/uat_runner.py --headless
```

### Build Time

A full build-boot-test cycle (`--headless` without `--skip-build`) takes
approximately 2-5 minutes depending on hardware. Use `--skip-build` as the
default for exploration and CI contexts where a server is already running.
Measure and update these estimates as the project grows.

### Chromium Binary Size

The Chromium binary is approximately 400 MB cached at
`~/.cache/ms-playwright/`. This cache is shared with the TypeScript Playwright
installation, so disk usage is not doubled.

### Screenshot Baselines

There is no visual regression testing against baseline screenshots. Screenshots
are captured for evidence and manual review only. Visual regression is future
work.
