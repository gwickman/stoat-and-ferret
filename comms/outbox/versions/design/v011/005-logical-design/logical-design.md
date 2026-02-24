# Logical Design Proposal: v011

## Version Overview

**Version:** v011 — GUI Usability & Developer Experience
**Description:** Close the biggest GUI interaction gaps and improve onboarding/process documentation.
**Depends on:** v010 deployed (completed 2026-02-23)
**Scope:** 2 themes, 5 features, 5 backlog items (BL-019, BL-070, BL-071, BL-075, BL-076)

### Goals
1. Add clip CRUD controls to the GUI, wiring the frontend to existing backend endpoints
2. Replace the text-only scan path input with a backend-assisted directory browser
3. Create developer onboarding artifacts (.env.example, Windows guidance)
4. Establish project-specific design-time checks via IMPACT_ASSESSMENT.md

---

## Theme 1: 01-scan-and-clip-ux

**Goal:** Deliver the missing GUI interaction layer for media scanning and clip management. The browse button (BL-070) validates the full-stack GUI pipeline (new backend endpoint + frontend component), while clip CRUD (BL-075) wires the frontend to existing backend endpoints — closing a gap deferred since v005.

**Backlog Items:** BL-070, BL-075

### Features

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-browse-directory | Add backend directory listing endpoint and frontend browse button to ScanModal | BL-070 | None |
| 2 | 002-clip-crud-controls | Add Add/Edit/Delete clip controls to ProjectDetails with form modals and state management | BL-075 | None (backend endpoints exist) |

### Feature Details

#### 001-browse-directory (BL-070)

**Goal:** Replace text-only scan path input with a backend-assisted directory browser.

**Scope:**
- New backend endpoint: `GET /api/v1/filesystem/directories?path={parent_path}` returning subdirectories within the given path
- Reuse `allowed_scan_roots` security pattern from scan endpoint (`src/stoat_ferret/api/routers/videos.py:194-200`)
- New `DirectoryBrowser.tsx` component rendering a flat directory list (one level at a time)
- Browse button in `ScanModal.tsx` opens the browser; selecting a directory populates the path input
- Manual path typing remains as fallback

**Acceptance Criteria:**
1. ScanModal includes a Browse button next to the path input field
2. Browse button opens a directory browser showing folders from the server filesystem
3. Directory browser respects `allowed_scan_roots` — paths outside allowed roots are rejected
4. Selecting a folder populates the path input with the chosen path
5. Users can still manually type a path as an alternative
6. **End-to-end AC:** Opening ScanModal, clicking Browse, navigating to a directory, and selecting it results in the path appearing in the input field and a subsequent scan succeeding

**Design decisions:**
- Backend-assisted directory listing over `showDirectoryPicker()` — Firefox/Safari lack support (evidence: `004-research/external-research.md`)
- Flat listing per LRN-029 (Conscious Simplicity) — document upgrade to native picker when browser support improves

#### 002-clip-crud-controls (BL-075)

**Goal:** Wire frontend clip management to existing backend CRUD endpoints.

**Scope:**
- New `clipStore.ts` Zustand store following independent-store pattern (per LRN-037)
- New `ClipFormModal.tsx` for Add/Edit with fields: `source_video_id`, `in_point`, `out_point`, `timeline_position`
- Reuse existing `DeleteConfirmation.tsx` pattern for clip deletion
- Add/Edit/Delete buttons in `ProjectDetails.tsx` clip table
- API client functions for POST/PATCH/DELETE clip endpoints
- Error display from backend validation (Rust core validates time ranges)

**Acceptance Criteria:**
1. ProjectDetails page includes an Add Clip button that opens a form to create a new clip
2. Each clip row has Edit and Delete action buttons
3. Edit opens a modal pre-populated with current clip properties (in/out points, timeline_position)
4. Delete prompts for confirmation then removes the clip via DELETE endpoint
5. Add/Edit forms validate input and display errors from the backend (e.g., invalid time ranges)
6. Clip list refreshes after any add/update/delete operation
7. **End-to-end AC:** Creating a clip via the Add button, then editing its in_point via Edit, then deleting it via Delete — each operation reflected immediately in the clip table

**Note on `label` field:** BL-075 AC3 references "label" but no `label` field exists in ClipCreate/ClipUpdate schemas (evidence: `004-research/codebase-patterns.md`). Design drops `label` from the form — the backend schema is authoritative. If label support is needed later, it requires a backend schema change first.

---

## Theme 2: 02-developer-onboarding

**Goal:** Reduce onboarding friction and establish project-specific design-time quality checks. Creates the missing .env.example template, documents the Windows /dev/null pitfall, and defines impact assessment checks that catch recurring issue patterns at design time rather than in production.

**Backlog Items:** BL-071, BL-019, BL-076

### Features

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-env-example | Create .env.example with all Settings fields documented | BL-071 | None |
| 2 | 002-windows-dev-guidance | Add Windows Git Bash /dev/null guidance to AGENTS.md | BL-019 | None |
| 3 | 003-impact-assessment | Create IMPACT_ASSESSMENT.md with 4 project-specific design checks | BL-076 | 001-env-example (assessment checks for .env.example) |

### Feature Details

#### 001-env-example (BL-071)

**Goal:** Create .env.example documenting all environment configuration variables.

**Scope:**
- New `.env.example` in project root with all 11 Settings fields (10 configurable + allowed_scan_roots)
- Each variable with STOAT_ prefix, comment explaining purpose, default value
- Grouped by category: database, API server, logging, security, frontend
- Update `docs/setup/02_development-setup.md` to reference .env.example
- Update `docs/manual/01_getting-started.md` to reference .env.example
- Update `docs/setup/04_configuration.md` to add 2 missing variables (log_backup_count, log_max_bytes)

