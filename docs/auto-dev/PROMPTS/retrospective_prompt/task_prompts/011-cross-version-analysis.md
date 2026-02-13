# Task 011: Cross-Version Analysis

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective

Analyze the last 5 versions for recurring patterns, efficiency trends, and systemic issues. Produce actionable Product Requests for findings that warrant attention.

## Context

Post-version retrospective for `${PROJECT}` version `${VERSION}`. This task runs at versions divisible by 5 (v050, v055, v060, v065, ...) and provides a cross-cutting view that single-version retrospectives cannot.

## Tasks

### 1. Determine Version Range

Calculate the 5 most recent versions ending with `${VERSION}`.

For example, if `${VERSION}` is `v060`, the range is: v056, v057, v058, v059, v060.

Store the range for use in subsequent steps.

### 2. Load Project-Specific Configuration

Read `docs/auto-dev/CROSS_VERSION_RETRO.md` if it exists.

- If present: extract the project-specific analysis checks defined in that file. These checks supplement the generic analysis in Step 4.
- If absent: proceed with generic analysis checks only. Do not fail.

### 3. Extract Retrospective Data

For each version in the range, read the following files from `comms/outbox/versions/retrospective/{version}/`:

| File | Folder | Content |
|------|--------|---------|
| `quality-report.md` | `004-quality-gates/` | Quality gate metrics and results |
| `learnings-detail.md` | `006-learnings/` | Extracted learnings from that version |
| `backlog-report.md` | `003-backlog-verification/` | Backlog coverage and verification |
| `final-summary.md` | `010-finalization/` | Overall version summary |

**Graceful degradation:** If a version's retrospective data is missing or incomplete, skip that version and note it in the summary rather than failing the analysis. Record which versions had complete data and which were skipped.

### 4. Cross-Version Analysis

Run the following generic analysis checks across the collected data:

#### 4a. Recurring Bugs and Failures

- Identify bug types or test failures that appear in 2+ versions
- Look for patterns in quality gate failures (ruff, mypy, pytest)
- Flag any issue category that persists across the version range

#### 4b. Persistent Quality Gaps

- Compare quality-gaps.md content across versions for repeated themes
- Identify gap categories that were documented but never resolved
- Check if quality gate pass rates are trending up, down, or flat

#### 4c. Efficiency Trends

- Compare feature completion rates across versions
- Look for increasing iteration counts (features requiring multiple fix cycles)
- Identify themes or feature types that consistently take longer

#### 4d. Log Patterns

- Use `get_server_logs` MCP tool with `source="cli"` to check for patterns in execution logs
- Identify recurring error patterns or investigation difficulties
- Flag excessive log retrieval indicating debugging struggles

#### 4e. Backlog Hygiene

- Use `list_backlog_items` MCP tool with `status="open"` to check for stale items
- Identify items open for 3+ versions without being scheduled
- Check for priority drift (items repeatedly deferred)
- Assess scheduled-vs-completed ratios from version summaries

#### 4f. Learning Effectiveness

- Use `list_learnings` MCP tool to retrieve all active learnings
- Cross-reference learnings against recurring issues: if an issue recurs after a learning was captured for it, the learning may be ineffective
- Identify learnings older than 5 versions that may need review

#### 4g. Project-Specific Checks

If `CROSS_VERSION_RETRO.md` was loaded in Step 2, execute each check defined there using the data sources, thresholds, and analysis steps specified. Follow the output instructions for each check.

### 5. Generate Product Requests

For each actionable finding from Steps 4a-4g, create a Product Request via the `add_product_request` MCP tool:

```python
add_product_request(
    project="${PROJECT}",
    title="<concise finding title>",
    description="<detailed description including evidence, affected versions, and suggested action>",
    tags=["cross-version-retro", "<category>"],
    priority="<medium|high based on severity and recurrence>",
    quality_assertion="Finding supported by data from {N} versions in range {VERSION_RANGE}"
)
```

Priority guidelines:
- **high**: Issue recurs in 3+ versions or shows worsening trend
- **medium**: Issue appears in 2 versions or represents a missed opportunity

Do NOT create Product Requests for one-off issues confined to a single version — those belong in single-version retrospectives.

### 6. Output Summary

Write the analysis summary to the output location specified below.

## Output Requirements

Save outputs to `comms/outbox/versions/retrospective/${VERSION}/011-cross-version/`:

### README.md (required)

First paragraph: Cross-version analysis summary (versions analyzed, findings count, Product Requests created).

Then:
- **Version Range**: Which versions were analyzed, which were skipped
- **Findings Summary**: Table of findings by category with severity
- **Product Requests Created**: List with PR-xxx IDs, titles, and priorities
- **Data Quality**: Notes on completeness of retrospective data across versions

### cross-version-report.md

Detailed analysis report:

```markdown
# Cross-Version Analysis: ${VERSION_RANGE}

## Data Coverage
| Version | Quality Report | Learnings | Backlog Report | Final Summary |
|---------|---------------|-----------|----------------|---------------|
| vXXX    | Present/Missing | ... | ... | ... |

## Generic Analysis

### Recurring Bugs and Failures
[Findings or "No recurring bugs detected"]

### Persistent Quality Gaps
[Findings or "No persistent gaps detected"]

### Efficiency Trends
[Findings or "No concerning trends detected"]

### Log Patterns
[Findings or "No problematic patterns detected"]

### Backlog Hygiene
[Findings or "Backlog health within thresholds"]

### Learning Effectiveness
[Findings or "Learnings effective — no recurring issues detected"]

## Project-Specific Analysis
[Results from CROSS_VERSION_RETRO.md checks, or "No project-specific config found"]

## Product Requests Created
| ID | Title | Priority | Category |
|----|-------|----------|----------|
| PR-xxx | ... | ... | ... |
```

## Allowed MCP Tools

- `read_document`
- `get_server_logs`
- `list_backlog_items`
- `list_learnings`
- `search_learnings`
- `add_product_request`

## Guidelines

- Focus on patterns that span multiple versions — single-version issues are out of scope
- Be conservative with Product Request creation: only create requests for well-evidenced, actionable findings
- Include version numbers and specific evidence in every finding
- Do NOT attempt to fix issues — only report and create Product Requests
- Do NOT commit — the master prompt handles commits
