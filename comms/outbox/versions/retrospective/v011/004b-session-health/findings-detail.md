# Session Health Findings Detail - v011

## Data Availability Verification

**Query:**
```
query_cli_sessions(
    project="stoat-and-ferret",
    mode="analytics",
    query_type="session_list"
)
```

**Result:** 50 sessions returned. Date range: 2026-02-14 to 2026-02-24. Mix of parent sessions and sub-agent sessions. Data confirmed available.

---

## Pattern 1: Hung WebFetch Calls

**Severity:** HIGH (zero tolerance)
**Threshold:** Any orphaned WebFetch tool_use with has_result=FALSE

**Query:**
```sql
SELECT tc.session_id, tc.tool_name, COUNT(DISTINCT tc.tool_use_id) as orphan_count,
       GROUP_CONCAT(DISTINCT tc.tool_use_id) as tool_use_ids
FROM tool_calls tc
WHERE tc.has_result = FALSE AND tc.tool_name = 'WebFetch'
GROUP BY tc.session_id, tc.tool_name
ORDER BY orphan_count DESC
```

**Raw Results (12 unique orphans across 12 sessions):**

| Session ID | Orphan Count | Tool Use IDs |
|-----------|-------------|--------------|
| agent-a8410c2 | 2 | toolu_01SfXvgj3vswAvPshEBNuNWw, toolu_01P6d5g1fojjr2cwWv1iZp2A |
| 792eb162-520c-44c4-b20c-7aa9535bd873 | 1 | toolu_01QygWk7ruTJJ4wEMJ5z3bWk |
| 98c9d711-45bb-4294-95d0-3bab9a14a7fc | 1 | toolu_01WBWuJUp2CpndMA93ZdKt2Y |
| agent-a5f8dfc | 1 | toolu_01Navb37g1e4YNc2xyd6E273 |
| 4a029681-5c00-4623-81d8-b633eca67df4 | 1 | toolu_01VohDh6N9MPDSQtzqgTATBG |
| agent-ae168d6 | 1 | toolu_019dw4KbiYRerSDbfQD4Wz9c |
| agent-a3ef471 | 1 | toolu_01To8o5Hj2igTSrQHnmuWwYp |
| agent-ab31cde | 1 | toolu_01WH2jbvkMi3nXykc57E82pQ |
| agent-ab353ea | 1 | toolu_01HdDSqMkgysFuZ3v5ixuNRA |
| agent-ab601f1 | 1 | toolu_01RBau1R4HSzby6X9rNE1Ahp |
| 23c77755-b880-4a44-81fc-c6f3813e9986 | 1 | toolu_01HB9LmpcGuVu2hEt2fKc1mx |
| 47054390-287b-4d87-963a-69480668444e | 1 | toolu_01PgbiNAZFw9Nu2Da664Kq8G |

**Known URLs from raw data:** ffmpeg filter docs (ayosec.github.io), Claude platform pricing, releasebot.io, code.claude.com docs, platform.claude.com docs, GitHub gist.

**Classification:** HIGH - 12 orphaned WebFetch calls detected. However, existing PR-001 (completed) and PR-006 (open) already cover this finding. PR-001 identified root cause as WebFetch having no timeout, addressed by auto-dev-mcp BL-536.

---

## Pattern 2: Tool Authorization Retry Waste

**Severity:** MEDIUM
**Threshold:** Same tool denied 3+ times in one session

**Query:**
```sql
SELECT tc.session_id, tc.tool_name, COUNT(*) as denial_count
FROM tool_calls tc
WHERE tc.is_error = TRUE AND tc.result_snippet LIKE '%UNAUTHORIZED%'
GROUP BY tc.session_id, tc.tool_name
HAVING COUNT(*) >= 3
ORDER BY denial_count DESC
```

**Raw Results (1 match):**

| Session ID | Tool Name | Denial Count |
|-----------|-----------|-------------|
| 5bf50e64-3af7-4542-8299-6c8a89c70d73 | Bash | 12 |

**Classification:** MEDIUM - 1 session with 12 repeated Bash UNAUTHORIZED denials. The agent was stuck in a retry loop, wasting ~12 API round-trips. This is an isolated incident (1 of 50+ sessions) rather than a systemic pattern.

