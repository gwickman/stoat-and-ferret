# Refined Logical Design: v011

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

**Goal:** Deliver the missing GUI interaction layer for media scanning and clip management.

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
- New backend endpoint: `GET /api/v1/filesystem/directories?path={parent_path}` returning subdirectories
- **Security:** Import and call `validate_scan_path()` from `src/stoat_ferret/api/services/scan.py` — same function used by scan endpoint. Uses `Path.resolve()` for normalization (not `os.path.realpath()`). See risk-assessment.md §path-traversal.
- New `DirectoryBrowser.tsx` component rendering a flat directory list (one level at a time)
- Browse button in `ScanModal.tsx` opens the browser; selecting a directory populates the path input
- Manual path typing remains as fallback
- **Initial browse path:** When `allowed_scan_roots` is non-empty, start at the first root. When empty (all paths allowed), start at a platform-appropriate default (e.g., user home). See risk-assessment.md §empty-allowlist.

**Acceptance Criteria:** (unchanged from Task 005 — no design changes needed)
1. ScanModal includes a Browse button next to the path input field
2. Browse button opens a directory browser showing folders from the server filesystem
3. Directory browser respects `allowed_scan_roots` — paths outside allowed roots are rejected
4. Selecting a folder populates the path input with the chosen path
5. Users can still manually type a path as an alternative
6. End-to-end: ScanModal → Browse → navigate → select → path in input → scan succeeds

**Design decisions:**
- Backend-assisted directory listing over `showDirectoryPicker()` — Firefox/Safari lack support
- Flat listing per LRN-029 (Conscious Simplicity)
- Reuse `validate_scan_path()` directly — no new security code needed
- `run_in_executor` for `os.scandir()` — matches async pattern from v010 ffprobe

#### 002-clip-crud-controls (BL-075)

**Goal:** Wire frontend clip management to existing backend CRUD endpoints.

**Scope:**
- New `clipStore.ts` Zustand store following independent-store pattern (per LRN-037)
- New `ClipFormModal.tsx` for Add/Edit with fields: `source_video_id` (dropdown), `in_point`, `out_point`, `timeline_position`
- **Source video selection:** Simple `<select>` dropdown populated from `useVideos` hook (`GET /api/v1/videos`). Matches existing dropdown patterns in SortControls.tsx, EffectCatalog.tsx. See risk-assessment.md §video-selection.
- Reuse existing `DeleteConfirmation.tsx` pattern for clip deletion
- Add/Edit/Delete buttons in `ProjectDetails.tsx` clip table
- API client functions for POST/PATCH/DELETE clip endpoints
- Error display from backend validation (Rust core validates time ranges)
- **Race condition mitigation:** Sequential await pattern with `isLoading` guard disabling buttons during operations. Matches `effectStackStore` convention. See risk-assessment.md §race-condition.

**Acceptance Criteria:** (updated — `label` removed per investigation)
1. ProjectDetails page includes an Add Clip button that opens a form to create a new clip
2. Each clip row has Edit and Delete action buttons
3. Edit opens a modal pre-populated with current clip properties (in/out points, timeline_position)
4. Delete prompts for confirmation then removes the clip via DELETE endpoint
5. Add/Edit forms validate input and display errors from the backend (e.g., invalid time ranges)
6. Clip list refreshes after any add/update/delete operation
7. End-to-end: Add clip → Edit in_point → Delete → each reflected in clip table

**Note on `label` field:** BL-075 AC3 references "label" but no `label` field exists in any clip schema or data model (confirmed by investigation — see risk-assessment.md §label). The form uses `timeline_position` instead. If label support is desired, it requires a backend schema change first.

---

## Theme 2: 02-developer-onboarding

**Goal:** Reduce onboarding friction and establish project-specific design-time quality checks.

**Backlog Items:** BL-071, BL-019, BL-076

### Features

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-env-example | Create .env.example with all Settings fields documented | BL-071 | None |
| 2 | 002-windows-dev-guidance | Add Windows Git Bash /dev/null guidance to AGENTS.md | BL-019 | None |
| 3 | 003-impact-assessment | Create IMPACT_ASSESSMENT.md with 4 project-specific design checks | BL-076 | 001-env-example |

### Feature Details

(Unchanged from Task 005 — no investigation findings required design changes for Theme 2)

#### 001-env-example (BL-071)
See Task 005 logical-design.md for full details. No changes.

#### 002-windows-dev-guidance (BL-019)
See Task 005 logical-design.md for full details. No changes.

#### 003-impact-assessment (BL-076)
See Task 005 logical-design.md for full details. Format confirmed appropriate by investigation (risk-assessment.md §format). No changes.

---

## Execution Order

(Unchanged from Task 005 — no structural changes needed)

### Theme-Level
Themes 1 and 2 have **no inter-theme dependencies**. Recommended: Theme 1 first (higher complexity, surfaces integration issues early), then Theme 2.

### Feature-Level
**Theme 1:** 001-browse-directory → 002-clip-crud-controls
**Theme 2:** 001-env-example → 002-windows-dev-guidance → 003-impact-assessment

---

## Handler Concurrency Decisions

### New Handler: `GET /api/v1/filesystem/directories`
- async handler with `run_in_executor` for `os.scandir()` call
- Security validation via `validate_scan_path()` runs synchronously (CPU-only)
- Matches v010 async pattern for ffprobe

---

## Changes from Task 005

| Change | Reason | Impact |
|--------|--------|--------|
| Security uses `Path.resolve()` not `os.path.realpath()` | Investigation found codebase uses pathlib consistently | Minor — implementation detail only |
| Added initial browse path guidance | Investigation revealed empty allowlist = all paths; need sensible default | Minor — UX refinement for 001-browse-directory |
| Confirmed `<select>` dropdown for video selection | Investigation found 3 existing patterns + useVideos hook | Resolves scope creep risk for 002-clip-crud-controls |
| Race condition accepted with isLoading mitigation | Investigation found no stores use AbortController; pattern is established | No design change — documents accepted approach |
| Confirmed no `label` field in any data model | Investigation searched all layers conclusively | Validates Task 005's decision to drop `label` |
