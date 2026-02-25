# v012 Learning Extraction

5 new learnings saved, 4 existing learnings reinforced by new evidence. Sources: 5 completion reports, 2 theme retrospectives, 1 version retrospective, session health findings, session analytics (failed_sessions, errors queries), backlog verification report, and quality gates report.

## New Learnings

| ID | Title | Tags | Source |
|----|-------|------|--------|
| LRN-063 | Zero-Caller Verification Before Code Removal Eliminates Regression Risk | pattern, code-removal, risk-management, refactoring, verification | v012/01-rust-bindings-cleanup retrospective, v012 version retrospective |
| LRN-064 | Group Cleanup Removals by Origin Era for Cohesive PRs | pattern, code-removal, refactoring, planning, pr-strategy | v012/01-rust-bindings-cleanup retrospective, v012 version retrospective |
| LRN-065 | Preserve Internal Implementations When Removing Public API Surface | pattern, architecture, api-design, code-removal, tech-debt | v012/01-rust-bindings-cleanup retrospective, completion reports |
| LRN-066 | Optional Props Pattern Extends UI Components Without Breaking Existing Callers | pattern, gui, react, backward-compatibility, component-design | v012/02-workshop-and-docs-polish/001-transition-gui completion-report |
| LRN-067 | Execution Metadata Requires Same Automation as Code Artifacts | process, failure-mode, automation, execution-tracking, metadata | v012 theme retrospectives (both), v012 version retrospective |

## Reinforced Learnings

| ID | Title | New Evidence |
|----|-------|-------------|
| LRN-061 | Documentation-Only Themes Are Low-Risk High-Value Process Investments | v012 feature 002-api-spec-corrections: 6 doc fixes across 2 files, zero test changes, all quality gates passed. Third consecutive version confirming this pattern. |
| LRN-029 | Conscious Simplicity with Documented Upgrade Paths | v012 CHANGELOG entries with explicit re-add triggers for all 11 removed bindings. Each trigger specifies the exact condition for re-exposure (e.g., "Phase 3 Composition Engine"). |
| LRN-039 | Excessive Context Compaction Signals Need for Task Decomposition | Session health found 27 sessions with 3+ compaction events (up to 16 in one session). Pattern persists across versions; PR-003 remains open. |
| LRN-038 | Sub-Agent File Operations Fail When Read-Before-Write Is Skipped | Session analytics errors query showed continued "File has not been read yet" and cascading "Sibling tool call errored" patterns in recent sessions. |

## Filtered Out

**Total filtered: 12 items**

| Category | Count | Examples |
|----------|-------|---------|
| Too implementation-specific | 3 | Specific file paths deleted, specific mypy error counts, specific test counts |
| Already covered by existing learnings | 3 | Component reuse (covered by LRN-060, LRN-037), tab-based separation (UI pattern already established) |
| Version-specific references | 2 | v012-specific state file path, PR numbers |
| Pre-existing issues not from v012 | 2 | 68 mypy errors (pre-v012), C4 doc regeneration failure |
| Insufficient evidence for causation | 1 | "Staged order built reviewer confidence" — no evidence that different ordering would have failed |
| Session analytics (non-systemic) | 1 | Single session with 12 Bash UNAUTHORIZED denials — isolated incident, not a pattern |

## Session Analytics Findings

Queried `failed_sessions` and `errors` troubleshoot modes for the last 30 days:
- **Failed sessions**: Top errors span v001-v012; no v012-specific systemic failures identified
- **Error patterns**: Dominated by "File does not exist", "Sibling tool call errored" (cascading parallel failures), and "File content exceeds maximum allowed tokens" — all known patterns already captured in LRN-038 or session health PR-002/PR-003
- **No new session-sourced learnings** warranted beyond the reinforcement of LRN-038 and LRN-039 noted above
