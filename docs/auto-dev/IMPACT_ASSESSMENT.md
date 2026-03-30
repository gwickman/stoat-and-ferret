# Impact Assessment Checks

Project-specific design-time checks for stoat-and-ferret. These checks are executed during auto-dev Task 003 (version design) to catch recurring issue patterns before they reach implementation.

## Async Safety

### What to look for

Features that introduce or modify `subprocess.run`, `subprocess.call`, `subprocess.check_output`, or `time.sleep` inside files containing `async def`.

Grep patterns:
- `subprocess\.(run|call|check_output)` in files with `async def`
- `time\.sleep` in files with `async def`

### Why it matters

Blocking calls in an async context freeze the event loop, preventing concurrent request handling. All WebSocket heartbeats, background tasks, and concurrent API requests stall until the blocking call completes.

### Concrete example

In v009, ffprobe used `subprocess.run()` inside an async endpoint. This blocked all WebSocket heartbeats and concurrent API requests for the duration of the ffprobe call. Fixed in v010 by switching to `asyncio.create_subprocess_exec()`.

## Settings Documentation

### What to look for

Versions that add or modify fields in `src/stoat_ferret/api/settings.py` (the Pydantic BaseSettings class). If Settings fields change, verify `.env.example` is updated to document the new or changed variables.

### Why it matters

Missing `.env.example` entries cause confusing startup failures for new developers who don't know which environment variables to configure. Without documentation, developers must read the settings source code to discover required configuration.

### Concrete example

The project had 11 Settings fields across 9 versions without any `.env.example` file. New developers had to read `settings.py` source code to discover configuration variables. This was finally addressed in v011 with the creation of `.env.example`.

## Cross-Version Wiring Assumptions

### What to look for

Features that depend on behavior from prior versions — especially features that consume endpoints, WebSocket messages, or state structures introduced in earlier versions. When identified, list assumptions explicitly and verify they hold.

### Why it matters

Prior-version features may have bugs, incomplete implementations, or different behavior than assumed. Unverified assumptions cause runtime failures that are difficult to diagnose because the root cause is in a different version's implementation.

### Concrete example

The v010 progress bar feature assumed v004's per-file progress reporting worked correctly. It didn't — the progress data structure was incomplete. The progress bar displayed incorrect data until the underlying reporting was fixed.

## GUI Input Mechanisms

### What to look for

GUI features that accept user input — particularly paths, IDs, or other structured data. Verify the design specifies an appropriate input mechanism (browse dialog, dropdown, autocomplete) rather than defaulting to a plain text input.

### Why it matters

Text-only inputs for structured data are error-prone and create poor UX. Users must know exact values and type them correctly, leading to typos and frustration.

### Concrete example

The scan directory feature (v005-v010) used a plain text input for directory paths. Users had to type full paths manually with no validation or assistance. v011 added a directory browse button — this could have been caught at design time if an input mechanism check existed.

## Smoke Test and UAT Impact Assessment

### Understand the Current Test Harness

Before assessing impact, read `docs/setup/smoke-test-harness-guide/smoke-test-key-files.md` to understand both testing tiers:

1. **Smoke tests** (API-level) — in-process httpx tests in `tests/smoke/` that validate API contracts and backend stack integration
2. **UAT journeys** (browser-level) — Playwright-based Python scripts in `scripts/uat_journey_*.py` that validate complete user workflows through a real browser

Read only the files relevant to the area you are assessing.

### Check for Smoke Test Impact

If **any** part of the design affects:

- API endpoint routes, request schemas, or response schemas
- Effect types, filter builders, or Rust core filter logic
- Job lifecycle, job status, or cancellation behaviour
- Video scanning, FFmpeg probe, or metadata extraction
- Project, clip, or transition data models
- Health check subsystems

...then the design has smoke test impact and the following two features must be added to the version design.

### Required Features When Smoke Test Impact Detected

When smoke test impact is detected, **two separate features must be demanded** (not combined into one):

**Feature A — Update smoke tests:**
A dedicated feature whose sole responsibility is updating `tests/smoke/` to ensure the smoke tests exercise the new or changed behaviour. This feature must be separate from the feature implementing the change itself.

**Feature B — Update smoke test harness guide:**
A dedicated feature whose sole responsibility is updating `docs/setup/smoke-test-harness-guide/` to reflect any changes to how the harness works, what it tests, or how to run it. This includes updating `smoke-test-key-files.md` if key files change.

### Check for UAT Impact

If **any** part of the design affects the following areas, corresponding UAT updates are required:

