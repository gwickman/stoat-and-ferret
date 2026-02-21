# Tool-Type Analysis: Orphaned Non-WebFetch Calls

## Bash (11 orphaned calls) — No Work Lost

| # | Timestamp | Command | Session | Context |
|---|-----------|---------|---------|---------|
| 1 | Feb 1 13:57 | `mkdir -p "...theme-3-spawn-integration/..."` | agent-a5e391f | Creating exploration directories |
| 2 | Feb 5 22:43 | `sleep 300` | 99f08e8c | Waiting for version-design orchestration |
| 3 | Feb 6 17:51 | `sleep 120 && echo "waited 120 seconds"` | 1d497037 | Waiting for quality gates |
| 4 | Feb 6 17:52 | `uv run pytest -v 2>&1` | 5cc0ac9c | Running full pytest suite |
| 5 | Feb 13 08:44 | `grep -c "...__c..." Assigned_Plan__c.object` | agent-af225e7 | Counting Salesforce custom fields |
| 6 | Feb 18 16:20 | `sleep 90` | 4501a34b | Waiting before polling task |
| 7 | Feb 18 18:14 | `sleep 60 && wc -l /tmp/full_suite_output.txt` | a56c2e2e | Checking test suite progress |
| 8 | Feb 19 01:29 | `sleep 240` | 497080ec | Waiting 4 min before polling task |
| 9 | Feb 19 17:18 | `cd ... && python -c "import openpyxl..."` | 9798eba0 | Reading D365 field data from Excel |
| 10 | Feb 21 02:30 | `cd ... && uv run pytest --tb=short -q 2>&1` | dd1d5578 | Running full pytest suite |
| 11 | Feb 21 02:32 | `sleep 120` | 6a2e8a73 | Waiting before polling task |

