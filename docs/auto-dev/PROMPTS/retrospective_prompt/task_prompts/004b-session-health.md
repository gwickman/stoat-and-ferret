# Task 004b: Session Health Check

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective

Detect CLI session health problems from version execution using 5 detection patterns against the session analytics database. Flag findings with severity classifications and propose remediation via product requests.

## Context

Post-version retrospective for `${PROJECT}` version `${VERSION}`.

This task runs between Task 004 (Quality Gates) and Task 005 (Architecture Alignment) in Phase 1: Verification. It uses the `query_cli_sessions` infrastructure (SQLite storage, JSONL ingestion, troubleshoot/sql modes) delivered in v066.

> **Initial thresholds — calibrate after first retrospective cycle.** The detection thresholds below are provisional and based on limited empirical data. Adjust after observing real-world distributions.

## Tasks

### 1. Verify Session Data Availability

Before running detection patterns, confirm session data exists for this version:

```
query_cli_sessions(
    project="${PROJECT}",
    mode="analytics",
    query_type="summary"
)
```

If no session data is available, document "No session data available for ${VERSION}" and skip to output.

### 2. Run Detection Patterns

Execute each of the 5 detection patterns below. Record all findings.

---

#### Pattern 1: Hung WebFetch Calls

**Severity:** HIGH (zero tolerance)
**Threshold:** Any orphaned WebFetch tool_use with has_result=FALSE in a completed session
**Mode:** troubleshoot
**Rationale:** Orphaned WebFetch calls indicate hung HTTP requests with no built-in timeout. Even one represents wasted execution time and potentially incomplete work.

```
query_cli_sessions(
    project="${PROJECT}",
    mode="troubleshoot",
    query_type="orphaned_tools"
)
```

Filter results to WebFetch tool calls only. Any match = HIGH finding.

---

#### Pattern 2: Tool Authorization Retry Waste

**Severity:** MEDIUM
**Threshold:** Same tool denied 3+ times in one session
**Mode:** sql (custom query)
**Rationale:** Each unauthorized retry wastes ~1 API round-trip. 3+ retries indicates the agent is stuck in a loop rather than adapting.

```
query_cli_sessions(
    project="${PROJECT}",
    mode="sql",
    sql="""
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
    """
)
```

Any row = MEDIUM finding. Report session_id, tool_name, and denial_count.

---

#### Pattern 3: Orphaned Tool Calls (Non-WebFetch)

**Severity:** HIGH (zero tolerance)
**Threshold:** Any tool_use without tool_result in a completed session (excluding WebFetch, which is Pattern 1)
**Mode:** troubleshoot
**Rationale:** Orphaned tool calls indicate crashes, hangs, or incomplete execution.

```
query_cli_sessions(
    project="${PROJECT}",
    mode="troubleshoot",
    query_type="orphaned_tools"
)
```

Filter results to exclude WebFetch tool calls. Any remaining match = HIGH finding.

---

#### Pattern 4: Excessive Context Compaction

**Severity:** MEDIUM
**Threshold:** 3+ compaction events per session
**Mode:** sql (custom query)
**Rationale:** Excessive compaction suggests the session is running out of context repeatedly, which may cause loss of implementation context and partial work.

```
query_cli_sessions(
    project="${PROJECT}",
    mode="sql",
    sql="""
        SELECT
            ce.session_id,
            COUNT(*) as compaction_count
        FROM compaction_events ce
        GROUP BY ce.session_id
        HAVING COUNT(*) >= 3
        ORDER BY compaction_count DESC
    """
)
```

Any row = MEDIUM finding. Report session_id and compaction_count.

---

#### Pattern 5: Sub-Agent Failure Cascades

**Severity:** HIGH (errors + long duration), MEDIUM (errors or long duration alone)
**Threshold:** Sub-agents with duration >30 minutes combined with errors or orphaned tools
**Mode:** sql (custom query)
**Rationale:** Sub-agents should complete focused tasks quickly. >30min combined with errors or orphaned tools indicates a cascade failure where the sub-agent is stuck.

```
query_cli_sessions(
    project="${PROJECT}",
    mode="sql",
    sql="""
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
    """
)
```

Classify: HIGH if both error_count > 0 AND orphaned_count > 0; MEDIUM otherwise.

### 3. Compile Findings

For each detection pattern, record:
- Pattern name and number
- Severity level
- Number of matches found (0 = clean)
- Details of each match (session_id, tool_name, counts, etc.)

### 4. Propose Remediation via Product Requests

For any HIGH severity finding, create a product request:

```
add_product_request(
    project="${PROJECT}",
    title="Session health: <brief description of finding>",
    description="<Pattern number, severity, evidence, suggested remediation>",
    tags=["session-health", "retrospective"],
    quality_assertion='{"problem_structured": true, "no_formulaic": true}'
)
```

**Use `add_product_request`, NOT `add_backlog_item`.** Findings from session health checks are observations that need triage before becoming actionable backlog items.

For MEDIUM severity findings, document them in the output but do not create product requests unless the count or pattern suggests a systemic issue.

## Output Requirements

Save to `comms/outbox/versions/retrospective/${VERSION}/004b-session-health/`:

### README.md (required)
- First paragraph: Session health summary (X patterns checked, Y findings at HIGH, Z findings at MEDIUM, or "all clean")
- Detection Results table (pattern name, severity, threshold, matches found)
- HIGH Findings (details of each)
- MEDIUM Findings (details of each)
- Product Requests Created (list with IDs)
- Data Availability Notes (any caveats about missing data)

### findings-detail.md
- For each pattern: full query used, raw results, classification reasoning
- Session IDs and tool names for traceability

## Allowed MCP Tools

query_cli_sessions, add_product_request, list_product_requests, get_product_request, update_product_request, upvote_item, read_document

## Guidelines
- Run all 5 detection patterns even if earlier ones find nothing
- Do NOT create backlog items — use `add_product_request` for all proposed remediation
- Do NOT modify session data or analytics infrastructure
- SQL queries use the existing 10-second timeout via sql mode
- Do NOT commit — the master prompt handles commits
