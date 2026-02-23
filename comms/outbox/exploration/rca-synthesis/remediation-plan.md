# Remediation Plan

Recommendations grouped by target. Only recommendations that survived critical review are included.

---

## Group 1: auto-dev-mcp Process Changes

These are general improvements to the orchestration system that would benefit all projects. Each should become a product request on auto-dev-mcp.

### 1A. Track Descoped Items as Backlog During Design

**What:** When a feature's requirements.md lists an "Out of Scope" item that corresponds to a design-doc specification or a prior backlog item, the executing agent should create a `deferred` backlog item.

**Where it belongs:** `docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/007-document-drafts.md` — add instruction in Step 5 (draft requirements.md) that says: "For each Out of Scope item that references a design-doc feature or existing capability, include a note in the requirements that a deferred backlog item should be created during execution."

**Why:** Three of six RCAs trace back to work that was descoped without tracking. This is the single highest-impact process change.

**Evidence:** rca-no-cancellation (cancellation descoped at `requirements.md:32`, no BL created), rca-clip-management (read-only delivered, no BL for CRUD), rca-no-progress (progress field stubbed, no BL for wiring).

**Concrete next step:** Create a product request on auto-dev-mcp describing this convention and the specific file to modify.

### 1B. Retrospective Debt Ingestion into Backlog

**What:** The retrospective backlog-verification step should cross-reference tech debt sections from theme retrospectives and create backlog items for any debt not already tracked.

**Where it belongs:** `docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/003-backlog-verification.md` — add a Step 5.5 or modify Step 5 (orphaned items check) to also scan theme retrospective tech-debt tables and verify each item has a corresponding open BL item.

**Why:** Both v004 theme and version retrospectives identified "no job cancellation API" as tech debt but created no backlog items. The debt sat in markdown until a user hit it.

**Evidence:** rca-no-cancellation evidence shows retrospective.md:49 (theme) and retrospective.md:72 (version) both acknowledged the gap with no BL item created.

**Concrete next step:** Create a product request on auto-dev-mcp describing the addition to the backlog-verification retrospective step.

### 1C. Wiring Audit: Add "Uncovered Endpoints" Check

**What:** Wiring audits should include a step that lists all write endpoints (POST, PATCH, DELETE) and checks whether any GUI component calls each one. Report uncovered endpoints as "unwired" alongside broken wiring.

**Where it belongs:** The wiring audit prompt/methodology in auto-dev-mcp. The v006-v007 audit already caught the transition API gap (same pattern), showing the methodology is inconsistent — it catches some absent wiring but not all.

**Why:** The clip CRUD gap and transition GUI gap are both instances where backend capabilities had no frontend surface. A systematic check would catch these.

**Evidence:** rca-clip-management shows v005 audit found 3 gaps but missed clip CRUD. v006-v007 audit caught transition API (same pattern).

**Concrete next step:** Create a product request on auto-dev-mcp to formalize the "uncovered endpoints" check in wiring audit methodology.

### 1D. End-to-End Wiring Verification in Completion Reports

**What:** When a feature creates an API field, endpoint, or UI element intended to display dynamic data, the completion report must include evidence that the data flows end-to-end — not just that the schema/field exists.

**Where it belongs:** The feature implementation prompt (`docs/auto-dev/PROMPTS/feature-implementation.md`) in the completion report section. Add a requirement: "For fields/endpoints that return dynamic data, include evidence (test output, log line, or API response) showing a non-default value."

**Why:** v004 Feature 002 marked FR-2 (progress reporting) PASS because `JobStatusResponse.progress` existed as a schema field, but it always returned `None`.

**Evidence:** rca-no-progress evidence trail, Section 3 (v004 Feature 002 completion report false PASS).

**Concrete next step:** Create a product request on auto-dev-mcp describing the completion report enhancement.

---

## Group 2: stoat-and-ferret IMPACT_ASSESSMENT.md

These are project-specific checks that should live in `docs/auto-dev/IMPACT_ASSESSMENT.md` for stoat-and-ferret. This file does not exist yet and should be created.

