# Product Requests

*Last updated: 2026-02-24 00:14*

| ID | Priority | Title | Upvotes | Tags |
|----|----------|-------|---------|------|
| PR-003 | P2 | Session health: Excessive context compaction across 27 sessions | 0 | session-health, retrospective |
| PR-004 | P3 | Replace polling-based job progress with WebSocket/SSE real-time push | 0 | websocket, jobs, progress, ux, deferred-v010 |

## PR-003: Session health: Excessive context compaction across 27 sessions

**Priority:** P2 | **Status:** open | **Upvotes:** 0
**Project:** stoat-and-ferret
**Tags:** session-health, retrospective

27 sessions triggered 3+ context compaction events, with the worst hitting 16 compactions in a single session. Top 5 sessions: 16, 12, 12, 10, 10 compaction events. This indicates sessions routinely exhausting their context windows, risking loss of implementation context and partial work. Possible causes include large codebase reads filling context, verbose tool results, or sessions that run too long without natural boundaries. Remediation options: (1) investigate top-compacting sessions to identify what fills context (2) consider prompt patterns that reduce context consumption (3) evaluate whether task decomposition into smaller sessions would help (4) explore pre-compaction checkpointing to preserve critical state.

## PR-004: Replace polling-based job progress with WebSocket/SSE real-time push

**Priority:** P3 | **Status:** open | **Upvotes:** 0
**Project:** stoat-and-ferret
**Tags:** websocket, jobs, progress, ux, deferred-v010

Job progress is currently poll-based via `GET /api/v1/jobs/{id}`. The frontend ScanModal polls at a fixed interval to update the progress bar. WebSocket infrastructure already exists (BL-029, BL-065 completed) but is not wired for job progress events. Pushing progress updates over the existing WebSocket connection would eliminate polling overhead and provide smoother real-time progress feedback. Identified as deferred work in v010 Theme 02 (job-controls) completion reports for both 001-progress-reporting and 002-job-cancellation.
