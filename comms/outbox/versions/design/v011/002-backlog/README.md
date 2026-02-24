# Task 002: Backlog Analysis and Retrospective Review

v011 covers 5 mandatory backlog items across 2 themes (scan-and-clip-ux, developer-onboarding), targeting GUI interaction gaps and process improvements. The previous version (v010) fixed a P0 async blocking bug and added job controls, establishing patterns for layered bug-fix approaches and protocol-first design that inform v011's work.

## Backlog Overview

- **Total items:** 5
- **Priority distribution:** P1 x2 (BL-075, BL-076), P2 x2 (BL-070, BL-071), P3 x1 (BL-019)
- **Size distribution:** Large x2 (BL-075, BL-076), Medium x3 (BL-019, BL-070, BL-071)
- **All items status:** open, none previously attempted

## Previous Version

- **Version:** v010 (most recent completed)
- **Completed:** 2026-02-24
- **Themes:** 2/2 (01-async-pipeline-fix, 02-job-controls)
- **Features:** 5/5
- **Retrospective locations:**
  - `docs/versions/v010/01-async-pipeline-fix_retrospective.md`
  - `docs/versions/v010/02-job-controls_retrospective.md`
  - `docs/versions/v010/VERSION_SUMMARY.md`

## Key Learnings Applicable to v011

1. **Detailed design specs correlate with first-iteration success** (LRN-031) — v011's GUI features (BL-070, BL-075) need precise UI specifications to avoid rework
2. **Schema-driven architecture enables backend-to-frontend consistency** (LRN-032) — BL-075 (clip CRUD) should leverage existing backend schemas for form generation
3. **Feature composition through independent store interfaces** (LRN-037) — new GUI components should follow the Zustand independent-store pattern established in v007
4. **Validate acceptance criteria against codebase during design** (LRN-016) — verify that BL-075's assumed API endpoints actually exist and match expected signatures
5. **Protocol-first design** (v010 retrospective) — any protocol changes for new features should update Protocol, production impl, and test doubles together

## Tech Debt

- **20 pre-existing test skips** — tests requiring ffprobe/ffmpeg binaries, carried through v010
- **InMemoryJobQueue growing no-op surface** — test double diverging from production queue
- **Health check uses subprocess.run under asyncio.to_thread** — inconsistent with async pattern used elsewhere
- **C4 documentation 2 versions behind** — last updated at v008

## Missing Items

None. All 5 backlog items (BL-019, BL-070, BL-071, BL-075, BL-076) were successfully fetched.

## Quality Refinements Applied

- **BL-019**: Added 4 testable acceptance criteria (had none) and expanded description with problem context. Use case remains formulaic (field not updatable via API).