### 2A. Async Safety Check

**What:** During impact assessment, flag any feature plan that introduces or modifies code calling `subprocess.run()`, `subprocess.call()`, `subprocess.check_output()`, or `time.sleep()` inside files containing `async def`.

**Why:** The ffprobe blocking bug was caused by `subprocess.run()` inside an async context. This check would flag it at design time.

**Evidence:** rca-ffprobe-blocking root cause #1. `probe.py:65` uses `subprocess.run()` called from `async def scan_directory()`.

### 2B. Settings Documentation Check

**What:** If a version adds or modifies Settings fields in `src/stoat_ferret/api/settings.py`, verify that `.env.example` is updated to match.

**Why:** 9 versions shipped without .env.example. A design-time check ensures this doesn't recur.

**Evidence:** rca-no-env-example timeline showing settings added incrementally v003-v008 with no documentation.

### 2C. Cross-Version Wiring Assumptions

**What:** When a version's features depend on behavior delivered in a prior version (e.g., frontend consuming a backend field), the impact assessment should list these assumptions explicitly so the implementation plan can include verification tests.

**Why:** v005's ScanModal assumed v004's progress reporting worked. It didn't. Listing assumptions at design time makes them testable.

**Evidence:** rca-no-progress RC-2 (no cross-version requirement tracing).

### 2D. GUI Input Mechanism Check

**What:** For GUI features that accept user input (paths, text, selections), verify that the implementation plan specifies an appropriate input mechanism (not just "text input" for file paths).

**Why:** The browse button gap was a specification omission. A lightweight checklist prompt during impact assessment could flag obvious UX gaps.

**Evidence:** rca-no-browse-button showing `implementation-plan.md:52` specified "directory path input" without questioning whether text-only is sufficient.

**Concrete next step for all Group 2 items:** Create `docs/auto-dev/IMPACT_ASSESSMENT.md` with sections for each check. This is a single file creation, not multiple changes.

---

## Group 3: stoat-and-ferret Code/Config Changes

These are concrete code changes to the project itself.

### 3A. Custom Blocking-in-Async CI Check

**What:** Add a CI script or pre-commit check that flags `subprocess.run(`, `subprocess.call(`, `time.sleep(` inside Python files that also contain `async def`.

**Where:** A script in `scripts/` or a ruff plugin configuration. Run as part of quality gates.

**Why:** Directly prevents the ffprobe-blocking class of bug at CI time. Simple grep-based check.

**Evidence:** rca-ffprobe-blocking recommendation #2. Three `subprocess.run()` calls exist in `src/` — one already causing issues, one will cause the same issue when render jobs use the async queue.

**Concrete next step:** Create a backlog item for the lint check. Implementation is ~20 lines of shell script.

### 3B. Event-Loop Responsiveness Integration Test

**What:** A test that starts a scan, then verifies `GET /api/v1/jobs/{id}` responds within a threshold (e.g., 2s) while the scan is running. Must use real (or simulated-slow) subprocess calls, not mocks.

**Where:** `tests/integration/` — requires a test that doesn't mock `ffprobe_video()`.

**Why:** All current scan tests mock `ffprobe_video()`, making the blocking behavior invisible. This test catches event-loop starvation.

**Evidence:** rca-ffprobe-blocking recommendation #3.

**Concrete next step:** Create a backlog item. Note: this test is only meaningful after BL-072 (fix blocking ffprobe) is implemented — otherwise it would just fail on the known bug.

### 3C. Fix API Spec Examples

**What:** Update `docs/design/05-api-specification.md` running-state job example to show `"progress": 0.45` instead of `"progress": null`.

**Where:** `docs/design/05-api-specification.md` lines 280-361.

**Why:** The spec normalized null progress, making it appear correct to implementors.

**Evidence:** rca-no-progress evidence trail, Section 1.

**Concrete next step:** Create a backlog item (small, P3).

---

## Group 4: stoat-and-ferret Learnings

### 4A. Learning: "Schema Without Wiring" Anti-Pattern

