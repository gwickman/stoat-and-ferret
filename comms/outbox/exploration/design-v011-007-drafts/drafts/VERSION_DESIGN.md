# Version Design: v011

## Description

GUI Usability & Developer Experience — Close the biggest GUI interaction gaps and improve onboarding/process documentation. Adds clip CRUD controls to the GUI (wiring frontend to existing backend endpoints), replaces text-only scan path input with a backend-assisted directory browser, creates developer onboarding artifacts (.env.example, Windows guidance), and establishes project-specific design-time checks via IMPACT_ASSESSMENT.md.

**Depends on:** v010 deployed (completed 2026-02-23)

## Design Artifacts

Full design analysis available at: `comms/outbox/versions/design/v011/`

- `001-environment/` — version context, environment checks
- `002-backlog/` — backlog details, retrospective insights, learnings summary
- `004-research/` — codebase patterns, external research, evidence log, impact analysis
- `005-logical-design/` — logical design, test strategy, risks and unknowns
- `006-critical-thinking/` — refined logical design, risk assessment, investigation log

## Constraints and Assumptions

**Constraints:**
- v010 must be deployed (prerequisite for scan UX improvements)
- No inter-theme dependencies — themes can execute in parallel
- Backend clip CRUD endpoints already exist — BL-075 is frontend-only
- `showDirectoryPicker()` not viable (Firefox/Safari lack support) — use backend-assisted directory listing
- No `label` field in clip schema — BL-075 AC3 reference is an AC drafting error

**Assumptions:**
- Empty `allowed_scan_roots` means all directories permitted (confirmed: LRN-017, test coverage)
- Simple `<select>` dropdown sufficient for source video selection in clip form
- Sequential await with `isLoading` guard sufficient for race condition mitigation
- IMPACT_ASSESSMENT.md markdown format consumable by auto-dev Task 003 agent

See `001-environment/version-context.md` for full context.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Backend-assisted directory listing over `showDirectoryPicker()` | Firefox/Safari lack support — see `004-research/external-research.md` |
| Flat directory listing (one level at a time) | LRN-029 Conscious Simplicity — upgrade to native picker when browser support improves |
| Reuse `validate_scan_path()` for directory listing security | Existing function uses `Path.resolve()` + `relative_to()` — robust against traversal — see `006-critical-thinking/risk-assessment.md` |
| Independent Zustand store for clipStore | Matches project's 7 existing independent stores — LRN-037 |
| Drop `label` from clip form | No label field exists in any clip data model — see `006-critical-thinking/investigation-log.md` |
| `run_in_executor` for `os.scandir()` | Matches v010 async pattern for ffprobe — see `005-logical-design/logical-design.md` |

See `006-critical-thinking/risk-assessment.md` for full rationale.

## Theme Overview

| # | Theme | Features | Backlog Items | Goal |
|---|-------|----------|---------------|------|
| 1 | scan-and-clip-ux | 2 | BL-070, BL-075 | Deliver the missing GUI interaction layer for media scanning and clip management |
| 2 | developer-onboarding | 3 | BL-019, BL-071, BL-076 | Reduce onboarding friction and establish project-specific design-time quality checks |

See `THEME_INDEX.md` for details.