**`data-testid` attribute changes:**
Any change to a component's `data-testid` attribute requires updating the relevant UAT journey script(s). The affected journey(s) should be noted in the PR. Grep for the old testid value in `scripts/uat_journey_*.py` to identify impacted journeys.

**API endpoint changes:**
Changes to API endpoint paths, response schemas, or validation rules (e.g., `le=` constraints) may require updates to UAT journey scripts and/or `scripts/seed_sample_project.py`. Journey scripts make assertions about rendered data that originates from API responses.

**New pages or navigation flows:**
Adding a new page or changing navigation (routes, sidebar links, tab structure) requires updating or adding UAT journey scripts and updating `docs/manual/uat-testing.md`.

**Seed script data model changes:**
Changes to the data model — especially Timeline Track entities, Clip fields, or Effect schema — require updating `scripts/seed_sample_project.py` to ensure J204 (export-render) remains valid. The seed script creates a Running Montage project with specific clips, effects, and transitions.

**`uat_runner.py` changes:**
Changes to server startup, teardown, or evidence collection in `scripts/uat_runner.py` require updating `docs/manual/uat-testing.md`.

**New effect types:**
Adding a new effect type with required schema fields that lack defaults requires checking the `useEffectPreview.ts` guard logic and may affect J203 (effects-timeline) if the journey exercises effect application.

**UAT manual maintenance:**
`docs/manual/uat-testing.md` must be kept up to date whenever the UAT harness changes — it is the developer-facing reference for running and maintaining UAT.

### Required Features When UAT Impact Detected

When UAT impact is detected, demand a dedicated feature for updating the affected UAT journey scripts and/or `docs/manual/uat-testing.md`. This should be separate from the feature implementing the change itself, following the same pattern as smoke test impact features.

## Operational Detection Scripts

Maintenance checks to flag when code changes may break smoke tests or require smoke test updates. These complement the design-time checks above with concrete detection commands.

### Smoke Test Coverage Gaps

**Trigger:** New API route definitions added to `src/stoat_ferret/api/routers/` that are not exercised by any smoke test.

**Detection:**

```bash
# List routes defined in routers
grep -rn '@router\.\(get\|post\|put\|patch\|delete\)' src/stoat_ferret/api/routers/

# List routes exercised in smoke tests
grep -rn 'client\.\(get\|post\|put\|patch\|delete\)' tests/smoke/
```

**Action:** Compare output. Any route in routers not covered by a smoke test should be flagged for review. Add smoke test coverage for new endpoints.

### Sample Project Compatibility

**Trigger:** New effect types added to `src/stoat_ferret/effects/` or new Rust filter builders that smoke tests don't exercise.

**Detection:**

```bash
# List effect/filter types in source
grep -rn 'class.*Effect' src/stoat_ferret/effects/
grep -rn 'pub struct.*Filter\|pub struct.*Builder' rust/stoat_ferret_core/src/

# List effects exercised in smoke tests
grep -rn 'effect\|filter\|transition' tests/smoke/
```

**Action:** Compare output. New effect types should have corresponding smoke test coverage to verify they work end-to-end with sample projects.

### Test Video Fixture Assumptions

**Trigger:** Changes to video files in the `videos/` directory or references to `EXPECTED_VIDEOS` in test fixtures.

**Detection:**

```bash
# Check for video file changes
git diff --name-only HEAD~1 | grep -i 'videos/'

# Check for EXPECTED_VIDEOS references
grep -rn 'EXPECTED_VIDEOS\|expected_videos\|video.*fixture' tests/smoke/
```

**Action:** When video files are added, removed, or modified, verify that smoke test fixtures still reference valid files and that expected video counts are correct.

### Composition Model Changes (Phase 3)

**Trigger:** Changes to Phase 3 composition types (`TrackType`, `LayoutPosition`, `LayoutPreset`, `AudioMixSpec`, `BatchProgress`) or their identifiers in Python or Rust source.

**Detection:**

```bash
# List Phase 3 composition model definitions in Python
grep -rn 'class.*TrackType\|class.*LayoutPosition\|class.*LayoutPreset\|class.*AudioMixSpec\|class.*BatchProgress' src/

# List Phase 3 composition model definitions in Rust
grep -rn 'pub struct TrackType\|pub struct LayoutPosition\|pub struct LayoutPreset\|pub struct AudioMixSpec\|pub struct BatchProgress\|pub enum TrackType\|pub enum LayoutPosition\|pub enum LayoutPreset' rust/stoat_ferret_core/src/

# List Phase 3 identifier usage in API schemas and routers
grep -rn 'track_type\|batch_id' src/stoat_ferret/api/

# List Phase 3 types exercised in smoke tests
grep -rn 'TrackType\|LayoutPosition\|LayoutPreset\|AudioMixSpec\|BatchProgress\|track_type\|batch_id' tests/smoke/
```

