# Session Health Findings Detail - v007 Retrospective

## Pattern 1: Hung WebFetch Calls

### Query Used

```sql
SELECT tc.session_id, tc.tool_use_id, tc.webfetch_url, COUNT(*) as duplicate_count
FROM tool_calls tc
WHERE tc.tool_name = 'WebFetch' AND tc.has_result = FALSE
GROUP BY tc.session_id, tc.tool_use_id
ORDER BY tc.timestamp DESC
```

### Raw Results (14 unique instances)

| Session ID | Tool Use ID | URL | DB Rows |
|------------|-------------|-----|---------|
| `792eb162-520c-44c4-b20c-7aa9535bd873` | `toolu_01QygWk7ruTJJ4wEMJ5z3bWk` | ayosec.github.io/ffmpeg-filters-docs/7.1/Filters/Audio/atempo.html | 4 |
| `98c9d711-45bb-4294-95d0-3bab9a14a7fc` | `toolu_01WBWuJUp2CpndMA93ZdKt2Y` | platform.claude.com/docs/en/about-claude/pricing | 2 |
| `agent-a5f8dfc` | `toolu_01Navb37g1e4YNc2xyd6E273` | releasebot.io/updates/anthropic/claude-code | 1 |
| `4a029681-5c00-4623-81d8-b633eca67df4` | `toolu_01VohDh6N9MPDSQtzqgTATBG` | code.claude.com/docs/en/sub-agents | 1 |
| `agent-ae168d6` | `toolu_019dw4KbiYRerSDbfQD4Wz9c` | platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use | 1 |
| `agent-ab353ea` | `toolu_01HdDSqMkgysFuZ3v5ixuNRA` | gist.github.com/tirufege/0720c288092c1a3a4750f7c198aa524b | 2 |
| `agent-a8410c2` | `toolu_01P6d5g1fojjr2cwWv1iZp2A` | www.braydenblackwell.com/blog/ffmpeg-text-rendering | 1 |
| `agent-a8410c2` | `toolu_01SfXvgj3vswAvPshEBNuNWw` | ffmpegbyexample.com/examples/50gowmkq/fade_in_and_out_text_using_the_drawtext_filter/ | 1 |
| `agent-a3ef471` | `toolu_01To8o5Hj2igTSrQHnmuWwYp` | github.com/golemcloud/golem-ai/issues/23 | 3 |
| `agent-ab31cde` | `toolu_01WH2jbvkMi3nXykc57E82pQ` | algora.io/golemcloud/home | 1 |
| `agent-ab601f1` | `toolu_01RBau1R4HSzby6X9rNE1Ahp` | github.com/MonoGame/MonoGame/issues/8120 | 5 |
| `agent-a73b721` | `toolu_01JkbNVvPUau1aGvyauLFhwQ` | www.upwork.com/freelance-jobs/apply/... | 1 |
| `47054390-287b-4d87-963a-69480668444e` | `toolu_01PgbiNAZFw9Nu2Da664Kq8G` | github.com/Jij-Inc/pyo3-stub-gen | 9 |
| `23c77755-b880-4a44-81fc-c6f3813e9986` | `toolu_01HB9LmpcGuVu2hEt2fKc1mx` | github.com/Jij-Inc/pyo3-stub-gen/tree/main/examples | 2 |

### Classification Reasoning

**Severity: HIGH (zero tolerance)**

Every orphaned WebFetch represents a hung HTTP request. The pattern shows WebFetch calls to diverse domains all failing to return results. The duplicate DB rows for the same tool_use_id suggest the JSONL ingestion records the tool_use block multiple times when it appears in successive assistant messages (context compaction replays). The underlying issue is consistent: WebFetch has no effective timeout, so hung requests block indefinitely.

---

## Pattern 2: Tool Authorization Retry Waste

### Query Used

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

### Raw Results (1 match)

| Session ID | Tool Name | Denial Count |
|------------|-----------|-------------|
| `5bf50e64-3af7-4542-8299-6c8a89c70d73` | Bash | 12 |

### Classification Reasoning

**Severity: MEDIUM**

One session had 12 UNAUTHORIZED Bash denials. This means the agent attempted to run Bash commands 12 times that were all blocked. At ~1 API round-trip per attempt, this wasted significant execution budget. The agent failed to adapt its approach after repeated denials. This is an agent behavior issue, not an infrastructure issue - the permission system worked correctly.

---

## Pattern 3: Orphaned Tool Calls (Non-WebFetch)

### Query Used

```sql
SELECT tc.tool_name, COUNT(DISTINCT tc.tool_use_id) as unique_orphaned_count, COUNT(*) as total_rows
FROM tool_calls tc
WHERE tc.tool_name != 'WebFetch' AND tc.has_result = FALSE
GROUP BY tc.tool_name
ORDER BY unique_orphaned_count DESC
```

### Raw Results (7 tool types)

