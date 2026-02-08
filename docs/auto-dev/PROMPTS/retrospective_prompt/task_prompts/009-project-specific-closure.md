# Task 009: Project-Specific Closure

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective

Execute the project-specific version closure checklist defined in `docs/auto-dev/VERSION_CLOSURE.md`. This task is generic — it reads whatever the closure document contains and orchestrates execution.

## Context

Post-version retrospective for `${PROJECT}` version `${VERSION}`. This task only runs if `docs/auto-dev/VERSION_CLOSURE.md` exists. The master prompt has already verified this condition.

## Tasks

### 1. Read VERSION_CLOSURE.md

Read `docs/auto-dev/VERSION_CLOSURE.md` in full. Parse the document to identify:
- All top-level sections (## headings)
- All checklist items within each section
- Any verification procedures described

### 2. Classify Each Section

For each section, determine the execution strategy:

**Inline Verification**: Sections that require running checks or calling MCP tools
- Example: "Run health_check", "Run pytest", "Verify file exists"
- Execute these directly within this task

**Document Updates**: Sections that require reading and updating documentation files
- Example: "Update TOOL_LISTING.md", "Update setup guides"
- Launch parallel explorations for independent document update sections

**Manual/Interactive**: Sections that require user action
- Example: Skills repackaging
- Document what needs to be done and flag for user attention

### 3. Execute Inline Verifications

For each section classified as "Inline Verification":
1. Execute the checks described
2. Record pass/fail for each checklist item
3. If a check fails: attempt straightforward fixes, document non-trivial failures

### 4. Launch Parallel Explorations for Document Updates

For each independent document update section, launch an exploration:

```python
start_exploration(
    project="${PROJECT}",
    results_folder=f"{VERSION}-closure-{section_slug}",
    prompt="""
Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective
Execute the "{section_name}" checklist from VERSION_CLOSURE.md for version {VERSION}.

## Input
Read: docs/auto-dev/VERSION_CLOSURE.md — section "{section_name}"

## Tasks
[Include the specific checklist items for this section]

## Output Requirements
Save outputs to comms/outbox/exploration/{VERSION}-closure-{section_slug}/:

### README.md (required)
First paragraph: Summary of checklist items completed.
Then: Table of each item, its status, and changes made.

Do NOT commit — the calling prompt handles commits.
"""
)
```

Poll all explorations until complete. Collect results.

### 5. Document Manual/Interactive Items

For sections requiring user action:
- Document exactly what needs to be done
- Include specific file paths and actions
- Flag for user notification by the master prompt

### 6. Compile Results

Aggregate results from:
- Inline verifications (step 3)
- Exploration results (step 4)
- Manual items flagged (step 5)

## Output Requirements

Save outputs to `comms/outbox/versions/retrospective/${VERSION}/009-project-closure/`:

### README.md (required)

First paragraph: Project-specific closure summary (X sections processed, Y passed, Z need attention).

Then:
- **Sections Processed**: Table of section → strategy → status
- **Inline Checks**: Results of verification checks
- **Document Updates**: Results from explorations
- **User Actions Required**: Items needing human intervention
- **Issues**: Any failures or blockers

### closure-detail.md

Per-section detail:

```markdown
## Section: [name]

**Strategy:** Inline Verification / Document Update / Manual

**Items:**
| Checklist Item | Status | Notes |
|----------------|--------|-------|
| Item 1 | Pass | Verified OK |
| Item 2 | Updated | Changed X to Y |
| Item 3 | User Action | Needs repackaging |
```

## Allowed MCP Tools

- `read_document`
- `health_check`
- `run_quality_gates`
- `start_exploration`
- `get_exploration_status`
- `get_exploration_result`
- `list_backlog_items`
- `add_backlog_item`
- `git_read`

## Guidelines

- Read VERSION_CLOSURE.md as-is — do not hardcode assumptions about its sections
- Launch explorations for document update sections that are independent of each other
- Wait for all explorations before compiling the final report
- Do NOT skip any section — every checklist item must be addressed
- Do NOT commit — the master prompt handles commits
