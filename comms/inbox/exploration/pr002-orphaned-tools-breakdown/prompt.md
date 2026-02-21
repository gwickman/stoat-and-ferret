Investigate PR-002: "Session health: 34 orphaned non-WebFetch tool calls detected" — provide a detailed breakdown by version, tool type, and session.

PR-002 reports 34 unique orphaned tool calls (tool_use without tool_result) across 7 tool types: Bash (11), Task (7), TaskOutput (7), Read (6), Edit (1), Grep (1), Write (1). Orphaned Read/Edit/Write calls indicate abnormal session termination where work may have been lost.

## Investigation

Use the `query_cli_sessions` MCP tool to dig into the session analytics database.

1. **Version-by-version breakdown**: Which versions (v001-v007) had orphaned non-WebFetch tool calls? How many per version, broken down by tool type?
2. **Session-level detail**: For each affected session, identify: what theme/feature was being worked on, which tools orphaned, and whether the session terminated abnormally
3. **Tool type analysis**: 
   - Bash (11): Were these long-running commands? What commands were being run?
   - Task/TaskOutput (7 each): Are these paired — i.e., tasks started but output never collected?
   - Read (6): What files were being read when the session died?
   - Edit/Write (1 each): Was work lost? Were these mid-file-modification?
4. **Pattern identification**: Are orphaned calls clustered around specific operations (e.g., CI waits, large file reads, complex git operations)?
5. **Impact**: Estimate whether orphaned Edit/Write calls resulted in lost work or corrupted state
6. **Correlation with WebFetch**: Do sessions with orphaned non-WebFetch calls also have orphaned WebFetch calls (PR-001), suggesting systematic session termination issues rather than tool-specific problems?

Use query_cli_sessions with mode="analytics" or mode="raw" SQL as needed.

## Output Requirements

Create findings in comms/outbox/exploration/pr002-orphaned-tools-breakdown/:

### README.md (required)
First paragraph: Summary of orphaned tool call distribution across versions and tool types.
Then: Key patterns, whether this represents lost work or just noisy session termination, and any systemic causes.

### version-breakdown.md
Per-version table with: version, session count, orphaned calls by tool type, affected themes/features, and identified patterns.

### tool-analysis.md
Per-tool-type analysis: what operations were interrupted, whether work was lost, and any common triggers.

## Guidelines
- Under 200 lines per document
- Include actual session IDs and timestamps where available
- If query_cli_sessions doesn't have the granularity needed, say so explicitly
- Commit when complete

## When Complete
git add comms/outbox/exploration/pr002-orphaned-tools-breakdown/
git commit -m "exploration: pr002-orphaned-tools-breakdown complete"
