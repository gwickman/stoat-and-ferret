# Learning Extraction - v008 Retrospective

7 new learnings saved (LRN-040 through LRN-046), 3 existing learnings reinforced with additional evidence. Sources included 4 completion reports, 2 theme retrospectives, 1 version retrospective, session health findings, and session analytics data.

## New Learnings

| ID | Title | Tags | Source |
|----|-------|------|--------|
| LRN-040 | Idempotent Startup Functions for Lifespan Wiring | pattern, startup, idempotency, fastapi, lifespan | T01 retrospective, 001/002 completion reports |
| LRN-041 | Static Type Checking Catches Cross-Module Wiring Errors | pattern, mypy, type-checking, wiring, debugging | 003 completion report, version retrospective |
| LRN-042 | Group Features by Modification Point for Theme Cohesion | process, planning, theme-design, cohesion, efficiency | T01 retrospective, version retrospective |
| LRN-043 | Explicit Assertion Timeouts in CI-Bound E2E Tests | testing, e2e, playwright, ci, reliability, failure-mode | T02 001 completion report, T02 retrospective |
| LRN-044 | Settings Consumer Traceability as a Completeness Check | pattern, configuration, settings, completeness, maintenance | 003 completion report, T01 retrospective |
| LRN-045 | Single-Feature Themes for Precisely-Scoped Bug Fixes | process, planning, theme-design, bug-fixes, scoping | T02 retrospective, version retrospective |
| LRN-046 | Maintenance Versions Succeed with Well-Understood Change Scoping | process, planning, scoping, maintenance, quality | version retrospective |

## Reinforced Learnings

| ID | Title | New Evidence |
|----|-------|--------------|
| LRN-031 | Detailed Design Specifications Correlate with First-Iteration Success | v008 achieved 100% first-iteration success (4/4 features) with well-scoped maintenance changes |
| LRN-033 | Fix CI Reliability Before Dependent Development Cycles | v008 directly addressed the flaky E2E test (BL-055) that blocked v007 CI merges |
| LRN-039 | Excessive Context Compaction Signals Need for Task Decomposition | Session health check found 27 sessions (0.9%) with 3+ compactions, continuing the pattern from v007 |

## Filtered Out

**Total items filtered:** 11

| Category | Count | Examples |
|----------|-------|---------|
| Duplicates (same insight from multiple sources) | 5 | Idempotent patterns mentioned in both completion reports and retrospective; theme cohesion mentioned in both theme and version retrospective |
| Too implementation-specific | 3 | Specific file paths, session IDs, individual test names |
| Already covered by existing learnings | 2 | First-iteration success correlation (LRN-031), CI reliability priority (LRN-033) |
| Session analytics noise | 1 | "Sibling tool call errored" cascade pattern — generic tool behavior, not project-specific |

## Session Analytics Insights

Queried failed sessions and error patterns from the past 30 days:

- **Most common error pattern:** "Sibling tool call errored" cascades from parallel tool calls — one failure causes all siblings to error. Not actionable at the project level.
- **VIRTUAL_ENV mismatch warnings:** Consistent `VIRTUAL_ENV` mismatch warnings from auto-dev-mcp venv conflicting with project venv. Functional but noisy.
- **Coverage fail-under on single files:** Running individual test files triggers `--cov-fail-under=80` failures because coverage is measured on the subset, not the full codebase. Known pytest-cov behavior.
- **No new systemic patterns** beyond what session health (004b) already documented.
