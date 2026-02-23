# Project Backlog

*Last updated: 2026-02-23 17:59*

**Total completed:** 59 | **Cancelled:** 0

## Priority Summary

| Priority | Name | Count |
|----------|------|-------|
| P0 | Critical | 1 |
| P1 | High | 4 |
| P2 | Medium | 6 |
| P3 | Low | 5 |

## Quick Reference

| ID | Pri | Size | Title | Description |
|----|-----|------|-------|-------------|
| <a id="bl-072-ref"></a>[BL-072](#bl-072) | P0 | l | Fix blocking subprocess.run() in ffprobe freezing async event loop | The `ffprobe_video()` function in `src/stoat_ferret/ffmpe... |
| <a id="bl-073-ref"></a>[BL-073](#bl-073) | P1 | l | Add progress reporting to job queue and scan handler | The job queue (`AsyncioJobQueue`), job result model (`Job... |
| <a id="bl-074-ref"></a>[BL-074](#bl-074) | P1 | m | Implement job cancellation support for scan and job queue | The `AsyncioJobQueue` has no `cancel()` method, no cancel... |
| <a id="bl-075-ref"></a>[BL-075](#bl-075) | P1 | l | Add clip management controls (Add/Edit/Delete) to project GUI | The GUI currently displays clips in a read-only table on ... |
| <a id="bl-076-ref"></a>[BL-076](#bl-076) | P1 | l | Create IMPACT_ASSESSMENT.md with project-specific design checks | stoat-and-ferret has no IMPACT_ASSESSMENT.md, so the auto... |
| <a id="bl-061-ref"></a>[BL-061](#bl-061) | P2 | l | Wire or remove execute_command() Rust-Python FFmpeg bridge | **Current state:** `execute_command()` was built in v002/... |
| <a id="bl-069-ref"></a>[BL-069](#bl-069) | P2 | xl | Update C4 architecture documentation for v009 changes | C4 documentation was last generated for v008. v009 introd... |
| <a id="bl-070-ref"></a>[BL-070](#bl-070) | P2 | m | Add Browse button for scan directory path selection | Currently the Scan Directory feature requires users to ma... |
| <a id="bl-071-ref"></a>[BL-071](#bl-071) | P2 | m | Add .env.example file for environment configuration template | The project has no .env.example file to guide new develop... |
| <a id="bl-077-ref"></a>[BL-077](#bl-077) | P2 | l | Add CI quality gate for blocking calls in async context | No automated check exists to detect synchronous blocking ... |
| <a id="bl-078-ref"></a>[BL-078](#bl-078) | P2 | l | Add event-loop responsiveness integration test for scan pipeline | All current scan tests mock `ffprobe_video()`, making the... |
| <a id="bl-019-ref"></a>[BL-019](#bl-019) | P3 | m | Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore | Add Windows bash null redirect guidance to AGENTS.md and ... |
| <a id="bl-066-ref"></a>[BL-066](#bl-066) | P3 | l | Add transition support to Effect Workshop GUI | **Current state:** `POST /projects/{id}/effects/transitio... |
| <a id="bl-067-ref"></a>[BL-067](#bl-067) | P3 | l | Audit and trim unused PyO3 bindings from v001 (TimeRange ops, input sanitization) | **Current state:** Several Rust functions are exposed via... |
| <a id="bl-068-ref"></a>[BL-068](#bl-068) | P3 | l | Audit and trim unused PyO3 bindings from v006 filter engine | **Current state:** Three v006 filter engine features (Exp... |
| <a id="bl-079-ref"></a>[BL-079](#bl-079) | P3 | l | Fix API spec examples to show realistic progress values for running jobs | The API specification at `docs/design/05-api-specificatio... |

## Tags Summary

| Tag | Count | Items |
|-----|-------|-------|
| user-feedback | 6 | BL-070, BL-071, BL-072, BL-073, ... |
| gui | 5 | BL-066, BL-070, BL-073, BL-074, ... |
| scan | 4 | BL-072, BL-073, BL-074, BL-078 |
| rca | 4 | BL-076, BL-077, BL-078, BL-079 |
| wiring-gap | 3 | BL-061, BL-066, BL-075 |
| rust-python | 3 | BL-061, BL-067, BL-068 |
| documentation | 3 | BL-069, BL-071, BL-079 |
| async | 3 | BL-072, BL-077, BL-078 |
| ffmpeg | 2 | BL-061, BL-072 |
| dead-code | 2 | BL-067, BL-068 |
| api-surface | 2 | BL-067, BL-068 |
| ux | 2 | BL-070, BL-073 |
| jobs | 2 | BL-073, BL-074 |
| windows | 1 | BL-019 |
| agents-md | 1 | BL-019 |
| gitignore | 1 | BL-019 |
| effects | 1 | BL-066 |
| transitions | 1 | BL-066 |
| architecture | 1 | BL-069 |
| c4 | 1 | BL-069 |
| library | 1 | BL-070 |
| devex | 1 | BL-071 |
| onboarding | 1 | BL-071 |
| bug | 1 | BL-072 |
| api | 1 | BL-074 |
| clips | 1 | BL-075 |
| crud | 1 | BL-075 |
| process | 1 | BL-076 |
| auto-dev | 1 | BL-076 |
| impact-assessment | 1 | BL-076 |
| ci | 1 | BL-077 |
| quality-gates | 1 | BL-077 |
| lint | 1 | BL-077 |
| testing | 1 | BL-078 |
| integration | 1 | BL-078 |
| api-spec | 1 | BL-079 |

## Tag Conventions

Use only approved tags when creating or updating backlog items. This reduces fragmentation and improves tag-based filtering.

### Approved Tags

| Tag | Description |
|-----|-------------|
| `process` | Process improvements, workflow changes, governance |
| `tooling` | MCP tools, CLI tooling, development infrastructure |
| `cleanup` | Code cleanup, refactoring, tech debt removal |
| `documentation` | Documentation improvements and maintenance |
| `execution` | Version/feature execution pipeline |
| `feature` | New feature development |
| `knowledge-management` | Learnings, institutional memory, bug tracking |
| `reliability` | System reliability, health checks, resilience, performance |
| `plugins` | Plugin integration and development |
| `testing` | Test infrastructure, test quality, code quality audits |
| `architecture` | Architecture documentation and decisions (incl. C4) |
| `notifications` | Notifications and alerting |
| `skills` | Chatbot skills and hierarchy |
| `integration` | External system integration |
| `research` | Research and investigation tasks |
| `claude-code` | Claude Code CLI-specific concerns |
| `async` | Async patterns and operations |
| `dx` | Developer/operator experience |

### Consolidation Rules

When a tag is not in the approved list, map it to the nearest approved tag:

| Retired Tag | Use Instead |
|-------------|-------------|
| `automation`, `design`, `design-workflow`, `guardrails`, `safety`, `permissions`, `capabilities`, `safeguard`, `chatbot-discipline` | `process` |
| `cli`, `logging`, `infrastructure`, `mcp-tools`, `mcp-protocol`, `bootstrap`, `exploration`, `multi-project` | `tooling` |
| `deprecation`, `refactoring`, `maintenance`, `audit`, `DRY`, `YAGNI` | `cleanup` |
| `setup` | `documentation` |
| `version-execution`, `watchdog`, `containers` | `execution` |
| `enhancement`, `discovery` | `feature` |
| `knowledge-extraction`, `troubleshooting` | `knowledge-management` |
| `health-check`, `dependencies`, `resilience`, `performance` | `reliability` |
| `quality`, `code-quality` | `testing` |
| `c4` | `architecture` |
| `skill` | `skills` |
| `ux` | `dx` |
| `efficiency`, `async-cli` | `async` |

### Version-Specific Tags

Tags like `v070-tech-debt` are acceptable temporarily to group related items from a specific version. Once all items with that tag are completed, the tag naturally expires. Prefer using `cleanup` plus a version reference in the item description over creating new version-specific tags.

## Item Details

### P0: Critical

#### 📋 BL-072: Fix blocking subprocess.run() in ffprobe freezing async event loop

**Status:** open
**Tags:** bug, async, ffmpeg, scan, user-feedback

The `ffprobe_video()` function in `src/stoat_ferret/ffmpeg/probe.py` uses synchronous `subprocess.run()` with a 30s timeout per file. This is called from the async scan handler, which blocks the entire asyncio event loop for the duration of each ffprobe call. While blocked, the server cannot handle any HTTP requests — including job status polling — making the scan appear completely frozen. This also makes `asyncio.wait_for()` timeout unreliable since the event loop has no opportunity to check it between blocking calls. This is the primary cause of the "scan directory hangs forever" bug.

**Use Case:** When a user scans a media directory, the server must remain responsive so progress polling, cancellation, and other API calls continue working throughout the scan.

**Acceptance Criteria:**
- [ ] ffprobe_video() uses asyncio.create_subprocess_exec() or asyncio.to_thread() instead of blocking subprocess.run()
- [ ] HTTP status polling endpoint remains responsive during an active scan job
- [ ] asyncio.wait_for() job timeout fires reliably at the configured threshold
- [ ] Existing ffprobe tests pass with the async implementation
- [ ] Scan of a directory with multiple video files completes without blocking other API requests

[↑ Back to list](#bl-072-ref)

### P1: High

#### 📋 BL-073: Add progress reporting to job queue and scan handler

**Status:** open
**Tags:** jobs, scan, gui, ux, user-feedback

The job queue (`AsyncioJobQueue`), job result model (`JobResult`), and job status response (`JobStatusResponse`) have no progress field. The scan handler processes files in a loop but never reports intermediate progress. The frontend polls job status but always receives `null` for progress, so the progress bar is permanently stuck at 0%. Users have no visibility into how far along a scan is or whether it's actually working.

**Use Case:** During a directory scan that may take minutes, users need to see real progress to know the operation is working and estimate remaining time.

**Acceptance Criteria:**
- [ ] _AsyncJobEntry includes a progress field (0.0-1.0 float or integer percentage)
- [ ] AsyncioJobQueue exposes a set_progress(job_id, value) method callable from within job handlers
- [ ] Scan handler calls set_progress after each file, reporting scanned_count/total_files
- [ ] GET /api/v1/jobs/{id} response includes a populated progress field during active jobs
- [ ] Frontend ScanModal progress bar reflects actual scan progress in real time

[↑ Back to list](#bl-073-ref)

#### 📋 BL-074: Implement job cancellation support for scan and job queue

**Status:** open
**Tags:** jobs, scan, api, gui, user-feedback

The `AsyncioJobQueue` has no `cancel()` method, no cancellation flag mechanism, and no cancel API endpoint. The scan handler's file processing loop has no cancellation check point. The frontend cancel button exists in ScanModal but has nothing to call — once a scan starts, the only way to stop it is to restart the server. Users are stuck waiting for potentially long scans with no way to abort.

**Use Case:** When a user accidentally scans the wrong directory or needs to stop a long-running scan, they need the cancel button to actually work rather than being forced to restart the application.

**Acceptance Criteria:**
- [ ] AsyncioJobQueue has a cancel(job_id) method that sets a cancellation flag on the running job
- [ ] A cancel API endpoint exists (DELETE /api/v1/jobs/{id} or POST /api/v1/jobs/{id}/cancel) returning appropriate status
- [ ] Scan handler checks the cancellation flag between file iterations and exits cleanly when cancelled
- [ ] Cancelled jobs report status 'cancelled' with partial results (files scanned so far are retained)
- [ ] Frontend ScanModal cancel button calls the cancel endpoint and updates UI to reflect cancellation

[↑ Back to list](#bl-074-ref)

#### 📋 BL-075: Add clip management controls (Add/Edit/Delete) to project GUI

**Status:** open
**Tags:** gui, clips, crud, wiring-gap, user-feedback

The GUI currently displays clips in a read-only table on the ProjectDetails page but provides no controls to add, edit, or remove clips. The backend API has full CRUD support for clips (POST, PATCH, DELETE on `/api/v1/projects/{id}/clips`) — all implemented and integration-tested — but the frontend never calls the write endpoints. Users must use the API directly to manage clips, which defeats the purpose of having a GUI. This was deferred from v005 (Phase 1 delivered read-only display) but is now a significant gap in the user workflow.

**Use Case:** When building a project in the GUI, users need to add video clips from their library, adjust clip boundaries, and remove clips without switching to API calls or external tools.

**Acceptance Criteria:**
- [ ] ProjectDetails page includes an Add Clip button that opens a form to create a new clip (selecting from library videos, setting in/out points)
- [ ] Each clip row in the project clips table has Edit and Delete action buttons
- [ ] Edit button opens an inline or modal form pre-populated with current clip properties (in/out points, label)
- [ ] Delete button prompts for confirmation then removes the clip via DELETE /api/v1/projects/{id}/clips/{clip_id}
- [ ] Add/Edit forms validate input and display errors from the backend (e.g. invalid time ranges)
- [ ] Clip list refreshes after any add/update/delete operation

[↑ Back to list](#bl-075-ref)

#### 📋 BL-076: Create IMPACT_ASSESSMENT.md with project-specific design checks

**Status:** open
**Tags:** process, auto-dev, impact-assessment, rca

stoat-and-ferret has no IMPACT_ASSESSMENT.md, so the auto-dev design phase runs no project-specific checks. RCA analysis identified four recurring issue patterns that project-specific impact assessment checks would catch at design time: (1) blocking subprocess calls in async context (caused the ffprobe event-loop freeze), (2) Settings fields added without .env.example updates (9 versions without .env.example), (3) features consuming prior-version backends without verifying they work (progress bar assumed v004 progress worked — it didn't), (4) GUI features with text-only input where richer mechanisms are standard (scan directory path with no browse button).

**Use Case:** During version design, the auto-dev impact assessment step reads this file and executes project-specific checks, catching recurring issue patterns before they reach implementation.

**Acceptance Criteria:**
- [ ] IMPACT_ASSESSMENT.md exists at docs/auto-dev/IMPACT_ASSESSMENT.md
- [ ] Contains async safety check: flag features that introduce or modify subprocess.run/call/check_output or time.sleep inside files containing async def
- [ ] Contains settings documentation check: if a version adds or modifies Settings fields, verify .env.example is updated
- [ ] Contains cross-version wiring assumptions check: when features depend on behavior from prior versions, list assumptions explicitly
- [ ] Contains GUI input mechanism check: for GUI features accepting user input, verify appropriate input mechanisms are specified
- [ ] Each check section includes what to look for, why it matters, and a concrete example from project history

**Notes:** IMPACT_ASSESSMENT.md is project-specific, not an auto-dev process artifact. Treat as project code — the assessment criteria are tailored to stoat-and-ferret's architecture and design constraints.

[↑ Back to list](#bl-076-ref)

### P2: Medium

#### 📋 BL-061: Wire or remove execute_command() Rust-Python FFmpeg bridge

**Status:** open
**Tags:** wiring-gap, ffmpeg, rust-python

**Current state:** `execute_command()` was built in v002/04-ffmpeg-integration as the bridge between the Rust command builder and the Python FFmpeg executor. It has zero callers in production code.

**Gap:** The function exists and is tested in isolation but is never used in any render or export workflow.

**Impact:** The Rust-to-Python FFmpeg pipeline has no integration point. Either the bridge needs wiring into a real workflow, or it's dead code that should be removed to reduce maintenance burden.

**Acceptance Criteria:**
- [ ] execute_command() is called by at least one render/export code path connecting Rust command builder output to Python FFmpeg executor
- [ ] Render workflow produces a working output file via the Rust→Python bridge
- [ ] If execute_command() is genuinely unnecessary, it is removed along with its tests

[↑ Back to list](#bl-061-ref)

#### 📋 BL-069: Update C4 architecture documentation for v009 changes

**Status:** open
**Tags:** architecture, c4, documentation

C4 documentation was last generated for v008. v009 introduced 6 features across 2 themes (observability-pipeline, gui-runtime-fixes) that created architecture drift in 5 areas:

1. **configure_logging() now includes RotatingFileHandler**: C4 Data Access component describes logging config as "JSON/console logging setup" but code now includes file-based logging with rotation (log_dir parameter, 10MB rotation, 5 backups). Evidence: src/stoat_ferret/logging.py:18-21,78-80.

2. **Project Repository missing count() method**: C4 Data Access lists Project Repository operations as "add, get, list_projects, update, delete" — missing the new count() method added for pagination. Evidence: src/stoat_ferret/db/project_repository.py:87,190,254.

3. **SPA routing uses catch-all routes, not StaticFiles mount**: C4 API Gateway states "Static File Serving: GUI static files mounted at /gui" but StaticFiles was replaced with @app.get("/gui") and @app.get("/gui/{path:path}") catch-all routes serving files with SPA fallback. Evidence: src/stoat_ferret/api/app.py:206-211.

4. **ObservableFFmpegExecutor and AuditLogger wired into create_app() lifespan**: These were pre-existing dead code documented in v008 C4 but are now actively wired as DI components in the lifespan — ObservableFFmpegExecutor wrapping RealFFmpegExecutor, AuditLogger with separate sync SQLite connection. Evidence: src/stoat_ferret/api/app.py:86-94.

5. **WebSocket broadcasts actively wired**: v008 C4 listed SCAN_STARTED, SCAN_COMPLETED, PROJECT_CREATED event types but broadcast() calls were not wired. v009 added active broadcast calls in scan handler and project creation router. Evidence: src/stoat_ferret/api/services/scan.py:84,94 and src/stoat_ferret/api/routers/projects.py:150.

The version retrospective also notes C4 regeneration was attempted but failed for v009.

**Use Case:** During version planning and onboarding, developers and the design agent consult C4 documentation to understand the current architecture. Stale documentation leads to incorrect assumptions about component capabilities and wiring, causing design decisions based on outdated information.

**Acceptance Criteria:**
- [ ] C4 Data Access component documents configure_logging() file rotation capability with log_dir parameter
- [ ] C4 Data Access component lists count() in Project Repository operations
- [ ] C4 API Gateway component describes SPA catch-all routing pattern instead of StaticFiles mount
- [ ] C4 API Gateway component reflects ObservableFFmpegExecutor and AuditLogger as DI-managed lifespan components
- [ ] C4 container/context docs reflect that WebSocket broadcast events are actively wired (not just defined)

**Notes:** size: l — C4 regeneration following established process, auto-estimate inflated by detailed description listing all 5 drift areas with code evidence

[↑ Back to list](#bl-069-ref)

#### 📋 BL-070: Add Browse button for scan directory path selection

**Status:** open
**Tags:** gui, ux, library, user-feedback

Currently the Scan Directory feature requires users to manually type or paste a directory path. There is no file/folder browser dialog to help users navigate to and select the target directory. This creates friction - users must know the exact path and type it correctly, which is error-prone and a poor UX pattern for desktop-style file selection.

**Use Case:** When a user wants to scan a media directory, they need to navigate to it visually rather than remembering and typing the full path, especially on systems with deep directory hierarchies.

**Acceptance Criteria:**
- [ ] Scan Directory UI includes a Browse button next to the path input field
- [ ] Clicking Browse opens a folder selection dialog that allows navigating the filesystem
- [ ] Selecting a folder in the dialog populates the path input field with the chosen path
- [ ] Users can still manually type a path as an alternative to browsing

[↑ Back to list](#bl-070-ref)

#### 📋 BL-071: Add .env.example file for environment configuration template

**Status:** open
**Tags:** devex, documentation, onboarding, user-feedback

The project has no .env.example file to guide new developers or users through environment configuration. Anyone setting up the project must reverse-engineer which environment variables are needed by reading source code. This is a common onboarding friction point - without a template, users may miss required configuration and encounter confusing startup failures.

**Use Case:** When a new developer or user clones the repo, they need a clear reference for what environment variables to configure before the application will start correctly.

**Acceptance Criteria:**
- [ ] A .env.example file exists in the project root with all required/optional environment variables documented
- [ ] Each variable includes a comment explaining its purpose and acceptable values
- [ ] The file contains sensible defaults or placeholder values (not real secrets)
- [ ] README or setup documentation references .env.example as part of the getting-started workflow

[↑ Back to list](#bl-071-ref)

#### 📋 BL-077: Add CI quality gate for blocking calls in async context

**Status:** open
**Tags:** ci, quality-gates, async, lint, rca

No automated check exists to detect synchronous blocking calls inside async code. Ruff, mypy, and pytest all pass despite `subprocess.run()` being called from an async scan handler, which froze the entire asyncio event loop. Two additional `subprocess.run()` calls exist in `src/` (executor.py:96, health.py:96) — one will cause the same problem when render jobs use the async job queue. A grep-based CI script (~20 lines) scanning for blocking calls in files containing `async def` would catch this entire class of bug at CI time.

**Acceptance Criteria:**
- [ ] A CI script or quality gate check exists that scans Python source files for blocking calls (subprocess.run, subprocess.call, subprocess.check_output, time.sleep) inside files that also contain async def
- [ ] The check runs as part of the existing quality gates (alongside ruff, mypy, pytest)
- [ ] The check fails with a clear error message identifying the file, line number, and the blocking call
- [ ] The check passes on the current codebase after BL-072 is fixed (async ffprobe)
- [ ] False positives for legitimate sync-only files are avoided by only flagging files containing async def

**Notes:** Depends on BL-072 (fix blocking ffprobe) being completed first, otherwise the check would immediately fail on the known bug.

[↑ Back to list](#bl-077-ref)

#### 📋 BL-078: Add event-loop responsiveness integration test for scan pipeline

**Status:** open
**Tags:** testing, integration, async, scan, rca

All current scan tests mock `ffprobe_video()`, making the blocking behavior that caused the "scan hangs forever" bug invisible to the test suite. No integration test verifies that the server remains responsive during a scan. An event-loop responsiveness test that uses real or simulated-slow subprocess calls (not mocks) would have caught the ffprobe blocking bug and would serve as a regression guard against future async/blocking issues in the scan pipeline.

**Acceptance Criteria:**
- [ ] An integration test exists that starts a directory scan with multiple files requiring real or simulated-slow processing
- [ ] While the scan runs, the test verifies that GET /api/v1/jobs/{id} responds within 2 seconds
- [ ] The test does NOT mock ffprobe_video — it must exercise real or simulated subprocess behavior to detect event-loop blocking
- [ ] The test fails if the event loop is starved (i.e. if blocking subprocess calls prevent polling responses)
- [ ] The test passes after BL-072 (async ffprobe) is implemented

**Notes:** Depends on BL-072 (fix blocking ffprobe) — this test validates the fix and prevents regression. Should be implemented alongside or after BL-072.

[↑ Back to list](#bl-078-ref)

### P3: Low

#### 📋 BL-019: Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore

**Status:** open
**Tags:** windows, agents-md, gitignore

Add Windows bash null redirect guidance to AGENTS.md and add `nul` to .gitignore. In bash contexts on Windows: Always use `/dev/null` for output redirection (Git Bash correctly translates this to the Windows null device). Never use bare `nul` which gets interpreted as a literal filename in MSYS/Git Bash environments. Correct: `command > /dev/null 2>&1`. Wrong: `command > nul 2>&1`.

**Use Case:** This feature addresses: Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore. It improves the system by resolving the described requirement.

**Notes:** The .gitignore half is already done (nul added to .gitignore). Remaining scope: add Windows bash /dev/null redirect guidance to AGENTS.md.

[↑ Back to list](#bl-019-ref)

#### 📋 BL-066: Add transition support to Effect Workshop GUI

**Status:** open
**Tags:** wiring-gap, gui, effects, transitions

**Current state:** `POST /projects/{id}/effects/transition` endpoint is implemented and functional, but the Effect Workshop GUI only handles per-clip effects. There is no GUI surface for the transition API.

**Gap:** The transition API was built in v007/02-effect-registry-api but the Effect Workshop GUI in v007/03 was scoped to per-clip effects only.

**Impact:** Transitions are only accessible via direct API calls. Users have no way to discover or apply transitions through the GUI.

**Acceptance Criteria:**
- [ ] Effect Workshop GUI includes a transition section or mode for applying transitions between clips
- [ ] GUI calls POST /projects/{id}/effects/transition endpoint
- [ ] User can preview and apply at least one transition type through the GUI

[↑ Back to list](#bl-066-ref)

#### 📋 BL-067: Audit and trim unused PyO3 bindings from v001 (TimeRange ops, input sanitization)

**Status:** open
**Tags:** dead-code, rust-python, api-surface

**Current state:** Several Rust functions are exposed via PyO3 but have zero production callers in Python. TimeRange list operations (find_gaps, merge_ranges, total_coverage) are design-ahead code for future timeline editing. Input sanitization functions (validate_crf, validate_speed) overlap with internal Rust validation in FFmpegCommand.build().

**Gap:** Functions were exposed "just in case" in v001 without a consuming code path. They're tested but unused.

**Impact:** Inflated public API surface increases maintenance burden and PyO3 binding complexity. Unclear to consumers which functions are intended for use vs aspirational.

**Acceptance Criteria:**
- [ ] TimeRange list operations (find_gaps, merge_ranges, total_coverage) are either used by a production code path or removed from PyO3 bindings
- [ ] Input sanitization functions (validate_crf, validate_speed, etc.) are either called from Python production code or removed from PyO3 bindings if Rust-internal validation covers the same checks
- [ ] Stub file reflects the final public API surface

[↑ Back to list](#bl-067-ref)

#### 📋 BL-068: Audit and trim unused PyO3 bindings from v006 filter engine

**Status:** open
**Tags:** dead-code, rust-python, api-surface

**Current state:** Three v006 filter engine features (Expression Engine, Graph Validation, Filter Composition) expose Python bindings via PyO3 that are only used in parity tests, never in production code. The Rust code uses these capabilities internally (e.g., DrawtextBuilder uses Expr for alpha fades, DuckingPattern uses composition).

**Gap:** PyO3 bindings were created in v006/01-filter-engine for all three features but no Python production code consumes them. The Rust-internal usage works fine without the Python bindings.

**Impact:** Six unused Python binding functions inflate the public API surface. Maintaining PyO3 wrappers for internally-consumed Rust code adds build complexity without value.

**Acceptance Criteria:**
- [ ] Expression Engine (Expr), Graph Validation (validate, validated_to_string), and Filter Composition (compose_chain, compose_branch, compose_merge) PyO3 bindings are either used by Python production code or removed from the public API
- [ ] If bindings are retained for future use, they are documented as such in the stub file
- [ ] Parity tests are updated to reflect any binding changes

[↑ Back to list](#bl-068-ref)

#### 📋 BL-079: Fix API spec examples to show realistic progress values for running jobs

**Status:** open
**Tags:** documentation, api-spec, rca

The API specification at `docs/design/05-api-specification.md` (lines 280-361) shows `"progress": null` in the running-state job status example. This normalized null progress as the correct behavior for running jobs, making it appear correct to implementors when the field was never actually populated. The spec examples should show realistic values for all states to set correct implementor expectations.

**Acceptance Criteria:**
- [ ] The running-state job example in docs/design/05-api-specification.md shows a realistic progress value (e.g. 0.45) instead of null
- [ ] All job status examples across the spec show realistic field values for their respective states

[↑ Back to list](#bl-079-ref)
