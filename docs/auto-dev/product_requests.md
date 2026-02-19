# Product Requests

*Last updated: 2026-02-19 23:09*

| ID | Priority | Title | Upvotes | Tags |
|----|----------|-------|---------|------|
| PR-001 | P1 | Session health: Orphaned WebFetch calls across 14 instances | 0 | session-health, retrospective |
| PR-002 | P2 | Session health: 34 orphaned non-WebFetch tool calls detected | 0 | session-health, retrospective |

## PR-001: Session health: Orphaned WebFetch calls across 14 instances

**Priority:** P1 | **Status:** open | **Upvotes:** 0
**Project:** stoat-and-ferret
**Tags:** session-health, retrospective

14 unique orphaned WebFetch tool_use calls found across 11 sessions in the past 7 days. These HTTP requests were issued but never returned results, wasting execution time and blocking parallel tool completion. Related to existing BL-054 (WebFetch safety rules). The current lack of effective WebFetch timeout means any hung HTTP request blocks the entire session until manual termination. Adding timeout enforcement would eliminate this class of waste and improve session reliability.

## PR-002: Session health: 34 orphaned non-WebFetch tool calls detected

**Priority:** P2 | **Status:** open | **Upvotes:** 0
**Project:** stoat-and-ferret
**Tags:** session-health, retrospective

34 unique orphaned tool calls (tool_use without tool_result) found across 7 tool types: Bash (11), Task (7), TaskOutput (7), Read (6), Edit (1), Grep (1), Write (1). Orphaned Read/Edit/Write calls indicate abnormal session termination where work may have been lost. Adding graceful shutdown handling that records partial results for in-flight tool calls would improve debugging and reduce repeated work after interrupted sessions.
