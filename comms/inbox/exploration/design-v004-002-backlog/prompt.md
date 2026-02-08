You are performing Task 002: Backlog Analysis and Retrospective Review for stoat-and-ferret version v004.

Read AGENTS.md first and follow all instructions there.

PROJECT=stoat-and-ferret
VERSION=v004

## Objective

Gather complete details for all backlog items in the version scope and learn from the previous version's retrospective.

## Context

Task 001 identified the backlog item IDs. This task gathers full details.

The backlog items for v004 are:
- New Items: BL-020, BL-021, BL-022, BL-023, BL-024, BL-025, BL-026, BL-027
- Existing/Retagged Items: BL-009, BL-010, BL-012, BL-014, BL-016

ALL 13 items are MANDATORY. No items may be deferred, descoped, or deprioritized.

## Tasks

### 1. Fetch Complete Backlog Items

For each backlog ID listed above:
- Call `get_backlog_item(project="stoat-and-ferret", item_id="BL-XXX")`
- Extract full details: title, description, acceptance criteria, priority, tags, notes
- Document any missing or incomplete backlog items

### 2. Quality Assessment for Each Item

For each backlog item, assess quality across three dimensions:

#### 2a. Description Depth
- Count approximate words in the description
- Flag items with descriptions under ~50 words as potentially too thin
- If thin, use `update_backlog_item` to expand with problem context, impact statement, and specific gaps

#### 2b. Acceptance Criteria Testability
- Check for action verbs in each criterion
- Flag noun phrases without verbs as potentially non-testable
- If non-testable, use `update_backlog_item` to rewrite with specific, verifiable actions

#### 2c. Use Case Authenticity
- Check for formulaic patterns like "This feature addresses: {title}. It improves the system by..."
- Flag formulaic use cases
- If formulaic, use `update_backlog_item` to write authentic user scenarios

#### 2d. Assessment Summary
Document results for each item as a table.

### 3. Identify Previous Version

Call `list_versions(project="stoat-and-ferret")` to find the most recent completed version before v004.

### 4. Review Previous Retrospective

Locate and read the previous version's retrospective:
- Check `docs/versions/vXXX/README.md`
- Check `comms/outbox/vXXX/retrospective.md`
- Extract insights relevant to v004 scope

### 5. Search Project Learnings

Run `search_learnings(project="stoat-and-ferret", tags=["design", "architecture"])` to find relevant documented learnings.

## Output Requirements

Create findings in comms/outbox/exploration/design-v004-002-backlog/:

### README.md (required)

First paragraph: Summary of backlog scope and key insights from retrospective.

Then:
- **Backlog Overview**: Count of items, priority distribution
- **Previous Version**: Version number, retrospective location
- **Key Learnings**: Top insights applicable to current version
- **Tech Debt**: Any debt items to address
- **Missing Items**: Any referenced backlog items not found

### backlog-details.md

For each backlog item, include:
- ID, Title, Priority
- Full description (quoted)
- Acceptance criteria (listed)
- Tags and notes
- Quality assessment results

### retrospective-insights.md

Synthesized insights from previous version:
- What worked well (to continue)
- What didn't work (to avoid)
- Tech debt addressed vs deferred
- Architectural decisions to inform current version

### learnings-summary.md

Relevant learnings from project learning repository.

## Guidelines

- ALL backlog items from PLAN.md are MANDATORY — no deferrals, no descoping
- Quote actual backlog text when documenting items
- Keep documents under 200 lines each

## When Complete

After writing all output files to comms/outbox/exploration/design-v004-002-backlog/, also COPY the README.md, backlog-details.md, retrospective-insights.md, and learnings-summary.md to comms/outbox/versions/design/v004/002-backlog/ so they are in the design artifact store.

git add comms/outbox/exploration/design-v004-002-backlog/
git commit -m "exploration: design-v004-002-backlog - backlog analysis complete"