| Tool Name | Unique Orphaned | Total DB Rows |
|-----------|----------------|---------------|
| Bash | 11 | 22 |
| Task | 7 | 17 |
| TaskOutput | 7 | 33 |
| Read | 6 | 15 |
| Edit | 1 | 4 |
| Grep | 1 | 5 |
| Write | 1 | 1 |

### Sample Orphaned Calls (from detailed query)

**Bash orphans** (11 unique):
- `sleep 240` (polling waits) - sessions `9b738766`, `497080ec`
- `sleep 90` (polling waits) - session `4501a34b`
- `sleep 60 && wc -l ...` (progress check) - session `a56c2e2e`
- System test execution - session `eaece100`
- Yocova data analysis script - session `9798eba0`

**Read orphans** (6 unique):
- File reads in `agent-a0fa358`, `agent-a2d8a40` (C4 documentation sessions)
- File read in `9798eba0` (tool result file)

**Task orphans** (7 unique):
- Research sub-agents in `ee7dda9e` (parallel tool research)
- FFmpeg research in `832998f8`
- Yocova data tasks in `aaefbad2`

**Edit orphans** (1 unique):
- Large code edit in `aaefbad2` (Yocova mapping script)

### Classification Reasoning

**Severity: HIGH (zero tolerance)**

While some orphaned Bash calls (sleep commands) are expected when sessions are terminated, the orphaned Read (6), Edit (1), Write (1), and Grep (1) calls represent 9 instances of abnormal termination during core file operations. Orphaned Task/TaskOutput calls (14 total) indicate sub-agent coordination failures where parent sessions ended before sub-agents completed.

---

## Pattern 4: Excessive Context Compaction

### Query Used

```sql
SELECT
    ce.session_id,
    COUNT(*) as compaction_count
FROM compaction_events ce
GROUP BY ce.session_id
HAVING COUNT(*) >= 3
ORDER BY compaction_count DESC
```

### Raw Results (24 sessions)

| Session ID | Compaction Count |
|------------|-----------------|
| `f9efa171-4e9b-4a13-9796-2fdbd353bedd` | 16 |
| `aaefbad2-2044-476a-8439-7b370cb813d4` | 12 |
| `247375f3-ba69-4cbd-b60e-f4aa43045131` | 12 |
| `b3acc3e9-2adf-46dd-934d-7bc2294c13ec` | 10 |
| `9b6aed8e-8f2c-461a-8cb1-94e0d6cb2a8c` | 10 |
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
| `9798eba0-1162-48fd-9a98-a9e05eb5bac0` | 4 |
| `7ee83eb8-ea60-4731-beed-a03833e67a9f` | 4 |
| `133419bc-b8f2-4ce7-8c8b-1a537429adde` | 4 |
| `fd64f530-4e71-4ad9-917e-503019a368c2` | 3 |
| `f17b818e-9aaa-4b59-bf25-8f75f8458b88` | 3 |
| `c8232369-2c44-4e5c-9a68-2dc5bdb540b1` | 3 |
| `agent-acdfa6c` | 3 |
| `2a941a6d-d5e1-4d78-baf0-c25bc2d654e3` | 3 |

### Classification Reasoning

**Severity: MEDIUM**

24 of ~50 sessions (48%) hit the 3+ compaction threshold. This is widespread. The top session had 16 compaction events, meaning it exhausted and compressed its context 16 times. While compaction is a normal part of long sessions, this frequency suggests:
- Sessions are reading too many large files without summarizing
- Long implementation tasks routinely exceed context limits
- Context management strategies (summarizing before compaction) may not be applied consistently

This is documented but no product request is created as individual compaction is expected for long tasks and the threshold of 3 may be too low for this project's typical workload.

---

## Pattern 5: Sub-Agent Failure Cascades

### Query Used

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

### Raw Results (1 match)

| Session ID | Duration (s) | Parent | Errors | Orphaned |
|------------|-------------|--------|--------|----------|
| `agent-a55770f` | 3190.2 | null | 56 | 0 |

### Session Details

- **Started:** 2026-02-03T09:59:51Z
- **Ended:** 2026-02-03T10:53:01Z
- **Duration:** ~53 minutes
- **Task:** Yocova metadata comparison (identifying modified components between prod and UAT)
- **Tool calls:** 332 total, 56 errors
- **Error rate:** 16.9%

### Classification Reasoning

**Severity: MEDIUM** (errors only, no orphaned tools)

Per the pattern criteria: HIGH requires both error_count > 0 AND orphaned_count > 0. This session only has errors (orphaned_count = 0), so it is classified MEDIUM.

The 56 errors over 332 tool calls (16.9% error rate) across 53 minutes indicates the sub-agent was struggling with its task but continued executing (no orphaned tools = no hangs). The task was Yocova metadata comparison, not directly stoat-and-ferret code, but ran within the project scope. The parent_session_id is null, which may indicate the parent session link was lost during ingestion.

No product request created as this is an isolated occurrence on a non-core task.
