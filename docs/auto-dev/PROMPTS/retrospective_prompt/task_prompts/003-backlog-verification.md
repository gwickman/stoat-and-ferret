# Task 003: Backlog Verification

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective

Cross-reference backlog items referenced in feature requirements with their actual status, and complete any still-open items that were implemented.

## Context

Post-version retrospective for `${PROJECT}` version `${VERSION}`. Completed features do NOT automatically close backlog items. This task ensures all implemented backlog items are marked complete.

## Tasks

### 1. Get Planned Items from PLAN.md

Read `docs/auto-dev/PLAN.md` — this is the **authoritative source** for which backlog items were planned for a version.

Find the section for `${VERSION}` and extract all `BL-XXX` references listed under its themes. The format looks like:

```
#### vXXX — Description (N items)
- **Theme 1: theme-name** — BL-101 (S), BL-102 (M), BL-103 (L)
- **Theme 2: theme-name** — BL-104 (S), BL-105 (M)
```

Record every BL-XXX from the version's section as a **planned** item.

> **Note:** Use `docs/auto-dev/PLAN.md` (the main plan file with all version sections), not per-version `VERSION_DESIGN.md` files.

### 2. Scan Feature Requirements for BL-XXX References

Read `comms/inbox/versions/execution/${VERSION}/THEME_INDEX.md` to get the version structure.

For each feature, read:
- `comms/inbox/versions/execution/${VERSION}/<theme>/<feature>/requirements.md`

Extract all `BL-XXX` references from each requirements file. This is a **secondary validation** step that catches items referenced in implementation but potentially missing from PLAN.md.

### 3. Check Backlog Item Status

For each unique BL-XXX reference found (from both Step 1 and Step 2), call:
```python
get_backlog_item(project="${PROJECT}", item_id="BL-XXX")
```

Record: item ID, title, current status, referencing feature, and whether the item was in PLAN.md (planned) or only found in requirements.md (unplanned).

### 4. Complete Open Backlog Items

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

### 5. Check for Orphaned Items

Call `list_backlog_items(project="${PROJECT}", status="open")` and check if any open items reference `${VERSION}` in their description or notes but were not found in requirements files.

Document any orphaned items found.

### 6. Backlog Hygiene Checks (Advisory)

Run the following advisory hygiene checks and include observations in the output. These are informational only and do NOT block the retrospective.

#### 6a. Staleness Detection

Use the `BacklogService.check_staleness()` method (available via the backlog service) to identify open items not updated within 90 days. Items with "deferred" in their notes are reported separately as intentionally deferred.

Report:
- Number of stale items (open > 90 days without deferred marker)
- Number of intentionally deferred items
- Top 5 stale items by age (ID, title, age in days)

#### 6b. Tag Consistency Review

Use the `BacklogService.check_tag_consistency()` method to identify:
- Orphaned tags (used only by completed/cancelled items, not by any active item)
- Tag frequency distribution for active items

Report:
- List of orphaned tags
- Top 10 most-used tags with counts

#### 6c. Size Calibration

For completed items in this version, compare the `size` estimate (S/M/L/XL) to actual execution patterns. Note any items whose actual complexity appeared to differ significantly from the estimate.

Report:
- Count of completed items by size category
- Any notable calibration observations

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
- **Hygiene Observations**: Advisory results from staleness detection, tag consistency review, and size calibration (Section 6)

### backlog-report.md

Detailed table:

```markdown
| Backlog Item | Title | Feature | Planned | Status Before | Action | Status After |
|--------------|-------|---------|---------|---------------|--------|--------------|
| BL-042 | Login flow | 001-login | Yes | open | completed | completed |
| BL-043 | Auth tokens | 001-login | Yes | completed | none | completed |
| BL-099 | Edge case fix | 002-api | No | open | completed | completed |
```

- **Planned = Yes**: Item appeared in `docs/auto-dev/PLAN.md` under the version section
- **Planned = No**: Item found only in feature `requirements.md` files (out-of-scope addition)

### Handling Unplanned Items

Items found in `requirements.md` but **not** in `PLAN.md` are out-of-scope additions. These are not errors, but should be flagged for visibility:

- Still complete them if the feature was implemented
- Note them in the README.md under a separate **Unplanned Items** section
- Include a brief explanation of why they were added (if apparent from the requirements)

## Allowed MCP Tools

- `read_document`
- `get_backlog_item`
- `list_backlog_items`
- `complete_backlog_item`
- `get_theme_status`
- `list_product_requests`
- `get_product_request`
- `add_product_request`
- `update_product_request`
- `upvote_item`

## Guidelines

**MCP Tools Only:** All backlog operations (completion, updates, creation) MUST use MCP tools (`complete_backlog_item`, `update_backlog_item`, `add_backlog_item`, `get_backlog_item`, `list_backlog_items`). NEVER edit `backlog.json` directly. Direct edits bypass the `next_id` counter increment, causing duplicate ID collisions.

- Complete ALL open items that have corresponding completed features — do not defer
- If `complete_backlog_item` fails for an item, document the error and continue
- Do NOT create new backlog items — only complete existing ones
- Do NOT commit — the master prompt handles commits