**Action:** Compare output. When composition model types or identifiers change, verify that smoke tests and contract tests still exercise the updated interfaces. New composition types should have corresponding test coverage.

### Preview and Proxy Model Changes (Phase 4)

**Trigger:** Changes to Phase 4 preview and proxy types (`PreviewSession`, `ProxyFile`, `PreviewQuality`) or their identifiers in Python or Rust source.

**Detection:**

```bash
# List Phase 4 preview/proxy model definitions in Python
grep -rn 'class.*PreviewSession\|class.*ProxyFile\|class.*PreviewQuality' src/

# List Phase 4 preview/proxy model definitions in Rust
grep -rn 'pub struct PreviewSession\|pub struct ProxyFile\|pub struct PreviewQuality\|pub enum PreviewSession\|pub enum ProxyFile\|pub enum PreviewQuality' rust/stoat_ferret_core/src/

# List Phase 4 preview/proxy identifier usage in API schemas and routers
grep -rn 'preview_session\|proxy_file\|simplify_filter' src/stoat_ferret/api/

# List Phase 4 preview/proxy types exercised in smoke tests
grep -rn 'PreviewSession\|ProxyFile\|PreviewQuality\|preview_session\|proxy_file\|simplify_filter' tests/smoke/
```

**Action:** Compare output. When preview or proxy model types or identifiers change, verify that smoke tests exercise the updated interfaces. Changes to `PreviewQuality` or `simplify_filter` may affect filter generation and should be validated against preview endpoint smoke tests.

### Thumbnail and Waveform Model Changes (Phase 4)

**Trigger:** Changes to Phase 4 media visualization types (`ThumbnailStrip`, `Waveform`) or their identifiers in Python or Rust source.

**Detection:**

```bash
# List Phase 4 thumbnail/waveform model definitions in Python
grep -rn 'class.*ThumbnailStrip\|class.*Waveform' src/

# List Phase 4 thumbnail/waveform model definitions in Rust
grep -rn 'pub struct ThumbnailStrip\|pub struct Waveform\|pub enum ThumbnailStrip\|pub enum Waveform' rust/stoat_ferret_core/src/

# List Phase 4 thumbnail/waveform identifier usage in API schemas and routers
grep -rn 'thumbnail_strip\|waveform' src/stoat_ferret/api/

# List Phase 4 thumbnail/waveform types exercised in smoke tests
grep -rn 'ThumbnailStrip\|Waveform\|thumbnail_strip\|waveform' tests/smoke/
```

**Action:** Compare output. When thumbnail or waveform model types or identifiers change, verify that smoke tests exercise the updated interfaces. Waveform changes may affect both PNG and JSON output formats.

### Theater Mode Component Changes (Phase 4)

**Trigger:** Changes to Phase 4 Theater Mode types (`TheaterMode`) or their identifiers in GUI source.

**Detection:**

```bash
# List Phase 4 Theater Mode component definitions
grep -rn 'TheaterMode\|theater_mode\|theaterMode' gui/src/

# List Phase 4 Theater Mode store definitions
grep -rn 'theaterStore\|isFullscreen\|isHUDVisible' gui/src/stores/

# List Theater Mode references in UAT journeys
grep -rn 'theater_mode\|TheaterMode\|theater' scripts/uat_journey_*.py
```

**Action:** Compare output. When Theater Mode components or identifiers change, verify that UAT journey scripts still exercise the updated interfaces. Changes to fullscreen or HUD visibility logic may affect keyboard shortcut handling.

### Sample Project Artifact Sync

**Trigger:** Changes to any of the three sample project artifacts:
- `scripts/seed_sample_project.py` — constants: `CLIP_DEFS`, `EFFECT_DEFS`, `TRANSITION_DEFS`, `SAMPLE_VIDEOS`
- `tests/smoke/conftest.py` — `sample_project` fixture values
- `docs/setup/guides/sample-project.md` — documented values shown to users

**Detection:**

```bash
# Check if any sample project artifact was modified
git diff --name-only HEAD~1 | grep -E 'scripts/seed_sample_project\.py|tests/smoke/conftest\.py|docs/setup/guides/sample-project\.md'
```

**Action:** When any of the three artifacts changes, verify the changed values match across all three. Check that clip frame values (in/out points, timeline positions), effect type names and parameters, transition type names and parameters, video filenames, and output settings are identical in the seed script constants, the smoke test fixture, and the user guide content.
