# Task 007: Stage 1 Proposals

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective

Compile all findings from tasks 001-006 into a single proposals document using the Crystal Clear Actions format. All proposals are auto-approved.

## Context

Post-version retrospective for `${PROJECT}` version `${VERSION}`. This task synthesizes all verification and analysis results into actionable remediation proposals.

## Tasks

### 1. Read All Previous Task Outputs

Read the README.md from each completed task:
- `comms/outbox/versions/retrospective/${VERSION}/001-environment/README.md`
- `comms/outbox/versions/retrospective/${VERSION}/002-documentation/README.md`
- `comms/outbox/versions/retrospective/${VERSION}/003-backlog/README.md`
- `comms/outbox/versions/retrospective/${VERSION}/004-quality/README.md`
- `comms/outbox/versions/retrospective/${VERSION}/005-architecture/README.md`
- `comms/outbox/versions/retrospective/${VERSION}/006-learnings/README.md`

Read detailed reports where the README references them.

### 2. Identify All Findings Requiring Action

From each task, extract items that need remediation:
- **001**: Environment blockers (stale branches, dirty working tree)
- **002**: Missing documentation artifacts
- **003**: Backlog items that failed to complete
- **004**: Quality gate failures not yet fixed
- **005**: Architecture drift items (already handled via backlog — reference only)
- **006**: Learning extraction issues (unlikely but check)

### 3. Create Backlog Items for Quality Gate Code Problems

For each failure classified as a "code problem" in Task 004's README.md:

1. Create a backlog item:
   ```python
   add_backlog_item(
       project="${PROJECT}",
       title="Fix: <test_name> — <brief description of the bug>",
       priority="P1",
       description="""
   ## Bug Description
   Test `<test_file>::<test_name>` correctly identifies a bug in `<production_file>`.

   **Expected behavior:** <what the test expects>
   **Actual behavior:** <what happens>
   **Root cause:** <analysis from Task 004>

   ## Evidence
   Identified during ${VERSION} retrospective quality gate analysis.
   Classification: code problem (test is correct, production code has a bug).

   ## Resolution
   Fix the production code to match the expected behavior.
   """,
       tags=["bug", "quality-gate", "retrospective"],
       quality_assertion='{"problem_structured": true, "ac_testable": true, "no_formulaic": true, "duplicate_checked": true}'
   )
   ```

2. Document the backlog item ID (BL-XXX) in the proposals output
3. Reference the backlog item ID in the Task 010 finalization summary

If Task 004 reports no code problems, skip this section and note "No quality gate backlog items needed."

### 4. Create Proposals Document

For each finding, use this exact format:

```markdown
### Finding: [Brief description]

**Source:** Task [NNN] - [task name]

**Current State:**
[What exists now — specific file paths and content]

**Gap:**
[What's missing or incorrect]

**Proposed Actions:**
- [ ] [Action 1]: `exact/file/path` — [exact change to make]
- [ ] [Action 2]: `exact/file/path` — [exact change to make]

**Auto-approved:** Yes
```

### Anti-Patterns (DO NOT USE)

- "Review and update if needed"
- "Consider adding documentation"
- "May need to check X"
- "Should probably update Y"

Every action must specify: exact file path, exact change, no ambiguity.

### 5. Categorize Proposals

Group proposals by type:
- **Immediate Fixes**: Can be executed by the remediation exploration
- **Backlog Items**: Already created by previous tasks (reference only)
- **User Action Required**: Items requiring human intervention

### 6. Summary Statistics

Count:
- Total findings across all tasks
- Findings with no action needed (everything was clean)
- Immediate fix proposals
- Backlog items created/updated
- User actions required

## Output Requirements

Save outputs to `comms/outbox/versions/retrospective/${VERSION}/007-proposals/`:

### README.md (required)

First paragraph: Proposals summary (X findings, Y immediate fixes, Z backlog items, W user actions).

Then:
- **Status by Task**: Table of task → findings count → actions needed
- **Immediate Fixes**: List of actions for remediation exploration
- **Backlog References**: Items already handled
- **User Actions**: Items requiring human intervention

### proposals.md

Complete proposals document with all findings in Crystal Clear Actions format. This file is the input for the remediation exploration launched by the master prompt.

## Allowed MCP Tools

- `read_document`
- `add_backlog_item`

## Guidelines

- Every finding must reference its source task number
- Every action must be specific enough to execute without further investigation
- Do NOT execute remediation actions — only document them
- The master prompt launches a separate exploration for remediation execution
- If no findings require action, create proposals.md stating "No remediation required"
- Do NOT commit — the master prompt handles commits
