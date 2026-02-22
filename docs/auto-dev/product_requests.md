# Product Requests

*Last updated: 2026-02-22 17:43*

| ID | Priority | Title | Upvotes | Tags |
|----|----------|-------|---------|------|
| PR-003 | P2 | Session health: Excessive context compaction across 27 sessions | 0 | session-health, retrospective |

## PR-003: Session health: Excessive context compaction across 27 sessions

**Priority:** P2 | **Status:** open | **Upvotes:** 0
**Project:** stoat-and-ferret
**Tags:** session-health, retrospective

27 sessions triggered 3+ context compaction events, with the worst hitting 16 compactions in a single session. Top 5 sessions: 16, 12, 12, 10, 10 compaction events. This indicates sessions routinely exhausting their context windows, risking loss of implementation context and partial work. Possible causes include large codebase reads filling context, verbose tool results, or sessions that run too long without natural boundaries. Remediation options: (1) investigate top-compacting sessions to identify what fills context (2) consider prompt patterns that reduce context consumption (3) evaluate whether task decomposition into smaller sessions would help (4) explore pre-compaction checkpointing to preserve critical state.