**Analysis**: 5 of 11 (45%) are `sleep` commands used for polling intervals. 2 are `pytest` runs. 1 is `mkdir`, 1 is `grep`, 1 is Python data extraction. All are either blocking waits or read-only operations. The `mkdir` (#1) almost certainly completed before the session ended — it's a near-instant filesystem operation. The pytest runs (#4, #10) may have continued executing after the session terminated.

**Pattern**: Sessions are timing out or being manually stopped while waiting in `sleep` loops that poll long-running background operations. This is an expected consequence of the polling pattern used by version execution and quality gate checks.

**Work lost**: None. All commands are idempotent or read-only.

## TaskOutput (8 orphaned calls) — Subagent Results Lost

| # | Timestamp | Task ID | Timeout (s) | Session | Context |
|---|-----------|---------|-------------|---------|---------|
| 1 | Feb 6 10:21 | ac79826 | 180 | 240a0257 | C4-architecture documentation |
| 2 | Feb 6 10:21 | a5ce835 | 180 | 240a0257 | C4-architecture documentation |
| 3 | Feb 6 10:21 | a13cc1d | 180 | 240a0257 | C4-architecture documentation |
| 4 | Feb 8 21:18 | b54460b | 310 | 2b3751e4 | stoat-and-ferret design-v004 |
| 5 | Feb 9 21:08 | a73b721 | 300 | 52cf738c | Directory listing |
| 6 | Feb 12 10:54 | af956d2 | 300 | f9efa171 | User-interrupted session |
| 7 | Feb 16 14:47 | b44d0b9 | 600 | 03679aa7 | Unknown (null task) |
| 8 | Feb 20 10:24 | a602d28 | 60 | de65edd6 | analysis-pass-12 data mapping |

**Analysis**: All 8 are blocking `TaskOutput` calls waiting for subagent completion. Three (#1-3) are from a single C4-architecture session that launched 3 parallel documentation agents — this session alone accounts for 3 of 8 orphans. The timeouts range from 60s to 600s.

**Pattern**: The parent session terminates while blocking on TaskOutput. The subagent may have completed its work and written files independently. The parent just never received the result message. Session 240a0257 (c4-architecture) is the worst case: 3 parallel subagents all orphaned simultaneously, suggesting the session hit a hard timeout.

**Work lost**: The subagent's output (files written, commits made) is likely preserved. Only the result message back to the parent is lost, meaning the parent couldn't continue processing based on the subagent's findings.

## Task (7 orphaned calls) — Subagent Launches at Session End

| # | Timestamp | Description | Subagent Type | Session | Context |
|---|-----------|-------------|---------------|---------|---------|
| 1 | Feb 1 13:56 | Create Theme 3 feature documents | general-purpose | bd143c2d | auto-dev-mcp phase-two-design |
| 2 | Feb 13 08:44 | Count fields per Yocova object | Explore | 0bcb8587 | Yocova field analysis |
| 3 | Feb 13 10:23 | Explore Yocova Data directory | (Explore) | aaefbad2 | Salesforce CDC analysis |
| 4 | Feb 13 11:18 | Build Pass 6 generator script | (general-purpose) | aaefbad2 | Salesforce data mapping |
| 5 | Feb 13 22:09 | FFmpeg expressions research | general-purpose | 832998f8 | stoat-and-ferret v006 design |
| 6 | Feb 14 12:29 | Research WebFetch timeout config | general-purpose | ee7dda9e | auto-dev-mcp followup |
| 7 | Feb 14 12:29 | Research parallel tool streaming | general-purpose | ee7dda9e | auto-dev-mcp followup |

**Analysis**: These are all subagent launch calls. The parent session recorded the Task invocation but never got the result. In 2 cases (#6-7), both Tasks were launched simultaneously at the session's final timestamp (12:29), suggesting the session ended right after dispatching them. Session aaefbad2 has 2 orphaned Task calls plus an orphaned Edit, indicating a long-running session that was producing work right up to its termination.

**Pattern**: Task orphans occur when a parent session dispatches work just before terminating. The subagents themselves likely started and may have completed independently.

**Work lost**: Minimal — subagents run in separate processes. Their file writes and commits persist. The parent session just lost the ability to act on the subagent results.

## Read (6 orphaned calls) — No Risk

| # | Timestamp | File Being Read | Session |
|---|-----------|----------------|---------|
| 1 | Feb 14 12:06 | `gw-test/search-refactoring-2-sql/implementation.md` | 2a941a6d |
| 2 | Feb 17 18:23 | `analysis-pass-10-data-mapping/README.md` | 08f1f0da |
| 3 | Feb 19 18:47 | `.claude/.../tool-results/b47b18c.txt` | 9798eba0 |
| 4 | Feb 19 21:58 | `stoat-and-ferret/docs/C4-Documentation/c4-code-gui-stores.md` | agent-a2d8a40 |
| 5 | Feb 19 21:58 | `stoat-and-ferret/docs/C4-Documentation/c4-code-gui-components-tests.md` | agent-a2d8a40 |
| 6 | Feb 19 22:05 | `stoat-and-ferret/src/stoat_ferret/api/app.py` | agent-a0fa358 |

**Analysis**: All read-only. Two (#4-5) are from the same subagent reading C4 documentation files in parallel. One (#3) is reading a tool-results cache file. Three (#4-6) are stoat-and-ferret files.

**Work lost**: None. Read operations cannot cause data loss.

## Edit (1 orphaned call) — Highest Risk

| Timestamp | File | Session | Context |
|-----------|------|---------|---------|
| Feb 13 12:23 | `analysis-pass-7-data-mapping/generate_mapping.py` | aaefbad2 | Modifying `load_csv_data()` function |

**Analysis**: This edit was replacing the `load_csv_data()` function in a Python data mapping script. The edit operation uses string replacement — the `old_string` was the existing function body. Since `has_result = FALSE`, it's unclear whether the edit was applied to the filesystem before the session terminated. Claude Code's Edit tool typically writes to disk synchronously, so the edit likely completed even though the result message was never recorded. The session (aaefbad2) ran for 279 minutes with 1,056 tool calls before terminating — this was a very long, active session.

**Work lost**: Possibly none (edit likely applied to disk). If the edit failed silently, the `load_csv_data()` function would remain in its original state, which is a safe failure mode.

## Write (1 orphaned call) — Low Risk

| Timestamp | File | Session | Context |
|-----------|------|---------|---------|
| Jan 22 09:24 | `auto-dev-mcp/comms/state/explorations/retrospective-meta-analysis/README.md` | dbaca306 | Writing exploration documentation |

**Analysis**: Writing a README for a meta-analysis exploration. The content was a documentation summary, not source code. Similar to Edit, the Write tool writes synchronously to disk, so the file was likely created successfully.

**Work lost**: Possibly none. If the write failed, the exploration folder would be missing its README — an inconvenience but not data corruption.

## Grep (1 orphaned call) — No Risk

| Timestamp | Pattern | File | Session |
|-----------|---------|------|---------|
| Feb 3 13:52 | `class SupportCaseWrapper\|solution\|type` | `SupportCenter_Ctrl.cls` | b3acc3e9 |

**Analysis**: Read-only search in a Salesforce Apex class during a Yocova UAT audit session.

**Work lost**: None.

## Overall Trigger Categories

| Category | Count | % | Examples |
|----------|-------|---|---------|
| Sleep/wait polling | 5 | 14% | `sleep 90/120/240/300` |
| Subagent result polling | 8 | 23% | TaskOutput with 60-600s timeouts |
| Subagent launching | 7 | 20% | Task spawns at session end |
| Long-running commands | 3 | 9% | pytest, Python scripts |
| Read-only operations | 8 | 23% | Read(6), Grep(1), Bash grep(1) |
| File mutations | 2 | 6% | Edit(1), Write(1) |
| Directory creation | 1 | 3% | mkdir |
| Unclear | 1 | 3% | mkdir result missing |

The dominant theme: **sessions terminate during blocking operations** (sleep, TaskOutput, pytest). This is normal behavior for long-running sessions, not a bug.
