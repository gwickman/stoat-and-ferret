# Learning Extraction - v010 Retrospective

7 new learnings saved (LRN-053 through LRN-059), 2 existing learnings reinforced. Sources: 5 completion reports, 2 theme retrospectives, 1 version retrospective, session health findings (Task 004b), and session analytics data.

## New Learnings

| ID | Title | Tags | Source |
|----|-------|------|--------|
| LRN-053 | Layered Defense-in-Depth for Critical Bug Fixes | process, bug-fixes, defense-in-depth, static-analysis, testing, decision-framework | v010/01-async-pipeline-fix retrospective, v010 version retrospective |
| LRN-054 | Use new_callable=AsyncMock for Cleaner Async Test Mocking | testing, async, mocking, pytest, pattern | v010/01-async-pipeline-fix/001-fix-blocking-ffprobe completion-report |
| LRN-055 | asyncio.to_thread() Bridges Legacy Sync Code in Async Contexts | pattern, async, asyncio, migration, subprocess | v010/01-async-pipeline-fix/002-async-blocking-ci-gate completion-report |
| LRN-056 | Use Production Implementations in Integration Tests for Async Concurrency | testing, async, integration-tests, concurrency, test-doubles | v010/01-async-pipeline-fix/003-event-loop-responsiveness-test completion-report |
| LRN-057 | Cooperative Cancellation via asyncio.Event with Checkpoint Pattern | pattern, async, cancellation, asyncio, api-design | v010/02-job-controls/002-job-cancellation completion-report |
| LRN-058 | Payload Injection Extends Handler Interfaces Without Signature Changes | pattern, backward-compatibility, api-design, dependency-injection, job-queue | v010/02-job-controls/001-progress-reporting completion-report |
| LRN-059 | Pre-Collect Items When Progress Reporting Needs a Known Total | pattern, progress-reporting, ux, iteration, api-design | v010/02-job-controls/001-progress-reporting completion-report |

## Reinforced Learnings

| ID | Title | New Evidence |
|----|-------|-------------|
| LRN-042 | Group Features by Modification Point for Theme Cohesion | v010 Theme 02 (job-controls) had both progress and cancellation features touching the same stack layers (queue -> scan handler -> API -> frontend), confirming that shared-layer grouping minimizes merge conflicts and keeps changes cohesive. |
| LRN-039 | Excessive Context Compaction Signals Need for Task Decomposition | v010 session health (Task 004b) found 27 sessions with 3+ context compactions (max 16), reinforcing that this remains a systemic pattern requiring decomposition strategies. |

## Filtered Out

**11 items filtered** across these categories:

| Category | Count | Examples |
|----------|-------|---------|
| Already captured (MEMORY.md or existing LRN) | 3 | Python 3.10 asyncio.TimeoutError compat (MEMORY.md), Protocol-first design (overlaps LRN-041), Theme dependency ordering (covered by LRN-019) |
| Too implementation-specific | 2 | Module name collision in test directories, HTTP 200/404/409 status codes for state transitions |
| Generic observation, not actionable insight | 2 | Full-stack feature delivery validated, Optional kwargs backward compatibility |
| Insufficient evidence (single session) | 3 | Authorization retry waste (1 session), Sub-agent failure cascade (1 instance), Quality gate runners trying nonexistent dirs |
| Infrastructure issue, not transferable | 1 | MCP server connectivity failures |
