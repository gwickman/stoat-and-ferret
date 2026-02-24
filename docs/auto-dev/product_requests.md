# Product Requests

*Last updated: 2026-02-24 10:33*

| ID | Priority | Title | Upvotes | Tags |
|----|----------|-------|---------|------|
| PR-003 | P2 | Session health: Excessive context compaction across 27 sessions | 0 | session-health, retrospective |
| PR-004 | P3 | Replace polling-based job progress with WebSocket/SSE real-time push | 0 | websocket, jobs, progress, ux, deferred-v010 |
| PR-005 | P2 | High Edit tool error rate (11.7%) indicates persistent sub-agent workflow issue | 0 | cross-version-retro, tooling, sub-agents, error-rate |
| PR-006 | P2 | WebFetch tool 58.3% error rate wastes API round-trips across versions | 0 | cross-version-retro, tooling, webfetch, error-rate |
| PR-007 | P1 | C4 architecture documentation drift accumulating across v009-v010 | 0 | cross-version-retro, architecture, documentation, drift |
| PR-009 | P3 | Add pagination to filesystem directory listing endpoint | 0 | api, filesystem, pagination, performance, deferred-v011 |

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

## PR-005: High Edit tool error rate (11.7%) indicates persistent sub-agent workflow issue

**Priority:** P2 | **Status:** open | **Upvotes:** 0
**Project:** stoat-and-ferret
**Tags:** cross-version-retro, tooling, sub-agents, error-rate

Session analytics across v006-v010 show the Edit tool has an 11.7% error rate (126 errors out of 1,074 calls). This is the second-highest error rate among core file operation tools (after WebFetch at 58.3%). LRN-038 (v007) documented that sub-agents frequently fail with "file not read" errors when attempting Write/Edit without prior Read calls. Despite this learning being captured, the Edit error rate remains elevated, suggesting the learning has not been effectively applied across all sub-agent prompt templates.

**Evidence:**
- Edit tool: 1,074 calls, 126 errors (11.7%)
- Write tool: 1,468 calls, 15 errors (1.0%) — demonstrates the gap is Edit-specific
- LRN-038 captured in v007, but errors persist through v008-v010
- Pattern is consistent with "file not read" failures across multiple sub-agent sessions

**Suggested action:** Audit sub-agent prompt templates to ensure all Edit operations are preceded by Read calls. Consider adding a pre-check validation or prompt pattern that enforces read-before-edit ordering.

## PR-006: WebFetch tool 58.3% error rate wastes API round-trips across versions

**Priority:** P2 | **Status:** open | **Upvotes:** 0
**Project:** stoat-and-ferret
**Tags:** cross-version-retro, tooling, webfetch, error-rate

Session analytics across v006-v010 show WebFetch has a 58.3% error rate (28 errors out of 48 calls). This is by far the highest error rate of any tool. PR-001 (completed) investigated orphaned WebFetch calls specifically, but the error rate itself persists. Each failed WebFetch call wastes an API round-trip and contributes to context consumption.

**Evidence:**
- WebFetch: 48 calls, 28 errors (58.3%) across the v006-v010 period
- PR-001 (completed) noted WebFetch has no timeout and agents fetch URLs that won't return
- LRN-038 (v007) and PR-002 addressed related orphaned call patterns
- deepwiki ask_question also shows 21.4% error rate (6 of 28 calls), suggesting external API reliability issues compound the problem

**Suggested action:** Add guardrails to sub-agent prompts discouraging WebFetch for auth-walled or unreliable URLs. Consider implementing a URL allowlist or pre-check pattern to avoid known-failing domains.

## PR-007: C4 architecture documentation drift accumulating across v009-v010

**Priority:** P1 | **Status:** open | **Upvotes:** 0
**Project:** stoat-and-ferret
**Tags:** cross-version-retro, architecture, documentation, drift

C4 architecture documentation has been falling behind implementation across v009 and v010, accumulating 16 drift items in BL-069. Despite LRN-030 (v006) establishing that architecture documentation should be an explicit feature deliverable, and v006 demonstrating this successfully with a dedicated documentation feature, v009 and v010 did not include architecture documentation features. The drift is growing version-over-version.

**Evidence:**
- v006: C4 docs updated within the version as a dedicated feature (LRN-030)
- v007: C4 docs regenerated in delta mode post-version, no drift
- v008: C4 docs regenerated in delta mode, no drift
- v009: 5 C4 drift items identified, BL-069 created
- v010: 11 additional drift items, BL-069 now at 16 total items
- LRN-030 explicitly recommends a documentation feature per theme — pattern abandoned after v007

**Suggested action:** Re-establish the dedicated architecture documentation feature pattern from v006/v007. BL-069 should be scheduled as a high-priority item in the next version before drift compounds further.

## PR-009: Add pagination to filesystem directory listing endpoint

**Priority:** P3 | **Status:** open | **Upvotes:** 0
**Project:** stoat-and-ferret
**Tags:** api, filesystem, pagination, performance, deferred-v011

The `GET /api/v1/filesystem/directories` endpoint (added in v011 feature 001-browse-directory) returns all subdirectories without any limit. For directories containing hundreds or thousands of subdirectories, this could cause slow response times and large payloads. The handoff-to-next.md for this feature explicitly noted: "No limit on number of entries returned; future features may want to add pagination for very large directories." Adding a `limit` and `offset` parameter (consistent with other paginated endpoints in the API) would prevent performance degradation when browsing directories with many entries.
