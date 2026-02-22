# Session Health Findings Detail - v009 Retrospective

## Pattern 1: Hung WebFetch Calls

### Query

```
query_cli_sessions(
    project="stoat-and-ferret",
    mode="troubleshoot",
    query_type="orphaned_tools"
)
```

Filtered results to `tool_name = "WebFetch"` only.

### Raw Results

1 WebFetch orphan found (appeared 4x in raw results due to row inflation):

| Timestamp | tool_use_id | Session | URL |
|-----------|-------------|---------|-----|
| 2026-02-18T14:31:15.539Z | `toolu_01QygWk7ruTJJ4wEMJ5z3bWk` | `792eb162-520c-44c4-b20c-7aa9535bd873` | `https://ayosec.github.io/ffmpeg-filters-docs/7.1/Filters/Audio/atempo.html` |

Session ended at `2026-02-18T14:31:33.420Z` (~18 seconds after the WebFetch call).

### Classification

**HIGH** (zero tolerance threshold). However, this is a pre-v009 finding (Feb 18, v009 execution started Feb 22) that was already captured and resolved by PR-001. The root cause (WebFetch lacks built-in timeout) was addressed globally by auto-dev-mcp BL-536. No new product request created.

---

## Pattern 2: Tool Authorization Retry Waste

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
|-----------|-----------|-------------|
| `5bf50e64-3af7-4542-8299-6c8a89c70d73` | Bash | 12 |

### Classification

**MEDIUM** (threshold: 3+ denials of same tool in one session). One session had 12 Bash authorization denials. The agent repeatedly attempted Bash commands that were denied by the permission system without adapting its approach. This represents ~12 wasted API round-trips.

This is an isolated incident (1 out of 50+ sessions). Not systemic. No product request created.

---

## Pattern 3: Orphaned Tool Calls (Non-WebFetch)

### Query

```
query_cli_sessions(
    project="stoat-and-ferret",
    mode="troubleshoot",
    query_type="orphaned_tools"
)
```

Filtered results to exclude `tool_name = "WebFetch"`.

### Raw Results

15 total rows returned, de-duplicated to 6 unique orphaned tool calls:

| Timestamp | tool_use_id | Tool | Session | Input Preview |
|-----------|-------------|------|---------|---------------|
| 2026-02-22T17:36:25.306Z | `toolu_01YAGUAj4zVk442bL8vbH4Zp` | Task | `e30efed3` | Task "Find v009 start commit" |
| 2026-02-22T17:36:07.843Z | `toolu_0182c5UyDdZRLVnkN4aANyhV` | Bash | `d6bdad8a` | `sleep 120` - polling wait |
| 2026-02-19T22:05:18.771Z | `toolu_01Qz9GMp1sQKPfJQkBoqYNth` | Read | `agent-a0fa358` | Read `app.py` |
| 2026-02-19T21:58:27.585Z | `toolu_01WHWFtS8ptyqPPRpJ9BZqdX` | Read | `agent-a2d8a40` | Read `c4-code-gui-stores.md` |
| 2026-02-19T21:58:28.344Z | `toolu_016Lh84ob4CzuEoSiZtXTNgn` | Read | `agent-a2d8a40` | Read `c4-code-gui-components-tests.md` |
| 2026-02-18T16:20:10.585Z | `toolu_018LUWwLQhcD2oDbAPUrGzKK` | Bash | `4501a34b` | `sleep 90` - polling wait |

### Classification

**HIGH** (zero tolerance). However:
- 2 Bash orphans are `sleep` commands (expected polling pattern for orchestration sessions)
- 1 Task orphan is from the v009 retrospective orchestrator itself (session ended while Task running)
- 2 Read orphans are from Feb 19 sub-agents (likely v008 C4 documentation work)
- 1 Bash orphan is from Feb 18 (pre-v009)

