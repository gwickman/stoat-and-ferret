# Task 004: Research and Investigation

Read AGENTS.md first and follow all instructions there.

## Objective

Research unknowns, investigate prior art, and gather evidence for design decisions that affect version STRUCTURE (not implementation details Claude Code can figure out).

## Context

This is Phase 1 (Environment & Investigation) for `${PROJECT}` version `${VERSION}`.

Tasks 001-003 gathered context. This task resolves unknowns before proposing solutions.

## Tasks

### 1. Identify Research Questions

Based on backlog items from Task 002 (read from `comms/outbox/versions/design/${VERSION}/002-backlog/`), identify:
- Technologies or libraries requiring investigation
- Unclear areas of existing codebase
- Patterns needed but not yet understood
- Configuration values requiring evidence (timeouts, limits, etc.)
- Integration points with existing systems

Create a list of specific research questions.

### 2. Codebase Investigation

For questions about existing code:
- Use `request_clarification` to search for patterns, classes, or files
- Read relevant source files to understand current implementation
- Document findings with file paths and line references

### 3. Verify Referenced Learnings

If any backlog items, previous version retrospectives, or research findings reference learnings (LRN-XXX):

1. Read the learning: `get_learning(learning_id="LRN-XXX", project="${PROJECT}")`
2. Verify the condition it describes still exists in the codebase (quick check — run relevant command or read relevant file)
3. If the condition has been fixed or changed since the learning was created, mark the learning as **STALE** and note that design decisions should NOT rely on it
4. If the condition persists, mark as **VERIFIED** and incorporate into design

Document all learning verifications in the research output with a table:

| Learning | Status | Evidence |
|----------|--------|----------|
| LRN-031 | STALE | All 7 test failures resolved in v048 commits |
| LRN-024 | VERIFIED | Pattern still present in version_design.py |

### 4. External Research

For questions about external libraries, patterns, or best practices:

**DeepWiki Research:**
- Use `ask_question` from mcp__deepwiki to query relevant repositories
- Document sources and specific implementation details found

**Web Search:**
- Use web search for official documentation, guides, GitHub issues
- Priority: Official docs > Library tests > GitHub issues
- Document URLs and relevant excerpts
- Never use WebFetch on URLs not provided by the user or found via web search. Do not hallucinate or construct URLs.
- Always pre-check URLs with curl --max-time 10 before WebFetch. This catches unresponsive hosts before they hang the session.
- If curl times out, skip WebFetch for that URL. Do not retry — move on and note the URL was unreachable.

### 5. Sub-Explorations for Complex Investigation

If investigation is complex or can be parallelized:
- You MAY spawn sub-explorations using `start_exploration`
- Each sub-exploration should have a focused question
- Monitor with `get_exploration_status` and retrieve results
- Integrate findings into this task's output

### 6. Evidence Gathering for Concrete Values

For any concrete values needed (timeouts, limits, thresholds):
- Query existing codebase for current values
- Check configuration files
- If not determinable pre-implementation, mark as "TBD - requires runtime testing"
- NEVER guess or use "typical" values without evidence

#### 6b. Historical Execution Evidence

When researching timing estimates, complexity assessments, or tool usage patterns, query session analytics for empirical data from past implementations:

```python
# How long did similar features take in past versions?
query_cli_sessions(
    project="${PROJECT}",
    mode="analytics",
    query_type="session_list",
    scope="project",
    intent='{"investigating": "Historical session durations for features similar to planned backlog items", "expected": "Session summaries with timing data to calibrate effort estimates"}'
)

# Which tools had issues in recent versions? Useful for risk assessment.
query_cli_sessions(
    project="${PROJECT}",
    mode="analytics",
    query_type="tool_usage",
    scope="project",
    since_days=60,
    intent='{"investigating": "Tool reliability data to identify risks for planned features", "expected": "Tool call success rates and latency to identify fragile tools"}'
)
```

