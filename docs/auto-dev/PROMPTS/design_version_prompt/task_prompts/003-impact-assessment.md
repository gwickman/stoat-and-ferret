# Task 003: Impact Assessment

Read AGENTS.md first and follow all instructions there.

## Objective

Identify documentation, tooling, and process impacts that the planned version changes will produce, so they can be scoped as features during logical design rather than discovered post-implementation.

## Context

This is Phase 1 (Environment & Investigation) for `${PROJECT}` version `${VERSION}`.

Tasks 001-002 gathered environment context and backlog details. This task reviews the planned changes and proactively identifies impacts before research investigation begins.

## Tasks

### 1. Read Phase 1 Outputs

Read backlog analysis outputs from the design artifact store:
- `comms/outbox/versions/design/${VERSION}/002-backlog/` — backlog details and scope

Identify which tools, documentation, and project areas will be affected by the planned changes.

### 2. Generic Impact Checks

These checks apply to all projects regardless of project-specific configuration.

#### 2.1 tool_help Currency

For each MCP tool whose parameters or behavior will change based on the planned backlog items:
- Check current `tool_help` content for the tool
- Identify if the planned changes will make the help text inaccurate
- Record each tool requiring a `tool_help` update

#### 2.2 Tool Description Accuracy

For each MCP tool affected by planned changes:
- Review the tool's description (the short text shown in tool listings)
- Flag descriptions that will become stale after implementation
- Record each tool requiring a description update

#### 2.3 Documentation Review

Identify which documentation files reference areas that will change:
- Search for references to changed tools, services, or APIs
- Check if any existing docs describe behavior that will change
- Record each document requiring review or update

### 3. Project-Specific Impact Checks

Read `docs/auto-dev/IMPACT_ASSESSMENT.md` if it exists for the current project.

```python
# Attempt to read project-specific impact checks
# If the file does not exist, skip this section — no error
# If the file exists, execute each check category defined there
```

If the file does not exist, document "No project-specific impact checks configured" and continue.

If the file exists, execute each check category defined there and record findings.

### 4. Classify Impacts

For each identified impact, classify it:

- **small**: Can be handled as a sub-task within an existing feature (e.g., update a help string, fix a doc reference)
- **substantial**: Requires its own feature in the version plan (e.g., rewrite a tool reference section, update multiple setup guides)
- **cross-version**: Too large for this version; should be added to the backlog for a future version (e.g., major documentation restructuring)

### 5. Generate Work Items

For each impact, produce a work item description that can feed into the logical design phase (Task 005):
- What needs to change
- Where the change is needed (file paths or areas)
- Estimated scope (small/substantial/cross-version)
- Which planned feature causes this impact

## Output Requirements

Save outputs to `comms/outbox/versions/design/${VERSION}/003-impact-assessment/`:

### README.md (required)

First paragraph: Summary of impact assessment — total impacts found, breakdown by classification.

Then:
- **Generic Impacts**: Count and categories
- **Project-Specific Impacts**: Count and categories (or "N/A — no IMPACT_ASSESSMENT.md")
- **Work Items Generated**: Total count by classification
- **Recommendations**: How impacts should be incorporated into logical design

### impact-table.md

Complete impact assessment table:

```markdown
| # | Area | Description | Classification | Resulting Work Item | Caused By |
|---|------|-------------|----------------|---------------------|-----------|
| 1 | tool_help | update_backlog_item help text outdated | small | Update tool_help for update_backlog_item | BL-XXX |
| 2 | TOOL_REFERENCE.md | New parameter not documented | substantial | Add feature for TOOL_REFERENCE.md update | BL-YYY |
```

### impact-summary.md

Summary by classification:

```markdown
## Small Impacts (sub-task scope)
- [list of small impacts with owning feature]

## Substantial Impacts (feature scope)
- [list of substantial impacts requiring own feature]

## Cross-Version Impacts (backlog scope)
- [list of cross-version impacts for future planning]
```

## Allowed MCP Tools

- `read_document`
- `request_clarification`
- `tool_help`
- `search_learnings`
- `list_product_requests`
- `get_product_request`
- `add_product_request`
- `update_product_request`
- `upvote_item`

## Guidelines

- ALL planned backlog items must be reviewed for impacts — do not skip any
- Generic checks run for every project; project-specific checks only when IMPACT_ASSESSMENT.md exists
- Missing IMPACT_ASSESSMENT.md is normal for new projects — not an error
- Be thorough but practical — only flag genuine impacts, not speculative ones
- Verify each impact by reading the actual tool_help output or document content that would be affected — do not flag impacts based on assumed file contents
- Each impact must have a concrete work item, not just "review X"
- Keep each document under 200 lines
- Do NOT commit — the master prompt handles commits after Phase 2