---

## Pattern 3: Orphaned Tool Calls (Non-WebFetch)

**Severity:** HIGH (zero tolerance)
**Threshold:** Any tool_use without tool_result in a completed session (excluding WebFetch)

**Query:**
```sql
SELECT tc.session_id, tc.tool_name, COUNT(DISTINCT tc.tool_use_id) as orphan_count,
       GROUP_CONCAT(DISTINCT tc.tool_use_id) as tool_use_ids
FROM tool_calls tc
WHERE tc.has_result = FALSE AND tc.tool_name != 'WebFetch'
GROUP BY tc.session_id, tc.tool_name
ORDER BY orphan_count DESC
```

**Raw Results (35 unique orphans across 35 session/tool combinations):**

| Session ID | Tool | Orphan Count |
|-----------|------|-------------|
| 240a0257-643e-4f41-b34e-daeeaa1c6721 | TaskOutput | 3 |
| aaefbad2-2044-476a-8439-7b370cb813d4 | Task | 2 |
| agent-a2d8a40 | Read | 2 |
| ee7dda9e-7f02-4cb1-9904-e9990734ca51 | Task | 2 |
| 03679aa7-a6f4-4e5f-9c06-e848f8cb7c5b | TaskOutput | 1 |
| 08f1f0da-0771-4da3-91b6-149320064faf | Read | 1 |
| 0bcb8587-5e3a-484c-a50d-fe45f46723de | Task | 1 |
| 1d497037-379b-49a7-b650-2ea5b2a851c2 | Bash | 1 |
| 2a941a6d-d5e1-4d78-baf0-c25bc2d654e3 | Read | 1 |
| 2b3751e4-1144-4f01-9e7f-735db21f440f | TaskOutput | 1 |
| 4501a34b-449d-40f4-87ae-eebbb6f55a46 | Bash | 1 |
| 497080ec-b00b-4934-936c-a433e1d28e68 | Bash | 1 |
| 526739f2-a1ea-4ad8-bb11-adf7beeb371d | Bash | 1 |
| 52cf738c-93ba-4068-9599-131dc0a71100 | TaskOutput | 1 |
| 5cc0ac9c-8ea6-43c4-acb0-45c3ba73d27f | Bash | 1 |
| 7560e29e-07d7-4d65-a674-0a5deca92bfb | Bash | 1 |
| 82746b32-7c5b-4ec6-8f4f-2bbf4497acba | Read | 1 |
| 832998f8-c26f-407a-916a-451360fc9420 | Task | 1 |
| 8717e56e-654d-4fc2-acc9-4dff51b9beea | Bash | 1 |
| 8959c1ad-c503-4c7f-acae-9203ca1e2bd0 | Bash | 1 |
| 9798eba0-1162-48fd-9a98-a9e05eb5bac0 | Bash | 1 |
| 9798eba0-1162-48fd-9a98-a9e05eb5bac0 | Read | 1 |
| 99f08e8c-5516-41a2-a528-7aa72d6275a1 | Bash | 1 |
| a56c2e2e-fc2b-4918-979d-34fb790b74bf | Bash | 1 |
| aaefbad2-2044-476a-8439-7b370cb813d4 | Edit | 1 |
| agent-a0fa358 | Read | 1 |
| agent-a5e391f | Bash | 1 |
| agent-af225e7 | Bash | 1 |
| b3acc3e9-2adf-46dd-934d-7bc2294c13ec | Grep | 1 |
| bd143c2d-bdd5-4fb1-b9f4-d9d5d33373fd | Task | 1 |
| dbaca306-096a-4911-8fd8-75e302ca0641 | Write | 1 |
| de65edd6-89ec-45b3-ad67-cd27f55805b7 | TaskOutput | 1 |
| e680d398-ca01-420f-87e7-08ba650ed24c | Bash | 1 |
| f9efa171-4e9b-4a13-9796-2fdbd353bedd | TaskOutput | 1 |

**Tool type breakdown:** Bash (13), TaskOutput (7), Task (6), Read (6), Edit (1), Grep (1), Write (1)

