Read AGENTS.md first and follow all instructions there.

## Objective

Check whether changes implemented in v004 of stoat-and-ferret have caused drift from documented architecture. Update or create backlog items only if NEW drift is detected.

## Tasks

### 1. Check for Existing Open Architecture Backlog Items
Search for open backlog items related to architecture or C4:
- list_backlog_items(project="stoat-and-ferret", status="open", search="C4")
- list_backlog_items(project="stoat-and-ferret", status="open", search="architecture")
- list_backlog_items(project="stoat-and-ferret", status="open", tags=["architecture"])
- list_backlog_items(project="stoat-and-ferret", status="open", tags=["c4"])

If an open item exists, read its description and notes to understand what drift is already documented.

### 2. Gather Version Changes
Read the version retrospective and all theme retrospectives:
- comms/outbox/versions/execution/v004/retrospective.md
- All comms/outbox/versions/execution/v004/<theme>/retrospective.md

Extract: new services/handlers/components added, components modified, components removed, new external dependencies.

### 3. Check Current Architecture Documentation
Read architecture documentation if it exists:
- docs/C4-Documentation/README.md
- docs/C4-Documentation/c4-context.md
- docs/C4-Documentation/c4-container.md
- docs/ARCHITECTURE.md

Note what exists and what doesn't.

### 4. Detect Drift
Compare changes from step 2 against documentation from step 3.

### 5. Take Action Based on Findings
- If NO new drift: document "no additional architecture drift detected"
- If NEW drift AND existing open architecture backlog item: update_backlog_item with notes
- If NEW drift AND no existing open item: add_backlog_item with title, priority P2, tags ["architecture", "c4", "documentation"]

## Output Requirements

Save outputs to comms/outbox/exploration/v004-retro-005-architecture/:

### README.md (required)
First paragraph: Architecture alignment summary (aligned / drift detected / no docs to compare).

Then:
- **Existing Open Items**: List of open architecture backlog items found (or "none")
- **Changes in v004**: Summary of architectural changes made
- **Documentation Status**: What architecture docs exist and their currency
- **Drift Assessment**: Specific drift items found (or "no additional drift")
- **Action Taken**: What was done (nothing / updated existing item / created new item)

Do NOT commit — the calling prompt handles commits. Results folder: v004-retro-005-architecture.