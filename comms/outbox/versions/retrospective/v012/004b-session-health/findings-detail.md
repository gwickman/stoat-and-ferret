# Session Health Findings Detail - v012

Detailed query results and classification reasoning for each detection pattern.

---

## Pattern 1: Hung WebFetch Calls

**Severity:** HIGH (zero tolerance)
**Threshold:** Any orphaned WebFetch tool_use with has_result=FALSE in a completed session

### Query

```
query_cli_sessions(
    project="stoat-and-ferret",
    mode="troubleshoot",
    query_type="orphaned_tools"
)
```

Filtered to `tool_name = "WebFetch"`.

### Raw Results

1 unique orphaned WebFetch call (appears 4x due to row inflation):

| timestamp | tool_use_id | session_id | input_preview |
|-----------|-------------|------------|---------------|
| 2026-02-18T14:31:15.539Z | toolu_01QygWk7ruTJJ4wEMJ5z3bWk | 792eb162-520c-44c4-b20c-7aa9535bd873 | `{"url": "https://ayosec.github.io/ffmpeg-filters-docs/7.1/Filters/Audio/atempo.html", ...}` |

Session ended at 2026-02-18T14:31:33.420Z (18 seconds after the WebFetch was initiated).

### Classification Reasoning

HIGH severity per zero-tolerance threshold. However, this is a continuation of the pattern already identified and addressed:
- PR-001 (completed): Root cause is WebFetch lacking timeout + agents fetching from unresponsive external sites
- PR-006 (open): Tracks the broader 58.3% WebFetch error rate
- auto-dev-mcp BL-536: Global fix in progress

No new product request needed — existing PRs provide full coverage.

---

## Pattern 2: Tool Authorization Retry Waste

**Severity:** MEDIUM
**Threshold:** Same tool denied 3+ times in one session

### Query

```sql
SELECT
    tc.session_id,
    tc.tool_name,
    COUNT(*) as denial_count
FROM tool_calls tc
WHERE tc.is_error = TRUE
  AND tc.result_snippet LIKE '%UNAUTHORIZED%'
GROUP BY tc.session_id, tc.tool_name
HAVING COUNT(*) >= 3
ORDER BY denial_count DESC
```

### Raw Results

| session_id | tool_name | denial_count |
|------------|-----------|-------------|
| 5bf50e64-3af7-4542-8299-6c8a89c70d73 | Bash | 12 |

### Classification Reasoning

MEDIUM severity — 1 session with 12 Bash UNAUTHORIZED denials. The agent repeatedly attempted Bash calls that were denied by the MCP tool key authorization system, wasting approximately 12 API round-trips.

This is an isolated incident (only 1 session out of 111 ingested). The high denial count (12) suggests the agent did not adapt its strategy after initial denials, but since this is a single occurrence, it does not rise to systemic. No product request created.

---

## Pattern 3: Orphaned Tool Calls (Non-WebFetch)

**Severity:** HIGH (zero tolerance)
**Threshold:** Any tool_use without tool_result in a completed session (excluding WebFetch)

### Query

```
query_cli_sessions(
    project="stoat-and-ferret",
    mode="troubleshoot",
    query_type="orphaned_tools"
)
```

Filtered to exclude `tool_name = "WebFetch"`.

### Raw Results (deduplicated by tool_use_id)

| timestamp | tool_use_id | tool_name | session_id | input_preview |
|-----------|-------------|-----------|------------|---------------|
| 2026-02-23T19:10:09.738Z | toolu_01NwENjBoCRk1XDSkUE9Duti | Read | 82746b32-7c5b-4ec6-8f4f-2bbf4497acba | manifest.json |
| 2026-02-19T22:05:18.771Z | toolu_01Qz9GMp1sQKPfJQkBoqYNth | Read | agent-a0fa358 | app.py |
| 2026-02-19T21:58:27.585Z | toolu_01WHWFtS8ptyqPPRpJ9BZqdX | Read | agent-a2d8a40 | c4-code-gui-stores.md |
| 2026-02-19T21:58:28.344Z | toolu_016Lh84ob4CzuEoSiZtXTNgn | Read | agent-a2d8a40 | c4-code-gui-components-tests.md |
| 2026-02-18T16:20:10.585Z | toolu_018LUWwLQhcD2oDbAPUrGzKK | Bash | 4501a34b-449d-40f4-87ae-eebbb6f55a46 | `sleep 90` |

