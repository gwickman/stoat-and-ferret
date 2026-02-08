# Task 010: Finalization

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective

Verify all retrospective tasks completed, run final quality gates, commit closure changes, push to remote, and mark the version as complete.

## Context

Post-version retrospective for `${PROJECT}` version `${VERSION}`. This is the final task — it wraps up everything and produces the official version completion.

## Tasks

### 1. Verify All Previous Tasks Completed

Read the README.md from each task folder and verify it exists and indicates successful completion:

| Task | Folder | Required |
|------|--------|----------|
| 001 | `comms/outbox/versions/retrospective/${VERSION}/001-environment/` | Yes |
| 002 | `comms/outbox/versions/retrospective/${VERSION}/002-documentation/` | Yes |
| 003 | `comms/outbox/versions/retrospective/${VERSION}/003-backlog/` | Yes |
| 004 | `comms/outbox/versions/retrospective/${VERSION}/004-quality/` | Yes |
| 005 | `comms/outbox/versions/retrospective/${VERSION}/005-architecture/` | Yes |
| 006 | `comms/outbox/versions/retrospective/${VERSION}/006-learnings/` | Yes |
| 007 | `comms/outbox/versions/retrospective/${VERSION}/007-proposals/` | Yes |
| 008 | `comms/outbox/versions/retrospective/${VERSION}/008-closure/` | Yes |
| 009 | `comms/outbox/versions/retrospective/${VERSION}/009-project-closure/` | Conditional |
| 010 | This task | — |

If any required task is missing or reports failure, document the gap and STOP.

### 2. Run Final Quality Gates and Verify Resolution

```python
run_quality_gates(project="${PROJECT}")
```

If ALL checks pass → proceed to step 3.

If any checks fail:
1. For each failure, check if it was classified as a "code problem" in Task 004 and has a corresponding backlog item created by Task 007
2. If ALL failures have backlog item references → proceed to step 3
   (Log: "Version completing with N documented code-problem deferrals: BL-XXX, BL-YYY")
3. If ANY failure lacks a backlog item reference → **STOP**
   ("Cannot complete version: unclassified test failures remain. Re-run Task 004 classification or create missing backlog items.")

This ensures a clean exit: either all tests pass, or every failure is explicitly accounted for with a backlog item.

### 3. Commit All Closure Changes

Stage and commit all retrospective and closure changes:

```bash
git add comms/outbox/versions/retrospective/${VERSION}/
git add docs/  # Any docs updated during closure
git add comms/  # Any state changes
git commit -m "chore(${VERSION}): version closure housekeeping"
```

### 4. Push to Remote

```bash
git push
```

### 5. Mark Version Complete

```python
complete_version(project="${PROJECT}", version_number=<N>)
```

Where N is the numeric version extracted from `${VERSION}`.

Verify the call succeeds.

### 6. Generate Final Summary

Create a summary of the entire retrospective process:
- Total tasks executed
- Findings count by category
- Remediation actions taken
- Backlog items created/completed
- Learnings saved
- Time from start to finish (if available)

## Output Requirements

Save outputs to `comms/outbox/versions/retrospective/${VERSION}/010-finalization/`:

### README.md (required)

First paragraph: Finalization summary (version officially closed / blocked with reason).

Then:
- **Task Verification**: All tasks confirmed complete
- **Final Quality Gates**: All passed
- **Commit**: SHA and files included
- **Version Status**: complete_version result
- **Retrospective Summary**: High-level metrics

### final-summary.md

Complete retrospective summary:

```markdown
# ${VERSION} Retrospective Summary

## Overview
- **Project**: ${PROJECT}
- **Version**: ${VERSION}
- **Status**: Complete
- **Commit**: [SHA]

## Verification Results
| Task | Status | Key Findings |
|------|--------|-------------|
| 001 Environment | Pass | [summary] |
| 002 Documentation | Pass | [summary] |
...

## Actions Taken
- Backlog items completed: X
- Documentation gaps fixed: Y
- Learnings saved: Z
- Architecture drift items: W

## Outstanding Items
- [Any items requiring future attention]
```

## Allowed MCP Tools

- `read_document`
- `run_quality_gates`
- `complete_version`
- `commit_changes`
- `git_read`

## Guidelines

- Do NOT proceed past a failing quality gate — STOP and report
- Do NOT skip the commit step
- Do NOT call complete_version if quality gates fail
- This task produces the final record of the retrospective — be thorough in the summary