Use session analytics to:
- **Calibrate effort estimates**: Check actual session durations for past features of similar complexity
- **Identify tool reliability risks**: If a tool the planned features depend on has high error rates, flag it as a risk
- **Verify assumptions**: If research assumes a particular workflow is fast/reliable, check session data for evidence

Mark findings sourced from session analytics with the tag "Source: query_cli_sessions" in evidence-log.md.

### 7. Impact Analysis

Document:
- **Dependencies**: What existing code/tools/configs will change?
- **Breaking changes**: Will existing workflows or APIs break?
- **Test impact**: What tests need creation or update?
- **Documentation**: What docs require update after implementation?

### 8. State & Persistence Analysis

For each feature that introduces or modifies persistent state (files, databases, config stores), analyse:

1. **Storage Location**: Where does the data live? Identify the file path, database, or config store. Verify the storage path API exists via `request_clarification` or codebase search — do not assume an API exists without evidence.
2. **Multi-Project Implications**: Does the storage location work correctly when multiple projects are registered? Is data isolated per project or shared globally?
3. **Data Classification**: Is the data user-generated, system-managed, or cached/derivable? What is the impact of data loss?
4. **Lifecycle**: When is data created, updated, and deleted? Are there cleanup or migration requirements?
5. **Path Stability**: Will the storage path remain valid across server restarts, project renames, and directory moves?

If no features introduce persistent state, note "No persistent state introduced" in the README and skip the `persistence-analysis.md` output.

## Output Requirements

Save outputs to `comms/outbox/versions/design/${VERSION}/004-research/`:

### README.md (required)

First paragraph: Summary of research scope and key findings.

Then:
- **Research Questions**: List of questions investigated
- **Findings Summary**: High-level results
- **Unresolved Questions**: Items that cannot be resolved pre-implementation
- **Recommendations**: Design direction based on research

### codebase-patterns.md

Findings from codebase investigation:
- Existing patterns found
- File paths and key classes/functions
- Code snippets showing relevant implementations

### external-research.md

Findings from DeepWiki and web research:
- Libraries/tools evaluated
- Patterns and best practices found
- Sources cited (with URLs or repo names)
- Recommended approaches with rationale

### evidence-log.md

For all concrete values needed:
```
## [Parameter Name]
- **Value**: [concrete value]
- **Source**: [where evidence came from]
- **Data**: [actual measurements or findings]
- **Rationale**: [why this value]
```

### impact-analysis.md

Analysis of implementation impact:
- Dependencies (code/tools/configs affected)
- Breaking changes identified
- Test infrastructure needs
- Documentation updates required

### persistence-analysis.md (conditional)

Required only when features introduce or modify persistent state. For each feature with persistence:
- Storage location and verified API path
- Multi-project isolation assessment
- Data classification and loss impact
- Lifecycle (create/update/delete) and migration needs
- Path stability across restarts and renames

## Allowed MCP Tools

- `request_clarification`
- `read_document`
- `start_exploration` (for sub-investigations)
- `get_exploration_status`
- `get_exploration_result`
- `list_explorations`
- `get_learning`
- `search_learnings`
- `get_backlog_item`
- `list_product_requests`
- `get_product_request`
- `add_product_request`
- `update_product_request`
- `upvote_item`
- `query_cli_sessions`

Plus DeepWiki tools:
- `mcp__deepwiki__ask_question`
- `mcp__deepwiki__read_wiki_structure`
- `mcp__deepwiki__read_wiki_contents`

## Guidelines

- ALL backlog items from PLAN.md are MANDATORY — research must cover all of them, no deferrals
- Research is the designer's responsibility — resolve all queryable unknowns NOW
- Document sources for all findings (file paths, URLs, repo names)
- Mark items as "TBD - requires [X]" only if truly not determinable pre-implementation
- Never defer research to Claude Code with phrases like "Check if..." or "Investigate..."
- Sub-explorations are encouraged for parallel investigation work
- Keep each document under 200 lines
- Do NOT commit — the master prompt handles commits after Phase 2
