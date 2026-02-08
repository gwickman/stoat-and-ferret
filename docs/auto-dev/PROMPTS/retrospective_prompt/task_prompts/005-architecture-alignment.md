# Task 005: Architecture Alignment

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective

Check whether changes implemented in `${VERSION}` have caused drift from documented architecture. Update or create backlog items only if NEW drift is detected.

## Context

Post-version retrospective for `${PROJECT}` version `${VERSION}`. Architecture documentation (C4 diagrams, ARCHITECTURE.md) may not reflect changes made during this version. This task detects drift without requiring immediate remediation — it creates backlog items for future C4 regeneration.

## Tasks

### 1. Check for Existing Open Architecture Backlog Items

Search for open backlog items related to architecture or C4:

```python
list_backlog_items(project="${PROJECT}", status="open", search="C4")
list_backlog_items(project="${PROJECT}", status="open", search="architecture")
list_backlog_items(project="${PROJECT}", status="open", tags=["architecture"])
list_backlog_items(project="${PROJECT}", status="open", tags=["c4"])
```

If an open item exists, read its description and notes to understand what drift is already documented.

### 2. Gather Version Changes

Read the version retrospective and theme retrospectives to understand what changed:
- `comms/outbox/versions/execution/${VERSION}/retrospective.md`
- All `comms/outbox/versions/execution/${VERSION}/<theme>/retrospective.md`

Extract:
- New services, handlers, or components added
- Existing components significantly modified
- Components removed or deprecated
- New external dependencies or integrations

### 3. Check Current Architecture Documentation

Read architecture documentation if it exists:
- `docs/C4-Documentation/README.md` (check timestamp)
- `docs/C4-Documentation/c4-context.md`
- `docs/C4-Documentation/c4-container.md`
- `docs/ARCHITECTURE.md`

Note: Some or all of these may not exist. Document what exists and what doesn't.

### 4. Detect Drift

Compare the changes from step 2 against the documentation from step 3:
- Are new components documented?
- Are removed components still listed?
- Do data flows reflect the current implementation?
- Are external dependencies current?

### 5. Take Action Based on Findings

**If NO new drift detected** (changes align with docs, or no docs exist to drift from):
- Document "no additional architecture drift detected" and move on

**If NEW drift detected AND an existing open architecture backlog item exists**:
- Add a note to the existing item via `update_backlog_item`:
  ```python
  update_backlog_item(
      project="${PROJECT}",
      item_id="BL-XXX",
      notes="Additional drift from ${VERSION}: [description of new drift]"
  )
  ```

**If NEW drift detected AND no existing open architecture backlog item**:
- Create a new backlog item:
  ```python
  add_backlog_item(
      project="${PROJECT}",
      title="Update C4/architecture documentation for ${VERSION} changes",
      priority="P2",
      description="Architecture drift detected during ${VERSION} retrospective:\n- [list of drift items]",
      tags=["architecture", "c4", "documentation"],
      quality_assertion='{"problem_structured": true, "ac_testable": true, "no_formulaic": true, "duplicate_checked": true}'
  )
  ```

## Output Requirements

Save outputs to `comms/outbox/versions/retrospective/${VERSION}/005-architecture/`:

### README.md (required)

First paragraph: Architecture alignment summary (aligned / drift detected / no docs to compare).

Then:
- **Existing Open Items**: List of open architecture backlog items found (or "none")
- **Changes in ${VERSION}**: Summary of architectural changes made
- **Documentation Status**: What architecture docs exist and their currency
- **Drift Assessment**: Specific drift items found (or "no additional drift")
- **Action Taken**: What was done (nothing / updated existing item / created new item)

## Allowed MCP Tools

- `list_backlog_items`
- `get_backlog_item`
- `update_backlog_item`
- `add_backlog_item`
- `read_document`

## Guidelines

- Do NOT regenerate C4 documentation — only detect drift and create/update backlog items
- Do NOT duplicate drift already documented in an existing open backlog item
- If no architecture documentation exists at all, note this and create a backlog item for initial generation
- Do NOT commit — the master prompt handles commits
