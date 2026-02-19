# Session Health Check - v007 Retrospective

5 detection patterns checked against CLI session analytics for `stoat-and-ferret`. Found 2 HIGH severity findings and 3 MEDIUM severity findings. No patterns returned clean. The HIGH findings involve orphaned WebFetch calls (14 unique instances) and orphaned non-WebFetch tool calls (34 unique instances), both indicating tool executions that never received results.

## Detection Results

| # | Pattern | Severity | Threshold | Matches |
|---|---------|----------|-----------|---------|
| 1 | Hung WebFetch Calls | HIGH | Any orphaned WebFetch with has_result=FALSE | **14 unique calls across 11 sessions** |
| 2 | Tool Authorization Retry Waste | MEDIUM | Same tool denied 3+ times in one session | **1 session (Bash denied 12 times)** |
| 3 | Orphaned Tool Calls (Non-WebFetch) | HIGH | Any tool_use without tool_result | **34 unique calls across 7 tool types** |
| 4 | Excessive Context Compaction | MEDIUM | 3+ compaction events per session | **24 sessions (max: 16 compactions)** |
| 5 | Sub-Agent Failure Cascades | MEDIUM | Sub-agents >30min with errors + orphans | **1 sub-agent (53min, 56 errors)** |

## HIGH Findings

### Pattern 1: Hung WebFetch Calls

14 unique orphaned WebFetch calls across 11 sessions. Each represents an HTTP request that was issued but never returned a result. URLs span GitHub, FFmpeg docs, Claude platform docs, and third-party sites.

**Notable instances:**
- `47054390` (Jan 26): 1 WebFetch to `github.com/Jij-Inc/pyo3-stub-gen` (9 duplicate DB rows)
- `792eb162` (Feb 18): 1 WebFetch to `ayosec.github.io/ffmpeg-filters-docs` (4 duplicate DB rows)
- `agent-ab601f1` (Feb 9): 1 WebFetch to `github.com/MonoGame/MonoGame/issues/8120` (5 duplicate DB rows)
- `agent-a8410c2` (Feb 13): 2 WebFetch calls to FFmpeg example sites

**Related existing item:** BL-054 (Add WebFetch safety rules to AGENTS.md)

### Pattern 3: Orphaned Tool Calls (Non-WebFetch)

34 unique orphaned tool calls across 7 tool types:

| Tool | Unique Orphaned | Total Rows (with duplicates) |
|------|----------------|------------------------------|
| Bash | 11 | 22 |
| Task | 7 | 17 |
| TaskOutput | 7 | 33 |
| Read | 6 | 15 |
| Edit | 1 | 4 |
| Grep | 1 | 5 |
| Write | 1 | 1 |

Many orphaned Bash calls are `sleep` commands used for polling waits, which are expected when sessions are terminated. However, orphaned Read/Edit/Write/Grep calls (9 total) indicate unexpected session termination mid-operation.

## MEDIUM Findings

### Pattern 2: Tool Authorization Retry Waste

1 session `5bf50e64` had the Bash tool denied 12 times (UNAUTHORIZED). This indicates the agent repeatedly attempted to run Bash commands that were blocked by permission settings, wasting 12 API round-trips without adapting its approach.

### Pattern 4: Excessive Context Compaction

24 sessions hit 3+ compaction events. Top 5:

| Session | Compaction Count |
|---------|-----------------|
| `f9efa171` | 16 |
| `aaefbad2` | 12 |
| `247375f3` | 12 |
| `b3acc3e9` | 10 |
| `9b6aed8e` | 10 |

This is widespread (24 of ~50 sessions) and suggests many sessions exhaust their context window repeatedly. While individual sessions with 3 compactions may be acceptable for long tasks, sessions hitting 10-16 compactions indicate significant context churn.

### Pattern 5: Sub-Agent Failure Cascades

1 sub-agent `agent-a55770f` ran for 53 minutes with 56 errors and 0 orphaned tools. This was a Yocova metadata comparison task (Feb 3). Since only errors were present (no orphaned tools), this is classified MEDIUM per the pattern criteria. The high error count suggests the sub-agent was repeatedly failing at file operations.

## Product Requests Created

| ID | Title | Priority |
|----|-------|----------|
| PR-001 | Session health: Orphaned WebFetch calls across 14 instances | P1 |
| PR-002 | Session health: 34 orphaned non-WebFetch tool calls detected | P2 |

## Data Availability Notes

- Session data queried with default 7-day window (since ~Feb 12, 2026)
- 50 sessions returned (pagination limit) covering both main sessions and sub-agents
- Some sessions in the data window belong to other project work (e.g., Yocova analysis) that shares the same project folder scope
- Duplicate rows in tool_calls table are present (same tool_use_id appearing multiple times), likely an ingestion artifact; unique counts are used for all finding totals
- The `orphaned_tools` troubleshoot query type referenced in the task prompt does not exist in the current schema; SQL mode was used for all orphaned tool detection