All match the patterns already investigated in PR-002 (completed): blocking waits, sub-agent termination during reads, and normal session lifecycle. The 3x row inflation from duplicate `tool_use_id` entries is also a known ingestion artifact flagged in PR-002.

No new product request created - PR-002 covers this pattern comprehensively.

---

## Pattern 4: Excessive Context Compaction

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

27 sessions matched (all rows shown):

| session_id | compaction_count |
|-----------|-----------------|
| `f9efa171-4e9b-4a13-9796-2fdbd353bedd` | 16 |
| `aaefbad2-2044-476a-8439-7b370cb813d4` | 12 |
| `247375f3-ba69-4cbd-b60e-f4aa43045131` | 12 |
| `b3acc3e9-2adf-46dd-934d-7bc2294c13ec` | 10 |
| `9b6aed8e-8f2c-461a-8cb1-94e0d6cb2a8c` | 10 |
| `de65edd6-89ec-45b3-ad67-cd27f55805b7` | 7 |
| `52cf738c-93ba-4068-9599-131dc0a71100` | 7 |
| `1093ba6f-b262-4adb-912c-890b4f13b4e1` | 7 |
| `7458fba6-90bb-4c0f-8cc0-b3fa32b66930` | 6 |
| `47b617ad-1e6a-492d-b6c7-ab631cd6e5fb` | 6 |
| `3f0bd0c9-d89e-4c9a-bcea-e229d77bc9c1` | 6 |
| `17b54bed-4830-4bee-a4fb-b7e02a647dca` | 6 |
| `0809e915-4edc-4308-b453-7ea17c5d4b3e` | 6 |
| `fe1c4c9f-fe62-400c-b804-fcb24148e32a` | 5 |
| `764b36bd-9181-4f8e-877a-24d1ead896e1` | 5 |
| `65c10871-a2c9-4488-9853-45b8e5d5f584` | 5 |
| `c61dc1f6-30ad-4542-a63c-b5e96135823a` | 4 |
| `9826ce4b-6b64-4961-bbfc-3e60ad2afd4f` | 4 |
| `9798eba0-1162-48fd-9a98-a9e05eb5bac0` | 4 |
| `7ee83eb8-ea60-4731-beed-a03833e67a9f` | 4 |
| `133419bc-b8f2-4ce7-8c8b-1a537429adde` | 4 |
| `fd64f530-4e71-4ad9-917e-503019a368c2` | 3 |
| `f17b818e-9aaa-4b59-bf25-8f75f8458b88` | 3 |
| `c8232369-2c44-4e5c-9a68-2dc5bdb540b1` | 3 |
| `agent-acdfa6c` | 3 |
| `9b738766-0aae-4e4c-a38b-d6768fea9e64` | 3 |
| `2a941a6d-d5e1-4d78-baf0-c25bc2d654e3` | 3 |

### Classification

**MEDIUM** (threshold: 3+ compactions per session). 27 sessions matched, making this the most widespread finding. Distribution: 5 sessions with 10+, 8 with 6-9, 14 with 3-5.

This is a systemic issue. Total compaction events across these 27 sessions: ~161 compaction events. Average: ~6 compactions per affected session.

**PR-003 created** because the count and pattern suggest a systemic issue requiring investigation.

---

## Pattern 5: Sub-Agent Failure Cascades

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
|-----------|--------------|-------------------|-------------|---------------|
| `agent-a55770f` | 3190.183 | null | 56 | 0 |

### Classification

**MEDIUM** (errors present but no orphaned tools). Per classification rules: HIGH requires both error_count > 0 AND orphaned_count > 0; MEDIUM otherwise.

This sub-agent ran for ~53 minutes with 56 tool errors and no orphaned tools. The null `parent_session_id` despite `is_subagent=TRUE` is a data quality anomaly. The error rate (~1 error per minute) suggests the sub-agent was repeatedly encountering failures without successfully completing its task.

Isolated incident (1 of many sub-agents). No product request created.