**Classification:** HIGH - 35 orphaned non-WebFetch calls detected. However, PR-002 (completed) investigated this pattern and concluded: 69% are blocking waits (sleep, TaskOutput polling, pytest) representing normal session termination. Lost work risk minimal. Row inflation from duplicate tool_use_ids in ingestion pipeline also noted.

---

## Pattern 4: Excessive Context Compaction

**Severity:** MEDIUM
**Threshold:** 3+ compaction events per session

**Query:**
```sql
SELECT ce.session_id, COUNT(*) as compaction_count
FROM compaction_events ce
GROUP BY ce.session_id
HAVING COUNT(*) >= 3
ORDER BY compaction_count DESC
```

**Raw Results (27 sessions):**

| Session ID | Compaction Count |
|-----------|-----------------|
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
| 3f0bd0c9-d89e-4c9a-bcea-e229d77bc9c1 | 6 |
| 17b54bed-4830-4bee-a4fb-b7e02a647dca | 6 |
| 0809e915-4edc-4308-b453-7ea17c5d4b3e | 6 |
| fe1c4c9f-fe62-400c-b804-fcb24148e32a | 5 |
| 764b36bd-9181-4f8e-877a-24d1ead896e1 | 5 |
| 65c10871-a2c9-4488-9853-45b8e5d5f584 | 5 |
| c61dc1f6-30ad-4542-a63c-b5e96135823a | 4 |
| 9826ce4b-6b64-4961-bbfc-3e60ad2afd4f | 4 |
| 9798eba0-1162-48fd-9a98-a9e05eb5bac0 | 4 |
| 7ee83eb8-ea60-4731-beed-a03833e67a9f | 4 |
| 133419bc-b8f2-4ce7-8c8b-1a537429adde | 4 |
| fd64f530-4e71-4ad9-917e-503019a368c2 | 3 |
| f17b818e-9aaa-4b59-bf25-8f75f8458b88 | 3 |
| c8232369-2c44-4e5c-9a68-2dc5bdb540b1 | 3 |
| agent-acdfa6c | 3 |
| 9b738766-0aae-4e4c-a38b-d6768fea9e64 | 3 |
| 2a941a6d-d5e1-4d78-baf0-c25bc2d654e3 | 3 |

**Distribution:** 2 sessions with 10+ compactions, 6 sessions with 6-9, 8 sessions with 4-5, 11 sessions with exactly 3.

**Classification:** MEDIUM - 27 sessions exceeded the threshold. PR-003 (open) already captures this finding. The pattern persists at similar severity to the prior retrospective.

---

## Pattern 5: Sub-Agent Failure Cascades

**Severity:** HIGH (errors + orphans), MEDIUM (errors or orphans alone)
**Threshold:** Sub-agents with duration >30 minutes + errors or orphaned tools

**Query:**
```sql
SELECT s.session_id, s.duration_secs, s.parent_session_id,
       COALESCE(err.error_count, 0) as error_count,
       COALESCE(orph.orphaned_count, 0) as orphaned_count
FROM sessions s
LEFT JOIN (
    SELECT session_id, COUNT(*) as error_count
    FROM tool_calls WHERE is_error = TRUE GROUP BY session_id
) err ON s.session_id = err.session_id
LEFT JOIN (
    SELECT session_id, COUNT(*) as orphaned_count
    FROM tool_calls WHERE has_result = FALSE GROUP BY session_id
) orph ON s.session_id = orph.session_id
WHERE s.is_subagent = TRUE
  AND s.duration_secs > 1800
  AND (COALESCE(err.error_count, 0) > 0 OR COALESCE(orph.orphaned_count, 0) > 0)
ORDER BY s.duration_secs DESC
```

**Raw Results (1 match):**

| Session ID | Duration (s) | Parent Session | Error Count | Orphaned Count |
|-----------|-------------|----------------|-------------|----------------|
| agent-a55770f | 3190.183 | null | 56 | 0 |

**Classification:** MEDIUM - error_count > 0 but orphaned_count = 0 (only one condition met, not both). The sub-agent ran for ~53 minutes with 56 errors. The null parent_session_id may indicate metadata was not captured. No orphaned tools means the sub-agent was still receiving responses despite errors.
