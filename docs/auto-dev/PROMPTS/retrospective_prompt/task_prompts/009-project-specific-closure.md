# Task 009: Project-Specific Closure

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective

Evaluate project-specific closure needs for this version, then execute any closure checklist defined in `docs/auto-dev/VERSION_CLOSURE.md`. This task always runs — even when VERSION_CLOSURE.md is absent, it evaluates closure needs based on the version's actual changes.

## Context

Post-version retrospective for `${PROJECT}` version `${VERSION}`.

## Tasks

### 1. Evaluate Project-Specific Closure Needs (ALWAYS runs)

**This step runs unconditionally, regardless of whether VERSION_CLOSURE.md exists.**

Review the version's themes and features to identify genuine project-specific closure needs. Read the version design and theme summaries to understand what changed:

- Read `comms/inbox/versions/design/${VERSION}/VERSION_DESIGN.md` (or equivalent) for version scope
- Read available theme summaries/completion reports under `comms/outbox/versions/execution/${VERSION}/`

Based on the actual changes, evaluate closure needs such as:
- Did this version modify any prompt templates that need cross-referencing with other prompts?
- Did this version add/change MCP tools that need documentation updates?
- Did this version alter any configuration schemas that need migration notes?
- Did this version change any shared utilities that downstream consumers depend on?
- Did this version introduce any new files/patterns that need to be reflected in project indexes?
- Did any features affect cross-project tooling (MCP tools, git operations, exploration)? If so, were they validated against a destructive test target project? If test-target validation was warranted but not performed, flag this as a gap.

**CRITICAL: Do NOT fabricate closure suggestions. Only identify genuine closure needs based on the version's actual changes. If no closure needs are found, state that explicitly — do not invent work.**

Record the evaluation findings for inclusion in the output.

### 2. Check for VERSION_CLOSURE.md

```python
# Check if docs/auto-dev/VERSION_CLOSURE.md exists
closure_file_exists = file_exists("docs/auto-dev/VERSION_CLOSURE.md")
```

- **If the file exists:** proceed to Step 3 (checklist execution) AND Step 4 (merge findings)
- **If the file is absent:** proceed to Step 5 (output evaluation summary)

### 3. Execute VERSION_CLOSURE.md Checklist (when file exists)

Read `docs/auto-dev/VERSION_CLOSURE.md` in full. Parse the document to identify:
- All top-level sections (## headings)
- All checklist items within each section
- Any verification procedures described

#### 3a. Classify Each Section

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

#### 3b. Execute Inline Verifications

For each section classified as "Inline Verification":
1. Execute the checks described
2. Record pass/fail for each checklist item
3. If a check fails: attempt straightforward fixes, document non-trivial failures

#### 3c. Launch Parallel Explorations for Document Updates

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

#### 3d. Document Manual/Interactive Items

For sections requiring user action:
- Document exactly what needs to be done
- Include specific file paths and actions
- Flag for user notification by the master prompt

### 4. Merge Checklist and Evaluation Findings (when file exists)

Combine results from:
- Step 1 evaluation findings (project-specific closure needs)
- Step 3 checklist execution (VERSION_CLOSURE.md items)

If the Step 1 evaluation identified closure needs not covered by VERSION_CLOSURE.md, include them as additional findings in the output.

### 5. Output Evaluation Summary (when file is absent)

When VERSION_CLOSURE.md does not exist, compile the Step 1 evaluation into a summary that explains:
- What closure areas were evaluated
- What the version's themes/features changed
- Whether any closure needs were identified
- Specific closure actions needed (if any), or explicit confirmation that none were found

**Do NOT output "Skipped" — always provide the evaluation summary from Step 1.**

## Output Requirements

Save outputs to `comms/outbox/versions/retrospective/${VERSION}/009-project-closure/`:

### README.md (required)

**When VERSION_CLOSURE.md exists:**

First paragraph: Project-specific closure summary (X sections processed, Y passed, Z need attention).

Then:
- **Closure Evaluation**: Summary of Step 1 findings (project-specific closure needs based on version changes)
- **Sections Processed**: Table of section → strategy → status
- **Inline Checks**: Results of verification checks
- **Document Updates**: Results from explorations
- **User Actions Required**: Items needing human intervention
- **Additional Closure Needs**: Any needs identified in Step 1 not covered by the checklist
- **Issues**: Any failures or blockers

**When VERSION_CLOSURE.md is absent:**

First paragraph: Project-specific closure evaluation summary for version ${VERSION}.

Then:
- **Closure Evaluation**: What areas were evaluated and what the version changed
- **Findings**: Any closure needs identified, or "No project-specific closure needs identified for this version"
- **Note**: "No VERSION_CLOSURE.md found. Evaluation was performed based on the version's actual changes."

### closure-detail.md (when VERSION_CLOSURE.md exists)

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

- **Always perform the closure evaluation (Step 1)** — this is the core change from previous behavior
- Read VERSION_CLOSURE.md as-is — do not hardcode assumptions about its sections
- Launch explorations for document update sections that are independent of each other
- Wait for all explorations before compiling the final report
- Do NOT skip any section — every checklist item must be addressed
- Do NOT fabricate closure suggestions — only report genuine needs based on actual changes
- Do NOT commit — the master prompt handles commits
