# Learning Extraction - v011 Retrospective

3 new learnings saved (LRN-060, LRN-061, LRN-062), 2 existing learnings reinforced. v011 was a clean version with zero iteration cycles, so learnings focus on process patterns rather than failure modes.

## New Learnings

| ID | Title | Tags | Source |
|----|-------|------|--------|
| LRN-060 | Wire Frontend to Existing Backend Endpoints Before Creating New Ones | pattern, frontend, api-design, planning, efficiency | v011/01-scan-and-clip-ux retrospective, v011 version retrospective |
| LRN-061 | Documentation-Only Themes Are Low-Risk High-Value Process Investments | process, documentation, planning, risk-management, efficiency | v011/02-developer-onboarding retrospective, v011 version retrospective |
| LRN-062 | Design-Time Impact Checks Shift Defect Detection Left from Implementation to Design | process, design, quality, failure-mode, institutional-knowledge | v011/02-developer-onboarding/003-impact-assessment completion-report, v011 version retrospective |

## Reinforced Learnings

| ID | Title | New Evidence |
|----|-------|-------------|
| LRN-031 | Detailed Design Specifications Correlate with First-Iteration Success | v011 achieved 0 iteration cycles across all 5 features with 34/34 acceptance criteria passing, reinforcing the correlation between well-scoped requirements and first-pass completion |
| LRN-038 | Sub-Agent File Operations Fail When Read-Before-Write Is Skipped | Session analytics for v011 period show continued "File does not exist" and "Sibling tool call errored" cascades from agents attempting to read nonexistent files |

## Filtered Out

**Total filtered: 8 items**

| Category | Count | Examples |
|----------|-------|---------|
| Overlaps with existing learnings | 3 | "Established frontend patterns scale" overlaps LRN-024/LRN-037; "Zustand per-entity store pattern" overlaps LRN-024 |
| Too implementation-specific | 2 | DirectoryBrowser component reuse details; specific file paths and endpoints |
| Version-specific observations | 1 | v011 test suite count (968 passed) — not transferable |
| Platform/tooling observations | 2 | Sibling tool call error cascade behavior; VIRTUAL_ENV mismatch warnings — Claude Code platform issues, not project-actionable |

## Data Sources Reviewed

- 5 completion reports (01-scan-and-clip-ux: 001, 002; 02-developer-onboarding: 001, 002, 003)
- 2 theme retrospectives (01-scan-and-clip-ux, 02-developer-onboarding)
- 1 version retrospective (v011)
- 1 handoff document (01-scan-and-clip-ux/001-browse-directory)
- Session health findings (Task 004b): 5 detection patterns analyzed
- Session analytics: failed_sessions and errors queries (30-day window)
- 59 existing learnings reviewed for reinforcement