**Acceptance Criteria:**
1. `.env.example` exists in project root with all 11 Settings fields
2. Each variable includes a comment explaining purpose and acceptable values
3. Contains sensible defaults matching Settings class (not real secrets)
4. `docs/setup/02_development-setup.md` references .env.example in setup steps
5. `docs/setup/04_configuration.md` documents all 11 variables (fixes 2-variable gap)
6. **End-to-end AC:** A new developer can `cp .env.example .env` and start the application with default settings

#### 002-windows-dev-guidance (BL-019)

**Goal:** Document the Windows Git Bash /dev/null vs nul pitfall in AGENTS.md.

**Scope:**
- Add "Windows (Git Bash)" section to AGENTS.md after Commands section (line 46)
- Document correct usage: `/dev/null` (Git Bash translates to Windows null device)
- Warn against `nul` (creates literal file in MSYS/Git Bash)
- Include correct/incorrect examples
- .gitignore already has `nul` entry — no change needed

**Acceptance Criteria:**
1. AGENTS.md contains a "Windows (Git Bash)" section
2. Documents /dev/null as correct for Git Bash on Windows
3. Warns against bare nul with explanation of MSYS behavior
4. Includes correct and incorrect usage examples

#### 003-impact-assessment (BL-076)

**Goal:** Create IMPACT_ASSESSMENT.md with 4 project-specific design-time checks.

**Scope:**
- New `docs/auto-dev/IMPACT_ASSESSMENT.md` with structured check sections
- Each check: name, what to look for, why it matters, concrete example from project history
- Four checks per BL-076 acceptance criteria:
  1. **Async safety:** Flag subprocess.run/call/check_output or time.sleep in files with async def
  2. **Settings documentation:** If Settings fields change, verify .env.example is updated
  3. **Cross-version wiring:** When features depend on prior-version behavior, list assumptions
  4. **GUI input mechanisms:** For GUI features accepting input, verify appropriate mechanisms specified

**Acceptance Criteria:**
1. `docs/auto-dev/IMPACT_ASSESSMENT.md` exists
2. Contains async safety check with grep patterns and ffprobe example
3. Contains settings documentation check with .env.example reference
4. Contains cross-version wiring check with progress bar example
5. Contains GUI input mechanism check with scan path example
6. Each check includes what to look for, why it matters, and a concrete project-history example
7. **End-to-end AC:** Running the auto-dev Task 003 impact assessment on a version that adds a Settings field triggers the settings documentation check

---

## Execution Order

### Theme-Level

Themes 1 and 2 have **no inter-theme dependencies** and can execute in parallel.

**Recommended order:** Theme 1 first, then Theme 2.

**Rationale:** Theme 1 contains the highest-complexity feature (BL-075, clip CRUD) and the only new backend endpoint (BL-070, directory listing). Executing Theme 1 first surfaces any integration issues early while Theme 2 is entirely documentation/configuration with lower risk.

### Feature-Level

**Theme 1:**
1. `001-browse-directory` — validates the full-stack GUI build pipeline (new endpoint + component)
2. `002-clip-crud-controls` — higher complexity but frontend-only; benefits from pipeline validation in 001

**Theme 2:**
1. `001-env-example` — prerequisite for 003-impact-assessment (assessment checks for .env.example)
2. `002-windows-dev-guidance` — independent, can run anytime
3. `003-impact-assessment` — depends on 001-env-example being complete

### Dependency Graph

```
Theme 1:                    Theme 2:
  001-browse-directory        001-env-example
       |                         |
  002-clip-crud-controls      002-windows-dev-guidance (independent)
                                 |
                              003-impact-assessment
```

---

## Research Sources Adopted

| Decision | Source | Evidence Path |
|----------|--------|---------------|
| Backend-assisted directory listing over showDirectoryPicker() | Browser API research | `004-research/external-research.md` §BL-070 |
| Flat directory listing (one level) with upgrade path | LRN-029 | `002-backlog/learnings-summary.md` §LRN-029 |
| Independent Zustand store for clipStore | Project pattern + LRN-037 | `004-research/codebase-patterns.md` §Zustand, `002-backlog/learnings-summary.md` §LRN-037 |
| Drop `label` from clip form (not in backend schema) | Schema verification per LRN-016 | `004-research/codebase-patterns.md` §Pydantic Models |
| Reuse allowed_scan_roots security pattern | Existing codebase pattern | `004-research/codebase-patterns.md` §BL-070 |
| Settings has 11 fields (not 9) | Settings class audit | `004-research/codebase-patterns.md` §BL-071 |
| Impact assessment format: check name + what/why/example | Auto-dev framework expectation | `004-research/external-research.md` §BL-076 |
| AGENTS.md insertion point after Commands | Codebase review | `004-research/codebase-patterns.md` §BL-019 |

---

## Handler Concurrency Decisions

### New Handler: `GET /api/v1/filesystem/directories`

- **I/O Profile:** Filesystem `os.scandir()` call to list directory contents (~5-50ms depending on directory size)
- **Event Loop Blocking:** Possible for large directories (>1000 entries), but typically <100ms. Use `run_in_executor` defensively since I/O time depends on filesystem and directory size.
- **Concurrent Callers:** Yes — multiple browser tabs or rapid navigation clicks could issue concurrent requests
- **Decision:** async handler with `run_in_executor` for the `os.scandir()` call. The security validation (`allowed_scan_roots` check) is CPU-only and can run synchronously. This matches the project's existing async pattern established in v010 for ffprobe.

No other new handlers introduced in v011. BL-075 uses existing clip CRUD endpoints.
