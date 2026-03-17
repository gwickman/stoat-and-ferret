# 04 — Auto-Dev Integration

## Two-Tier Model

The UAT script integrates with auto-dev version closure using a two-tier approach that balances automation with human judgement.

### Tier 1 — Automated (Headless)

**When:** Runs automatically during every version closure as part of `VERSION_CLOSURE.md`.

**How:** Claude Code exploration executes `python scripts/uat_runner.py --headless`, which:
1. Builds the project from clean state (`maturin develop`, `pip install -e .`, `npm run build`)
2. Boots the application (`uvicorn` on port 8765)
3. Seeds sample data (`scripts/seed_sample_project.py`)
4. Runs all 7 user journeys via headless Playwright
5. Captures screenshots at every checkpoint
6. Generates `uat-report.json` and `uat-report.md`
7. Shuts down the server

**Output location:** `C:\Users\grant\Documents\projects\auto-dev-projects\stoat-and-ferret\uat-evidence\{timestamp}\`

**On success:** Version closure proceeds. Evidence directory archived with version artifacts.

**On failure:** Flags specific journeys/steps that failed. Human Tier 2 review required before closure.

### Tier 2 — Manual (Headed)

**When:** Triggered manually when:
- Tier 1 reports failures
- Final release sign-off needed
- GUI-impacting changes require visual inspection

**How:** Developer runs locally:
```
python scripts/uat_runner.py --headed
```

Same test script, same journeys, same assertions — but browser is visible. On failure, the browser pauses so the developer can inspect the state, check the DOM, and review console errors interactively.

## VERSION_CLOSURE.md Updates

The following should be added to `docs/auto-dev/VERSION_CLOSURE.md`:

```markdown
## Automated UAT (Tier 1)
- [ ] Run exploration: `uat-headless-regression`
  - Builds project, boots server, seeds sample data
  - Runs Playwright headless against all 7 journeys
  - Captures screenshots to `uat-evidence/{timestamp}/`
  - Generates `uat-report.json` with pass/fail per step
  - If any failures: flag for human Tier 2 review

## Manual UAT (Tier 2) — only if Tier 1 flags issues
- [ ] Developer runs: `python scripts/uat_runner.py --headed`
  - Same journeys, visible browser
  - Developer reviews screenshots and confirms or files bugs
```

## What Goes in Version Closure Evidence

For each version closure, the UAT evidence directory should contain:

| Artifact | Description |
|----------|-------------|
| `uat-report.json` | Structured pass/fail results per journey and step |
| `uat-report.md` | Human-readable summary with issue details |
| `{journey-name}/` | Screenshot directories for each journey |
| `{journey-name}/*_FAIL_*.png` | Failure-specific screenshots (if any) |

The evidence directory is timestamped, so multiple runs are preserved without conflict.

## Limitations

### 1. Display Server Requirement

Headless Chromium renders pages but may miss visual bugs that only manifest with GPU rendering or specific display DPI. True visual verification (colors, fonts, animation smoothness) requires Tier 2 headed mode with a display server (X11, Wayland, or Windows desktop).

Headless mode is sufficient for:
- Verifying page loads and elements render
- Checking API data flows through to the GUI
- Detecting broken interactions (clicks, form submissions)
- Capturing layout structure

Headless mode does not cover:
- Color accuracy and contrast
- Font rendering differences
- GPU-rendered visual effects
- Animation and transition smoothness

### 2. Build Time

The full build sequence (Rust + Node + seed) can take 2-5 minutes. For exploration contexts with tight time limits:
- Use `--skip-build` if the application is already running
- Run build as a separate CI step, UAT as a follow-up step

### 3. Browser Binary Availability

Playwright's Chromium browser (~400MB) must be installed:
```
playwright install chromium
```

In CI environments, this requires explicit setup. The binary is cached between runs.

### 4. Screenshot Baselines

The first UAT run establishes baseline screenshots. Regression detection (comparing against known-good baselines) is a future enhancement. The initial implementation focuses on step pass/fail based on element presence and data correctness, not pixel-level comparison.

### 5. Exploration Timeout Risk

Running all 7 journeys with full build may approach exploration time limits. Mitigations:
- `--journey N` flag to run individual journeys
- `--skip-build` to skip the build phase
- Split into per-journey explorations if needed