**What:** Save a learning documenting the pattern where a schema field, UI element, or infrastructure component exists but is never connected to a data source. Three instances: progress field (always null), WebSocket broadcasts (never called), cancel button (disabled during scanning).

**Why:** This is the most recurring anti-pattern in the project. A learning ensures future design phases check for it.

**Evidence:** rca-no-progress, rca-no-cancellation, BL-065.

### 4B. Learning: "Descoped Without Backlog" Anti-Pattern

**What:** Save a learning documenting the pattern where work is explicitly or implicitly descoped during design/implementation but no backlog item is created, making it invisible to future planning.

**Why:** Three of six RCAs trace to this pattern. A learning codifies the lesson.

**Evidence:** rca-no-cancellation (explicit descoping), rca-clip-management (implicit deferral), rca-no-progress (stubbed without wiring).

### 4C. Learning: "Research Findings Not Tracked as Backlog"

**What:** Save a learning documenting that v004 research (`codebase-patterns.md:100`) explicitly identified the blocking ffprobe pattern but no backlog item was created. Research findings should generate BL items for identified issues.

**Why:** Captures the specific failure mode where analysis identifies a problem but the pipeline doesn't track it.

**Evidence:** rca-ffprobe-blocking evidence trail, Section 4.

---

## Group 5: Not Worth Doing

| Recommendation | Source RCA | Why Not |
|---|---|---|
| Add ASYNC ruff rules | rca-ffprobe-blocking #1 | RCA itself acknowledges these target trio/anyio, not asyncio. Would not catch the bug. |
| Modal/dialog wireframes in design docs | rca-no-browse-button #1 | Design docs exist and aren't being rewritten. Retroactive effort for speculative future benefit. |
| UX-specific acceptance criteria | rca-no-browse-button #2 | Impossible to enforce exhaustively. Can't anticipate every UX pattern. |
| Standard UX patterns in implementation plans | rca-no-browse-button #3 | Same issue — asking the agent to think of things nobody thought of. |
| UX gap detection in retrospectives | rca-no-browse-button #5 | Retrospectives can't catch gaps nobody has identified as gaps. |
| Developer onboarding in version design checklists | rca-no-env-example #2 | Over-engineering for a single-developer project. |
| Retrospective question for documentation gaps | rca-no-env-example #3 | Unbounded scope — can't add a retrospective question for every possible artifact. |
| Design-doc traceability check | rca-no-cancellation R3 | Complex to operationalize (parsing milestones, mapping to AC). R1 (descoped→backlog) is sufficient. |
| Split Out of Scope sections | rca-no-cancellation R5 | Cosmetic. R1 already ensures descoped items get tracked. |
| Retrospective "backend without GUI" check | rca-clip-management #3 | Too specific. The wiring audit expansion (1C) covers this more generally. |
| Companion BL items for phased work | rca-clip-management #4 | Redundant with 1A (descoped→backlog tracking). |

---

## Priority Order

| Priority | Item | Group | Effort | Impact |
|---|---|---|---|---|
| P1 | Track descoped items as backlog | 1A | Low | High — prevents 3 of 6 RCA patterns |
| P1 | Retrospective debt ingestion | 1B | Low | High — closes feedback loop |
| P1 | Schema-without-wiring learning | 4A | Trivial | Medium — knowledge capture |
| P1 | Descoped-without-backlog learning | 4B | Trivial | Medium — knowledge capture |
| P1 | Research-not-tracked learning | 4C | Trivial | Medium — knowledge capture |
| P1 | Create IMPACT_ASSESSMENT.md | 2A-D | Low | High — enables 4 project-specific checks |
| P2 | Blocking-in-async CI check | 3A | Low | High — direct prevention |
| P2 | Wiring audit expansion | 1C | Medium | Medium — catches backend/GUI gaps |
| P2 | End-to-end wiring in completion reports | 1D | Low | Medium — prevents false PASSes |
| P2 | Event-loop responsiveness test | 3B | Medium | Medium — after BL-072 is fixed |
| P3 | Fix API spec examples | 3C | Trivial | Low — local improvement |
