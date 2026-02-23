# Session Health Findings Detail - v010

Full query details, raw results, and classification reasoning for each detection pattern.

---

## Pattern 1: Hung WebFetch Calls

### Query

```
query_cli_sessions(
    project="stoat-and-ferret",
    mode="troubleshoot",
    query_type="orphaned_tools"
)
```

Filter: WebFetch tool calls only.

### Raw Results (WebFetch subset)

| Timestamp | Tool Use ID | Session ID | Input Preview |
|-----------|-------------|------------|---------------|
| 2026-02-18T14:31:15.539Z | `toolu_01QygWk7ruTJJ4wEMJ5z3bWk` | `792eb162-520c-44c4-b20c-7aa9535bd873` | WebFetch of `https://ayosec.github.io/ffmpeg-filters-docs/7.1/Filters/Audio/atempo.html` |

Note: This single tool_use_id appears 4 times in results due to duplicate ingestion inflation.

### Classification

**Severity: HIGH** (zero tolerance threshold met - 1 orphaned WebFetch call found)

**Remediation status:** Already addressed. PR-001 (completed) investigated this class of finding. Root cause: WebFetch lacks built-in timeout. Remediated globally via auto-dev-mcp BL-536. Session `792eb162` ended at `2026-02-18T14:31:33.420Z`, only 18 seconds after the orphaned call - impact minimal.

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

| Session ID | Tool Name | Denial Count |
|------------|-----------|-------------|
| `5bf50e64-3af7-4542-8299-6c8a89c70d73` | Bash | 12 |

### Classification

**Severity: MEDIUM** (threshold met: same tool denied 3+ times in one session)

**Reasoning:** 12 Bash denials in a single session represents significant waste (~12 wasted API round-trips). The agent repeatedly attempted Bash commands that the permission mode or autoDevToolKey restrictions rejected, rather than adapting to use allowed alternatives. However, this is an isolated single-session occurrence, not a systemic pattern across multiple sessions.

**No product request created** - single instance, not systemic. If recurrence is observed in future retrospectives, a PR should be created to investigate agent retry behavior on authorization failures.

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

Filter: Exclude WebFetch tool calls.

### Raw Results (Non-WebFetch, deduplicated by tool_use_id)

| Timestamp | Tool Use ID | Tool | Session ID | Context |
|-----------|-------------|------|------------|---------|
| 2026-02-23T23:55:14.110Z | `toolu_013Pwu...` | Bash | `81a62f81-c2ab-4f5b-9cac-b9d8f1d28cf1` | `sleep 90` - wait before polling |
| 2026-02-23T19:10:09.738Z | `toolu_01NwEN...` | Read | `82746b32-7c5b-4ec6-8f4f-2bbf4497acba` | Reading `manifest.json` |
| 2026-02-19T22:05:18.771Z | `toolu_01Qz9G...` | Read | `agent-a0fa358` | Reading `app.py` |
| 2026-02-19T21:58:27.585Z | `toolu_01WHWFtS...` | Read | `agent-a2d8a40` | Reading C4 code docs (2 duplicate rows) |
| 2026-02-19T21:58:28.344Z | `toolu_016Lh8...` | Read | `agent-a2d8a40` | Reading C4 component docs (2 duplicate rows) |
| 2026-02-18T16:20:10.585Z | `toolu_018LUW...` | Bash | `4501a34b-449d-40f4-87ae-eebbb6f55a46` | `sleep 90` - wait before polling Task 005 (4 duplicate rows) |

**5 unique tool_use_ids, 10 duplicate rows** (total 15 rows including WebFetch).

### Classification

**Severity: HIGH** (zero tolerance threshold met - 5 orphaned non-WebFetch tool calls found)

**Remediation status:** Already addressed. PR-002 (completed) investigated this class of finding. Conclusions:
- 2 of 5 are `sleep 90` commands (blocking waits) - normal session termination during long operations
- 3 of 5 are Read calls - non-destructive, likely session ended during file reads
- All represent normal session lifecycle patterns, not crashes or data loss
- Duplicate row inflation (2-4x per tool_use_id) is a known ingestion pipeline artifact

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

| Session ID | Compaction Count |
|------------|-----------------|
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

**27 sessions total.** Distribution: 1 session at 16, 2 at 12, 2 at 10, 3 at 7, 5 at 6, 3 at 5, 5 at 4, 6 at 3.

### Classification

**Severity: MEDIUM** (threshold met: 27 sessions with 3+ compactions)

**Remediation status:** Already tracked. PR-003 ("Session health: Excessive context compaction across 27 sessions") is open at P2 with the same data set. No new product request created.

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

| Session ID | Duration (secs) | Parent Session | Error Count | Orphaned Count |
|------------|----------------|----------------|-------------|----------------|
| `agent-a55770f` | 3190.183 | null | 56 | 0 |

### Classification

**Severity: MEDIUM** (errors > 0 but orphaned_count = 0; HIGH requires both)

**Reasoning:** Sub-agent `agent-a55770f` ran for 53 minutes with 56 errors but no orphaned tools. The high error count suggests persistent retry behavior against failing operations, but the absence of orphaned tools means no work was left incomplete. The null parent_session_id may indicate the parent session was already cleaned up or the relationship wasn't captured during ingestion.

**No product request created** - MEDIUM severity, single instance, not systemic. If multiple sub-agents exhibit this pattern in future retrospectives, a PR should investigate error-driven retry loops in sub-agent execution.
