# 005 Logical Design Proposal — v011

Proposed structure for v011 (GUI Usability & Developer Experience): 2 themes containing 5 features total, addressing all 5 backlog items (BL-019, BL-070, BL-071, BL-075, BL-076). Theme 1 delivers scan and clip UX improvements including a new backend directory listing endpoint. Theme 2 creates developer onboarding artifacts and project-specific design-time checks.

## Theme Overview

| # | Theme | Goal | Features | Backlog Items |
|---|-------|------|----------|---------------|
| 1 | 01-scan-and-clip-ux | Wire frontend to backend for directory browsing and clip CRUD | 2 | BL-070, BL-075 |
| 2 | 02-developer-onboarding | Create onboarding artifacts and design-time quality checks | 3 | BL-071, BL-019, BL-076 |

## Key Decisions

- **Backend-assisted directory listing** over `showDirectoryPicker()` — Firefox/Safari lack support. Uses flat listing (one level) per LRN-029 with documented upgrade path.
- **Drop `label` from clip form** — not in backend schema. AC3 references it but `ClipCreate`/`ClipUpdate` have no label field. Backend schema is authoritative.
- **Independent Zustand store** (`clipStore.ts`) for clip state — follows project's established 7-store pattern per LRN-037.
- **Async handler with `run_in_executor`** for the new directory listing endpoint — defensive against large directory I/O.
- **All 5 backlog items mapped** — no deferrals, no descoping.

## Dependencies

- **No inter-theme dependencies.** Themes can execute in parallel.
- **Intra-Theme 1:** 001-browse-directory before 002-clip-crud-controls (validates full-stack pipeline).
- **Intra-Theme 2:** 001-env-example before 003-impact-assessment (assessment references .env.example).
- **Recommended execution:** Theme 1 then Theme 2 (higher complexity first).

## Risks and Unknowns

| Risk | Severity | Summary |
|------|----------|---------|
| `label` field mismatch | medium | AC3 references label, but backend schema has no label field |
| Directory listing path traversal | high | New endpoint exposes filesystem — needs `os.path.realpath()` + allowed_scan_roots |
| Clip add scope creep (video picker) | medium | Add Clip needs source_video_id selection — no existing picker widget |
| Empty `allowed_scan_roots` behavior | medium | Unclear if empty list means "allow all" or "deny all" |
| Clip refresh race condition | low | Rapid mutations could cause stale list state |
| IMPACT_ASSESSMENT.md format | low | No formal schema for auto-dev consumption |
| Theme 2 feature ordering | low | Already mitigated by execution order constraint |

See `risks-and-unknowns.md` for full details. These feed into Task 006 (Critical Thinking).

## Artifacts

- `logical-design.md` — Complete design proposal with themes, features, execution order, research sources
- `test-strategy.md` — Test requirements per feature (5 pytest, 18 Vitest, 6 manual checks)
- `risks-and-unknowns.md` — 7 risks for Task 006 review
