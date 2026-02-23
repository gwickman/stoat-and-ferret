# Version Context — v010 Async Pipeline & Job Controls

## Version Goals

**Goal:** Fix the P0 async blocking bug, add guardrails to prevent recurrence, then build user-facing job progress and cancellation on top of the working pipeline.

**Roadmap reference:** RCA + Phase 1 gaps

## Themes and Features

### Theme 1: async-pipeline-fix

| Feature | Description | Backlog | Priority |
|---------|-------------|---------|----------|
| 001-fix-blocking-ffprobe | Fix blocking `subprocess.run()` in ffprobe | BL-072 | P0 |
| 002-async-blocking-ci-gate | Add CI lint rule flagging blocking calls inside `async def` | BL-077 | P2 |
| 003-event-loop-responsiveness-test | Integration test verifying event loop stays responsive during scan | BL-078 | P2 |

### Theme 2: job-controls

| Feature | Description | Backlog | Priority |
|---------|-------------|---------|----------|
| 001-progress-reporting | Add progress % and status updates to job queue, wire through WebSocket | BL-073 | P1 |
| 002-job-cancellation | Add cancel endpoint and cooperative cancellation to scan and job queue | BL-074 | P1 |

## Backlog Items Referenced

BL-072, BL-073, BL-074, BL-077, BL-078 (5 items total)

*Full backlog item details to be gathered in Task 002.*

## Dependencies

- **Inter-theme:** Theme 2 depends on Theme 1 — progress/cancellation are meaningless if the event loop is frozen.
- **External:** v010 is the next version after v009 (completed 2026-02-22). No outstanding blockers.
- **Downstream:** v011 depends on v010 deployed (progress reporting needed for scan UX improvements).

## Constraints and Assumptions

1. BL-072 touches the async subprocess layer affecting all FFmpeg/ffprobe interactions — high-risk, high-impact change.
2. BL-078 validates the BL-072 fix; BL-077 prevents regression via CI enforcement.
3. The existing async job queue (`stoat_ferret.jobs`) and WebSocket infrastructure (`stoat_ferret.api.websocket`) provide the foundation for progress reporting and cancellation.

## Deferred Items to Be Aware Of

| Item | Deferred From | Notes |
|------|---------------|-------|
| Phase 3: Composition Engine | v008 (original) | Deferred to post-v010; wiring audit fixes take priority |
| Drop-frame timecode support | M1.2 | Complex; start with non-drop-frame only |
| BL-069 | Excluded from versions | C4 documentation update, deferred |

## Recently Completed (Context)

- **v009** (2026-02-22): Observability & GUI Runtime — ObservableFFmpegExecutor, AuditLogger, file logging, SPA routing, pagination fix, WebSocket broadcasts
- **v008** (2026-02-22): Startup Integrity & CI Stability — database startup, structured logging, orphaned settings wiring, flaky E2E fix
