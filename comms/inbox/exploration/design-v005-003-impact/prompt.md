Read AGENTS.md first and follow all instructions there.

## Objective

Identify documentation, tooling, and process impacts that the planned v005 changes will produce for stoat-and-ferret, so they can be scoped as features during logical design rather than discovered post-implementation.

## Context

This is Phase 1 (Environment & Investigation) for stoat-and-ferret version v005. Tasks 001-002 gathered environment context and backlog details. This task reviews the planned changes and proactively identifies impacts before research investigation begins.

v005 scope: GUI shell + library browser + project manager. New frontend project, WebSocket support, application shell, library browser with thumbnails, project manager. Backlog items: BL-003, BL-028 through BL-036.

## Tasks

### 1. Read Phase 1 Outputs

Read backlog analysis outputs from the design artifact store:
- `comms/outbox/versions/design/v005/002-backlog/backlog-details.md` — backlog details and scope
- `comms/outbox/versions/design/v005/002-backlog/README.md` — overview

Identify which tools, documentation, and project areas will be affected by the planned changes.

### 2. Generic Impact Checks

#### 2.1 tool_help Currency

For each MCP tool whose parameters or behavior will change based on the planned backlog items:
- Check current `tool_help` content for the tool
- Identify if the planned changes will make the help text inaccurate
- Record each tool requiring a `tool_help` update

#### 2.2 Tool Description Accuracy

For each MCP tool affected by planned changes:
- Review the tool's description
- Flag descriptions that will become stale after implementation
- Record each tool requiring a description update

#### 2.3 Documentation Review

Identify which documentation files reference areas that will change:
- Search for references to changed tools, services, or APIs
- Check if any existing docs describe behavior that will change
- Record each document requiring review or update

### 3. Project-Specific Impact Checks

Read `docs/auto-dev/IMPACT_ASSESSMENT.md` if it exists. If not, document "No project-specific impact checks configured" and continue.

### 4. Classify Impacts

For each identified impact, classify it:
- **small**: Can be handled as a sub-task within an existing feature
- **substantial**: Requires its own feature in the version plan
- **cross-version**: Too large for this version; should be added to the backlog

### 5. Generate Work Items

For each impact, produce a work item description for the logical design phase:
- What needs to change
- Where the change is needed (file paths or areas)
- Estimated scope (small/substantial/cross-version)
- Which planned feature causes this impact

## Output Requirements

Save ALL outputs to BOTH locations:

**Primary (exploration output):** `comms/outbox/exploration/design-v005-003-impact/`
**Design artifact store:** `comms/outbox/versions/design/v005/003-impact-assessment/`

Write identical files to both locations.

### README.md (required)

First paragraph: Summary of impact assessment — total impacts found, breakdown by classification.

Then:
- **Generic Impacts**: Count and categories
- **Project-Specific Impacts**: Count and categories (or "N/A")
- **Work Items Generated**: Total count by classification
- **Recommendations**: How impacts should be incorporated into logical design

### impact-table.md

Complete impact assessment table:
| # | Area | Description | Classification | Resulting Work Item | Caused By |
|---|------|-------------|----------------|---------------------|-----------|

### impact-summary.md

Summary by classification (small, substantial, cross-version).

## Allowed MCP Tools

- `read_document`
- `request_clarification`
- `search_learnings`

## Guidelines

- ALL planned backlog items must be reviewed for impacts — do not skip any
- Generic checks run for every project; project-specific checks only when IMPACT_ASSESSMENT.md exists
- Missing IMPACT_ASSESSMENT.md is normal for new projects — not an error
- Be thorough but practical — only flag genuine impacts, not speculative ones
- Each impact must have a concrete work item, not just "review X"
- Keep each document under 200 lines
- Do NOT commit — the orchestrator handles commits after Phase 2

Do NOT commit or push — the calling prompt handles commits. Results folder: design-v005-003-impact.