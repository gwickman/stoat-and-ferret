Read AGENTS.md first and follow all instructions there.

## Objective

Extract transferable learnings from all completion reports and theme retrospectives for v005 of stoat-and-ferret, then save them via the learnings system.

## Tasks

### 1. Read All Completion Reports
Read every completion report for v005:
- `comms/outbox/versions/execution/v005/<theme>/<feature>/completion-report.md`

For each report, identify patterns that worked well, approaches that failed, decision rationale worth preserving, and debugging techniques that resolved issues.

### 2. Read All Theme Retrospectives
Read every theme retrospective:
- `comms/outbox/versions/execution/v005/<theme>/retrospective.md`

Identify cross-feature patterns, theme-level learnings, and process observations.

### 3. Read Version Retrospective
Read `comms/outbox/versions/execution/v005/retrospective.md` and identify version-level insights.

### 4. Deduplicate and Filter
Remove duplicates, implementation-specific details, and version-specific references. Keep transferable patterns, failure modes, decision frameworks, and debugging approaches.

### 5. Save Learnings
For each unique learning, call `save_learning(project="stoat-and-ferret", ...)` with title, content (using Context/Learning/Evidence/Application markdown structure), tags, source, and summary.

### 6. Check Existing Learnings
Call `list_learnings(project="stoat-and-ferret")` and check if any existing learnings are reinforced by new evidence. Note but do NOT modify existing learnings.

## Output Requirements

Save outputs to comms/outbox/exploration/v005-retro-006-learnings/

### README.md (required)
First paragraph: Learnings summary (X new learnings saved, Y existing reinforced).

Then:
- **New Learnings**: Table of title, tags, source
- **Reinforced Learnings**: Existing learnings that got additional evidence
- **Filtered Out**: Count and categories of items filtered

### learnings-detail.md
For each learning saved: title, tags, source, full content.

Commit the results in v005-retro-006-learnings with message "docs(v005): retrospective task 006 - learning extraction".