5 unique orphaned tool calls across 4 sessions. Note: raw query returned 10 rows due to 2-4x duplicate inflation per tool_use_id.

### Classification Reasoning

HIGH severity per zero-tolerance threshold. Breakdown:
- 4 orphaned Read calls: Non-destructive file reads. Sessions likely terminated during the read operation. No data loss risk.
- 1 orphaned Bash call (`sleep 90`): Session terminated during a polling sleep. No data loss risk.

All 5 orphans are non-destructive operations, consistent with PR-002's finding that 69% of orphans are blocking waits representing normal session termination. No new product request needed — PR-002 (completed) provides full coverage.

---

## Pattern 4: Excessive Context Compaction

**Severity:** MEDIUM
**Threshold:** 3+ compaction events per session

### Query

```sql
SELECT
    ce.session_id,
    COUNT(*) as compaction_count
FROM compaction_events ce
GROUP BY ce.session_id
HAVING COUNT(*) >= 3
ORDER BY compaction_count DESC
```

### Raw Results

27 sessions matched. Top 10:

| session_id | compaction_count |
|------------|-----------------|
| f9efa171-4e9b-4a13-9796-2fdbd353bedd | 16 |
| aaefbad2-2044-476a-8439-7b370cb813d4 | 12 |
| 247375f3-ba69-4cbd-b60e-f4aa43045131 | 12 |
| b3acc3e9-2adf-46dd-934d-7bc2294c13ec | 10 |
| 9b6aed8e-8f2c-461a-8cb1-94e0d6cb2a8c | 10 |
| de65edd6-89ec-45b3-ad67-cd27f55805b7 | 7 |
| 52cf738c-93ba-4068-9599-131dc0a71100 | 7 |
| 1093ba6f-b262-4adb-912c-890b4f13b4e1 | 7 |
| 7458fba6-90bb-4c0f-8cc0-b3fa32b66930 | 6 |
| 47b617ad-1e6a-492d-b6c7-ab631cd6e5fb | 6 |

Remaining 17 sessions had 3-6 compactions each. 1 sub-agent session (`agent-acdfa6c`) was among the matches.

Distribution:
- 16 compactions: 1 session
- 10-12 compactions: 4 sessions
- 6-7 compactions: 8 sessions
- 3-5 compactions: 14 sessions

### Classification Reasoning

MEDIUM severity — 27 sessions is a significant count indicating a systemic pattern. However, PR-003 (open) already tracks this exact finding with identical session data. The compaction counts are consistent with the previous retrospective's observations. No duplicate product request created.

---

## Pattern 5: Sub-Agent Failure Cascades

**Severity:** HIGH (errors + orphaned), MEDIUM (errors or orphaned alone)
**Threshold:** Sub-agents with duration >30 minutes combined with errors or orphaned tools

### Query

```sql
SELECT
    s.session_id,
    s.duration_secs,
    s.parent_session_id,
    COALESCE(err.error_count, 0) as error_count,
    COALESCE(orph.orphaned_count, 0) as orphaned_count
FROM sessions s
LEFT JOIN (
    SELECT session_id, COUNT(*) as error_count
    FROM tool_calls
    WHERE is_error = TRUE
    GROUP BY session_id
) err ON s.session_id = err.session_id
LEFT JOIN (
    SELECT session_id, COUNT(*) as orphaned_count
    FROM tool_calls
    WHERE has_result = FALSE
    GROUP BY session_id
) orph ON s.session_id = orph.session_id
WHERE s.is_subagent = TRUE
  AND s.duration_secs > 1800
  AND (COALESCE(err.error_count, 0) > 0 OR COALESCE(orph.orphaned_count, 0) > 0)
ORDER BY s.duration_secs DESC
```

### Raw Results

| session_id | duration_secs | parent_session_id | error_count | orphaned_count |
|------------|--------------|-------------------|-------------|----------------|
| agent-a55770f | 3190.183 | null | 56 | 0 |

### Classification Reasoning

MEDIUM severity — the sub-agent has errors (56) but no orphaned tools (0). Per the classification rule: HIGH requires both error_count > 0 AND orphaned_count > 0; this has only errors.

The sub-agent ran for ~53 minutes with 56 errors. The absence of orphaned tools suggests it was retrying failed operations but ultimately completing each tool call cycle (receiving results, even if error results). The `parent_session_id` is null, which may indicate the parent session data was not ingested or the relationship was not captured.

Only 1 sub-agent affected out of all sub-agent sessions in the dataset. Non-systemic. No product request created.
