# Session Health Check - v012 Retrospective

5 detection patterns checked against stoat-and-ferret session analytics. 2 findings at HIGH severity (both covered by existing product requests from prior retrospectives), 3 findings at MEDIUM severity (1 covered by existing PR, 2 new but non-systemic). No new product requests created — all HIGH findings have existing coverage.

## Detection Results

| # | Pattern | Severity | Threshold | Matches | Status |
|---|---------|----------|-----------|---------|--------|
| 1 | Hung WebFetch Calls | HIGH | Any orphaned WebFetch | 1 unique | Covered by PR-001 (completed), PR-006 (open) |
| 2 | Tool Authorization Retry Waste | MEDIUM | Same tool denied 3+ times/session | 1 session (12 denials) | New finding, non-systemic |
| 3 | Orphaned Tool Calls (Non-WebFetch) | HIGH | Any orphaned non-WebFetch tool | 5 unique across 4 sessions | Covered by PR-002 (completed) |
| 4 | Excessive Context Compaction | MEDIUM | 3+ compactions/session | 27 sessions | Covered by PR-003 (open) |
| 5 | Sub-Agent Failure Cascades | MEDIUM | >30min + errors/orphans | 1 sub-agent | New finding, non-systemic |

## HIGH Findings

### Pattern 1: Hung WebFetch Calls

1 orphaned WebFetch call detected in session `792eb162-520c-44c4-b20c-7aa9535bd873` (Feb 18). The call fetched FFmpeg atempo filter documentation from an external site. This is consistent with the root cause identified in PR-001: WebFetch has no built-in timeout and agents fetch URLs that may not return promptly.

**Existing coverage:** PR-001 (completed) investigated and closed this pattern. PR-006 (open) tracks the broader 58.3% WebFetch error rate. auto-dev-mcp BL-536 addresses the global fix.

### Pattern 3: Orphaned Tool Calls (Non-WebFetch)

5 unique orphaned non-WebFetch tool calls across 4 sessions:

| Session | Tool | Input |
|---------|------|-------|
| `82746b32` | Read | manifest.json |
| `agent-a0fa358` | Read | app.py |
| `agent-a2d8a40` | Read | c4-code-gui-stores.md |
| `agent-a2d8a40` | Read | c4-code-gui-components-tests.md |
| `4501a34b` | Bash | `sleep 90` |

Note: Duplicate row inflation (3-4x per tool_use_id) is present in the raw results, consistent with the ingestion pipeline issue flagged in PR-002.

**Existing coverage:** PR-002 (completed) investigated this pattern extensively. Conclusion was that 69% of orphans are blocking waits (sleep, TaskOutput polling) representing normal session termination, with minimal lost work risk.

## MEDIUM Findings

### Pattern 2: Tool Authorization Retry Waste

Session `5bf50e64-3af7-4542-8299-6c8a89c70d73` had 12 UNAUTHORIZED denials for the Bash tool. This indicates the agent repeatedly attempted Bash calls that were denied by the permission model, wasting ~12 API round-trips.

**Assessment:** Only 1 session affected. While 12 denials is notable, this appears to be an isolated case rather than a systemic pattern. No product request created. Will monitor in subsequent retrospectives.

### Pattern 4: Excessive Context Compaction

27 sessions triggered 3+ compaction events. Top 5 by count: 16, 12, 12, 10, 10. One sub-agent session (`agent-acdfa6c`) also appeared, indicating compaction affects both parent and sub-agent sessions.

**Existing coverage:** PR-003 (open) already tracks this pattern with identical findings from the previous retrospective cycle. No duplicate PR needed.

### Pattern 5: Sub-Agent Failure Cascades

1 sub-agent session matched: `agent-a55770f` ran for 3190 seconds (~53 minutes) with 56 errors and 0 orphaned tools. Since it had errors but no orphaned tools, severity is MEDIUM per the classification rules.

**Assessment:** Only 1 sub-agent affected. The 56 errors without orphaned tools suggests the sub-agent was retrying operations that consistently failed, but eventually completed (no orphaned calls). No product request created. Will monitor in subsequent retrospectives.

## Product Requests Created

None. All HIGH severity findings are already covered by existing product requests:

- **PR-001** (completed): Orphaned WebFetch calls — addressed globally by auto-dev-mcp BL-536
- **PR-002** (completed): Orphaned non-WebFetch tool calls — determined to be normal session lifecycle patterns
- **PR-003** (open): Excessive context compaction — still pending remediation
- **PR-006** (open): WebFetch 58.3% error rate — still pending remediation

## Data Availability Notes

- Session data covers the default 7-day lookback window (since ~Feb 18, 2026)
- 111 session files found and ingested
- The `orphaned_tools` troubleshoot query returns duplicate rows per tool_use_id (3-4x inflation), consistent with the known ingestion pipeline issue noted in PR-002. Unique counts reported above are deduplicated by tool_use_id.
- The `query_type=summary` mode referenced in the task prompt is not a valid analytics query type. Used `session_list` instead to verify data availability.
