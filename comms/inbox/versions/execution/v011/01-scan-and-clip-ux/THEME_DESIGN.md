# Theme: scan-and-clip-ux

## Goal

Deliver the missing GUI interaction layer for media scanning and clip management. The browse button (BL-070) validates the full-stack GUI pipeline by adding a new backend endpoint and frontend component, while clip CRUD (BL-075) wires the frontend to existing backend endpoints — closing a gap deferred since v005.

## Design Artifacts

See `comms/outbox/versions/design/v011/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | browse-directory | BL-070 | Replace text-only scan path input with a backend-assisted directory browser |
| 002 | clip-crud-controls | BL-075 | Wire frontend clip management to existing backend CRUD endpoints |

## Dependencies

- v010 deployed (completed 2026-02-23) — progress reporting is prerequisite for scan UX
- No inter-feature dependencies within this theme (backend clip endpoints already exist)
- Feature execution order: 001 before 002 (001 validates full-stack pipeline)

## Technical Approach

**001-browse-directory:** New `GET /api/v1/filesystem/directories` endpoint using `os.scandir()` wrapped in `run_in_executor` for async safety. Reuses `validate_scan_path()` from `src/stoat_ferret/api/services/scan.py` for security. New `DirectoryBrowser.tsx` component renders a flat directory list (one level). Browse button added to `ScanModal.tsx`. See `004-research/external-research.md` for browser API evaluation and `004-research/codebase-patterns.md` for endpoint patterns.

**002-clip-crud-controls:** New `clipStore.ts` Zustand store following the independent-store pattern (7 existing stores). New `ClipFormModal.tsx` for Add/Edit with `source_video_id` dropdown (from `useVideos` hook), `in_point`, `out_point`, `timeline_position` fields. Reuses `DeleteConfirmation.tsx` pattern. Add/Edit/Delete buttons in `ProjectDetails.tsx` clip table. See `004-research/codebase-patterns.md` for frontend patterns and Zustand conventions.

## Risks

| Risk | Mitigation |
|------|------------|
| Directory listing path traversal | Reuse `validate_scan_path()` with `Path.resolve()` — see `006-critical-thinking/risk-assessment.md` |
| `label` field mismatch in BL-075 AC | AC drafting error — no label field in data model. Use `timeline_position` instead — see `006-critical-thinking/risk-assessment.md` |
| Source video selection scope creep | Simple `<select>` dropdown using existing patterns and `useVideos` hook — see `006-critical-thinking/risk-assessment.md` |
| Empty `allowed_scan_roots` UX | Empty = all paths allowed (LRN-017). Default browse to first root or user home — see `006-critical-thinking/risk-assessment.md` |
| Clip CRUD refresh race condition | Sequential await with `isLoading` guard — matches `effectStackStore` pattern — see `006-critical-thinking/risk-assessment.md` |