# Task 002: Backlog Analysis and Retrospective Review

Read AGENTS.md first and follow all instructions there.

## Objective

Gather complete details for all backlog items in the version scope and learn from the previous version's retrospective.

## Context

This is Phase 1 (Environment & Investigation) for `${PROJECT}` version `${VERSION}`.

Task 001 identified the backlog item IDs. This task gathers full details.

## Tasks

### 1. Fetch Complete Backlog Items

For each backlog ID identified in Task 001:
- Call `get_backlog_item(project="${PROJECT}", item_id="BL-XXX")`
- Extract full details: title, description, acceptance criteria, priority, tags, notes
- Document any missing or incomplete backlog items

**MANDATORY SCOPE:** ALL backlog items listed in PLAN.md for this version are mandatory. No items may be deferred, descoped, or deprioritized. PLAN.md defines the version scope — it is not a suggestion. Read ALL backlog items and include ALL of them.

### 2. Quality Assessment for Selected Items

For each backlog item fetched in Task 1, assess quality across three dimensions.
This assessment is advisory — document findings but proceed even if refinement is not practical.

#### 2a. Description Depth
- Count approximate words in the item's description
- Consider reviewing items with descriptions under ~50 words — these may be too thin for design and could lead to scope invention
- If description is thin, use `update_backlog_item` to expand it with problem context, impact statement, and specific gaps, including `quality_assertion: {"quality_maintained": true, "change_justified": true}`

#### 2b. Acceptance Criteria Testability
- For each acceptance criterion, check for the presence of an action verb
- Consider reviewing criteria that are noun phrases without verbs (e.g., "User authentication" vs. "User can authenticate with email and password") — these may not be testable
- If AC is non-testable, use `update_backlog_item` to rewrite with specific, verifiable actions, including `quality_assertion`

#### 2c. Use Case Authenticity
- Check use_case text against known formulaic patterns:
  - "This feature addresses: {title}. It improves the system by resolving the described requirement."
  - "Implementing {title} improves the {area} by providing better {noun}."
- Consider reviewing items with formulaic use cases — they add no information beyond the title
- If formulaic, use `update_backlog_item` to write an authentic user scenario describing who benefits, what they do, and why it matters, including `quality_assertion`

#### 2d. Assessment Summary
Document the assessment results for each item in the task output:
- Item ID, title
- Description depth: word count, flagged (yes/no)
- AC testability: flagged criteria count
- Use case authenticity: formulaic (yes/no)
- Refinement action taken (if any)

### 3. Identify Previous Version

Call `list_versions(project="${PROJECT}")` to find the most recent completed version before `${VERSION}`.

### 4. Review Previous Retrospective

Locate and read the previous version's retrospective:
- Check `docs/versions/vXXX/README.md`
- Check `comms/outbox/vXXX/retrospective.md`

Extract insights relevant to current design:
- Learnings that apply to `${VERSION}` scope
- Patterns that worked well
- Tech debt to address
- Recommendations for future work

### 5. Search Project Learnings

Run `search_learnings(project="${PROJECT}", tags=["design", "architecture"])` to find relevant documented learnings.

Review any learnings that might inform the design approach for `${VERSION}`.

## Output Requirements

Save outputs to `comms/outbox/versions/design/${VERSION}/002-backlog/`:

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
- Complexity assessment (based on description, not title)

### retrospective-insights.md

Synthesized insights from previous version:
- What worked well (to continue)
- What didn't work (to avoid)
- Tech debt addressed vs deferred
- Architectural decisions to inform current version

### learnings-summary.md

Relevant learnings from project learning repository:
- Learning ID and title
- Summary of insight
- Applicability to current version

## Allowed MCP Tools

- `get_backlog_item`
- `update_backlog_item`
- `list_versions`
- `read_document`
- `search_learnings`
- `list_learnings`
- `get_learning`

## Guidelines

- ALL backlog items from PLAN.md are MANDATORY — no deferrals, no descoping
- Quote actual backlog text when documenting items
- Distinguish title complexity from implementation complexity
- Connect retrospective insights to current backlog items where possible
- Keep documents under 200 lines each
- Do NOT commit — the master prompt handles commits after Phase 2
