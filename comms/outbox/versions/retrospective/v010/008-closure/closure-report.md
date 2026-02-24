# v010 Closure Report

**Date:** 2026-02-24
**Project:** stoat-and-ferret
**Version:** v010

---

## 1. Plan.md Changes

**Action:** Updated `docs/auto-dev/plan.md`

### Diff Summary

**Last Updated date:**
```diff
-> Last Updated: 2026-02-22
+> Last Updated: 2026-02-24
```

**Current Focus section:**
```diff
-**Recently Completed:** v009 (Observability & GUI Runtime)
-**Upcoming:** v010 (Async Pipeline & Job Controls)
+**Recently Completed:** v010 (Async Pipeline & Job Controls)
+**Upcoming:** v011 (GUI Usability & Developer Experience)
```

**Version table — v010 row:**
```diff
-| v010 | RCA + Phase 1 gaps | Async Pipeline & Job Controls: fix blocking ffprobe, CI async gate, progress reporting, job cancellation | 📋 planned |
+| v010 | RCA + Phase 1 gaps | Async Pipeline & Job Controls: fix blocking ffprobe, CI async gate, progress reporting, job cancellation | ✅ complete |
```

**Planned Versions section — removed v010 block:**
```diff
-### v010 — Async Pipeline & Job Controls
-
-**Goal:** Fix the P0 async blocking bug, add guardrails to prevent recurrence, then build user-facing job progress and cancellation on top of the working pipeline.
-
-**Theme 1: async-pipeline-fix**
-- 001-fix-blocking-ffprobe: Fix blocking subprocess.run() in ffprobe [BL-072, P0]
-- 002-async-blocking-ci-gate: Add CI lint rule flagging blocking calls inside async def [BL-077, P2]
-- 003-event-loop-responsiveness-test: Integration test verifying event loop stays responsive during scan [BL-078, P2]
-
-**Theme 2: job-controls**
-- 001-progress-reporting: Add progress percentage and status updates to job queue, wire through WebSocket [BL-073, P1]
-- 002-job-cancellation: Add cancel endpoint and cooperative cancellation to scan and job queue [BL-074, P1]
-
-**Backlog items:** BL-072, BL-073, BL-074, BL-077, BL-078 (5 items)
-**Dependencies:** Theme 2 depends on Theme 1 — progress/cancellation are meaningless if the event loop is frozen.
-**Risk:** BL-072 touches async subprocess layer affecting all FFmpeg/ffprobe interactions. BL-078 validates the fix; BL-077 prevents regression.
```

**Completed Versions section — added v010 entry (before v009):**
```diff
+### v010 - Async Pipeline & Job Controls (2026-02-23)
+- **Themes:** async-pipeline-fix, job-controls
+- **Features:** 5 completed across 2 themes
+- **Backlog Resolved:** BL-072, BL-073, BL-074, BL-077, BL-078
+- **Key Changes:** Async ffprobe with `asyncio.create_subprocess_exec()` replacing blocking `subprocess.run()`, Ruff ASYNC rules (ASYNC210/221/230) as CI gate for blocking-in-async detection, event-loop responsiveness integration test (<2s jitter), job progress reporting with per-file progress via WebSocket, cooperative job cancellation with `cancel_event` and per-file checkpoints saving partial results
+- **Deferred:** None
```

**Change Log table — added entry:**
```diff
+| 2026-02-24 | v010 complete: Async Pipeline & Job Controls delivered (2 themes, 5 features, 5 backlog items completed). Moved v010 from Planned to Completed. Updated Current Focus to v011. |
```

---

## 2. CHANGELOG.md Verification

**Action:** Verified — no changes needed.

**Verification checklist:**
- [x] v010 section exists with date (2026-02-23)
- [x] Section contains categorized entries (Added, Changed, Fixed)
- [x] BL-072 (Fix blocking ffprobe) → "Async FFprobe" under Added + "P0" entry under Fixed
- [x] BL-077 (CI async gate) → "Async Blocking CI Gate" under Added
- [x] BL-078 (Event-loop test) → "Event-Loop Responsiveness Test" under Added
- [x] BL-073 (Progress reporting) → "Job Progress Reporting" under Added
- [x] BL-074 (Job cancellation) → "Cooperative Job Cancellation" under Added
- [x] Changed section covers scan_directory refactor and protocol extensions
- [x] Fixed section documents the P0 async blocking resolution

All 5 backlog items are accurately represented with correct categorization.

---

## 3. README.md Review

**Action:** Reviewed — no changes needed.

The project root README.md contains:
```
# stoat-and-ferret
[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready
```

**Assessment:**
- v010's changes (async pipeline fix, CI async gate, event-loop test, progress reporting, job cancellation) are internal infrastructure improvements
- The project description ("AI-driven video editor with hybrid Python/Rust architecture") remains accurate
- The "[Alpha]" and "not production ready" qualifiers are still appropriate
- No new user-facing capabilities need to be described in the README

---

## 4. Repository Cleanup

**Action:** Verified — repository is clean.

| Check | Result | Details |
|-------|--------|---------|
| Open PRs | 0 | All v010 PRs merged |
| Stale branches | 0 | Only `main` exists locally and remotely |
| Working tree | 1 modified file | `comms/state/explorations/v010-retro-008-closure-1771892210722.json` (MCP state, expected) |
| Branch sync | In sync | `main` is 0 ahead / 0 behind `origin/main` |

No cleanup actions required.
