Read AGENTS.md first and follow all instructions there.

## Objective

Compile all findings from retrospective tasks 001-006 for stoat-and-ferret version v004 into a single proposals document using the Crystal Clear Actions format. All proposals are auto-approved.

## Tasks

### 1. Read All Previous Task Outputs
Read the README.md from each completed task:
- comms/outbox/versions/retrospective/v004/001-environment/README.md
- comms/outbox/versions/retrospective/v004/002-documentation/README.md
- comms/outbox/versions/retrospective/v004/003-backlog/README.md
- comms/outbox/versions/retrospective/v004/004-quality/README.md
- comms/outbox/versions/retrospective/v004/005-architecture/README.md
- comms/outbox/versions/retrospective/v004/006-learnings/README.md

Read detailed reports where the README references them.

### 2. Identify All Findings Requiring Action
From each task, extract items that need remediation:
- 001: Environment blockers (stale branches, dirty working tree)
- 002: Missing documentation artifacts
- 003: Backlog items that failed to complete
- 004: Quality gate failures not yet fixed
- 005: Architecture drift items (already handled via backlog — reference only)
- 006: Learning extraction issues

### 3. Create Backlog Items for Quality Gate Code Problems
For each failure classified as a "code problem" in Task 004's README.md, create a backlog item via add_backlog_item(). If Task 004 reports no code problems, skip this section.

### 4. Create Proposals Document
For each finding use this exact format:
```
### Finding: [Brief description]
**Source:** Task [NNN] - [task name]
**Current State:** [What exists now]
**Gap:** [What's missing or incorrect]
**Proposed Actions:**
- [ ] [Action]: `exact/file/path` — [exact change]
**Auto-approved:** Yes
```

Anti-patterns to avoid: "Review and update if needed", "Consider adding", "May need to check", "Should probably update".

### 5. Categorize Proposals
Group by: Immediate Fixes, Backlog Items (reference only), User Action Required.

### 6. Summary Statistics
Count: total findings, findings with no action needed, immediate fix proposals, backlog items, user actions.

## Output Requirements

Save outputs to comms/outbox/exploration/v004-retro-007-proposals/:

### README.md (required)
First paragraph: Proposals summary (X findings, Y immediate fixes, Z backlog items, W user actions).

Then:
- **Status by Task**: Table of task to findings count to actions needed
- **Immediate Fixes**: List of actions for remediation exploration
- **Backlog References**: Items already handled
- **User Actions**: Items requiring human intervention

### proposals.md
Complete proposals document with all findings in Crystal Clear Actions format. This file is the input for remediation if needed.

Do NOT commit — the calling prompt handles commits. Results folder: v004-retro-007-proposals.