Read AGENTS.md first and follow all instructions there.

## Objective

Cross-reference backlog items referenced in feature requirements with their actual status, and complete any still-open items that were implemented during v005 of stoat-and-ferret.

## Tasks

### 1. Scan Feature Requirements for BL-XXX References
Read `comms/inbox/versions/execution/v005/THEME_INDEX.md` to get the version structure.

For each feature, read:
- `comms/inbox/versions/execution/v005/<theme>/<feature>/requirements.md`

Extract all `BL-XXX` references from each requirements file.

### 2. Check Backlog Item Status
For each unique BL-XXX reference found, call:
`get_backlog_item(project="stoat-and-ferret", item_id="BL-XXX")`

Record: item ID, title, current status, referencing feature.

### 3. Complete Open Backlog Items
For each backlog item that is still "open" but was referenced by a completed feature, call:
`complete_backlog_item(project="stoat-and-ferret", item_id="BL-XXX", version="v005", theme="<theme-name>")`

Record: item ID, action taken, result.

### 4. Check for Orphaned Items
Call `list_backlog_items(project="stoat-and-ferret", status="open")` and check if any open items reference v005 in their description or notes but were not found in requirements files. Document any orphaned items found.

## Output Requirements

Save outputs to comms/outbox/exploration/v005-retro-003-backlog/

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
| Backlog Item | Title | Feature | Status Before | Action | Status After |

Commit the results in v005-retro-003-backlog with message "docs(v005): retrospective task 003 - backlog verification".