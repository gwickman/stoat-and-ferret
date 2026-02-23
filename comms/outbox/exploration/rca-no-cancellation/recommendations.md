# Recommendations: Preventing Omission of Specified Design Features

## Already Addressed

1. **BL-074 created** (2026-02-23): Backlog item now exists for job cancellation with detailed acceptance criteria covering `AsyncioJobQueue.cancel()`, cancel API endpoint, scan handler checkpoint, and frontend wiring.

2. **BL-073 created** (2026-02-23): Companion item for progress reporting, which was also specified in design but delivered as a non-functional stub (progress bar permanently at 0%).

3. **LRN-016** (Validate Acceptance Criteria Against Codebase During Design): Learning captured from v004 about validating that acceptance criteria reference existing capabilities. However, this learning addresses a different failure mode (unachievable criteria) than the one here (missing criteria).

## Recommended Process Changes

### R1: Track Descoped Items as Backlog During Design

**Problem:** The v004 async-scan-endpoint requirements explicitly descoped cancellation ("Scan cancellation — not required for initial implementation") but created no backlog item. The retrospective noted it as tech debt but still created no backlog item. The gap was invisible to future version planning.

**Recommendation:** When a feature's requirements document lists an "Out of Scope" item that corresponds to a design-doc specification, the design agent should create a backlog item tagged `deferred` with a reference to the originating design spec. This makes descoped work visible to the planning pipeline.

**Where to implement:** `docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/007-document-drafts.md` — add a step requiring backlog items for descoped design-doc requirements.

### R2: Retrospective Tech Debt Should Generate Backlog Items

**Problem:** Both the v004 theme and version retrospectives identified "no job cancellation API" as tech debt, but neither created a backlog item. The debt sat in retrospective markdown files where it was invisible to the planning pipeline.

**Recommendation:** The retrospective backlog-verification step (`docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/003-backlog-verification.md`) should cross-reference the tech debt section of each theme retrospective and create backlog items for any tech debt not already tracked. Currently this step verifies completions and finds orphans, but does not ingest new debt from retrospectives.

**Where to implement:** Add a "tech debt ingestion" section to the backlog-verification retrospective task.

### R3: Design-Doc Traceability Check During Version Planning

**Problem:** The design docs specify cancellation in 6 places (roadmap, API spec, architecture, GUI wireframes). The version design process did not check whether planned features covered all aspects of the referenced design-doc milestones. BL-027 mapped to Milestone 5.4 but only partially implemented it.

**Recommendation:** During the backlog analysis step of version design (`002-backlog-analysis.md`), when a backlog item references a design-doc milestone, the agent should verify that the item's acceptance criteria cover all sub-items of that milestone. If not, flag the gap for the human reviewer or create supplementary backlog items.

**Where to implement:** `docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/002-backlog-analysis.md` — add design-doc traceability validation.

### R4: GUI Features Must Validate Backend API Availability

**Problem:** v005's library browser shipped a cancel button without verifying that a cancel API endpoint existed. The button was rendered disabled during scans — non-functional by design, but misleading because the UI implies the capability exists.

**Recommendation:** When a GUI feature includes a user-facing control (button, action, menu item), the requirements should include an acceptance criterion verifying the backend endpoint exists and is callable. If the endpoint doesn't exist, the feature should either omit the control or explicitly state it's a placeholder with a backlog reference.

**Where to implement:** This is a design-agent convention. Add a note to the GUI feature requirements template about verifying backend API availability for interactive controls.

### R5: Distinguish "Out of Scope" from "Not Needed"

**Problem:** The v004 requirements used "Out of Scope" to mean both "deferred to later" (cancellation) and "not needed at this scale" (multiple workers). These have different follow-up requirements — deferred items need backlog tracking, while scale-dependent items don't.

**Recommendation:** Split "Out of Scope" into two explicit sections in requirement templates:
- **Deferred** — Will be needed; not in this feature's scope. Each item gets a backlog reference.
- **Not Applicable** — Not needed for current requirements or scale. No backlog tracking needed.

**Where to implement:** Feature requirements template in the design prompt system.

## Priority Assessment

| # | Recommendation | Impact | Effort |
|---|---------------|--------|--------|
| R1 | Track descoped items as backlog | High — prevents invisible gaps | Low — template change |
| R2 | Retrospective debt ingestion | High — closes the feedback loop | Medium — prompt modification |
| R3 | Design-doc traceability | Medium — catches partial implementations | Medium — analysis step addition |
| R4 | GUI-backend API validation | Medium — prevents dead UI elements | Low — convention addition |
| R5 | Split Out of Scope sections | Low — improves clarity | Low — template change |
