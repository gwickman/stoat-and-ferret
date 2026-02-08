# Task 003: Backlog Verification

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective

Cross-reference backlog items referenced in feature requirements with their actual status, and complete any still-open items that were implemented.

## Context

Post-version retrospective for `${PROJECT}` version `${VERSION}`. Completed features do NOT automatically close backlog items. This task ensures all implemented backlog items are marked complete.

## Tasks

### 1. Scan Feature Requirements for BL-XXX References

Read `comms/inbox/versions/execution/${VERSION}/THEME_INDEX.md` to get the version structure.

For each feature, read:
- `comms/inbox/versions/execution/${VERSION}/<theme>/<feature>/requirements.md`

Extract all `BL-XXX` references from each requirements file.

### 2. Check Backlog Item Status

For each unique BL-XXX reference found, call:
```python
get_backlog_item(project="${PROJECT}", item_id="BL-XXX")
```

Record: item ID, title, current status, referencing feature.

### 3. Complete Open Backlog Items

For each backlog item that is still "open" but was referenced by a completed feature:

Execute immediately (auto-approved):
```python
complete_backlog_item(
    project="${PROJECT}",
    item_id="BL-XXX",
    version="${VERSION}",
    theme="<theme-name>"
)
```

Record: item ID, action taken, result.

### 4. Check for Orphaned Items

Call `list_backlog_items(project="${PROJECT}", status="open")` and check if any open items reference `${VERSION}` in their description or notes but were not found in requirements files.

Document any orphaned items found.

## Output Requirements

Save outputs to `comms/outbox/versions/retrospective/${VERSION}/003-backlog/`:

### README.md (required)

First paragraph: Backlog verification summary (X items checked, Y completed, Z already complete).

Then:
- **Items Verified**: Count of BL-XXX references found
- **Items Completed**: List of items closed by this task
- **Already Complete**: List of items that were already closed
- **Orphaned Items**: Any open items referencing this version not in requirements
- **Issues**: Any items that could not be completed (with reason)

### backlog-report.md

Detailed table:

```markdown
| Backlog Item | Title | Feature | Status Before | Action | Status After |
|--------------|-------|---------|---------------|--------|--------------|
| BL-042 | Login flow | 001-login | open | completed | completed |
| BL-043 | Auth tokens | 001-login | completed | none | completed |
```

## Allowed MCP Tools

- `read_document`
- `get_backlog_item`
- `list_backlog_items`
- `complete_backlog_item`

## Guidelines

- Complete ALL open items that have corresponding completed features — do not defer
- If `complete_backlog_item` fails for an item, document the error and continue
- Do NOT create new backlog items — only complete existing ones
- Do NOT commit — the master prompt handles commits
