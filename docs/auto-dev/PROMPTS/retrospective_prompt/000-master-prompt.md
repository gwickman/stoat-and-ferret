# Post-Version Retrospective Orchestrator - Master Prompt

**PROJECT CONFIGURATION:**
```
PROJECT=[SET_PROJECT_NAME_HERE]
VERSION=[SET_VERSION_HERE]
```

**CRITICAL:** Set both PROJECT and VERSION variables above before proceeding.

---

## MCP Tool Authorization

Extract the autoDevToolKey from your initial prompt if present:
- Pattern: `autoDevToolKey: ([a-f0-9-]{36})`
- Include in all MCP tool calls to auto-dev-mcp

---

## Pre-Execution Validation

**STEP 1:** Verify variables are set.

```python
if PROJECT == "[SET_PROJECT_NAME_HERE]" or not PROJECT.strip():
    STOP: "ERROR: PROJECT variable not set."
if VERSION == "[SET_VERSION_HERE]" or not VERSION.strip():
    STOP: "ERROR: VERSION variable not set."
```

**STEP 2:** Verify project exists.

```python
result = get_project_info(project=PROJECT)
if not result.success:
    STOP: "ERROR: Project {PROJECT} not found."
```

**STEP 3:** Verify version execution is complete.

```python
result = get_version_status(project=PROJECT, version_number=int(VERSION[1:]))
# version-state.json status must be "completed" or all themes must be completed
if status not in ("completed", "all_themes_complete"):
    STOP: "ERROR: Version {VERSION} execution not complete."
```

**STEP 4:** Verify retrospective folder does NOT already exist.

```python
# Check: comms/outbox/versions/retrospective/{VERSION}/ must NOT exist
if folder_exists:
    STOP: "ERROR: Retrospective for {VERSION} already exists."
```

**STEP 5:** Create deliverables folder structure.

```
comms/outbox/versions/retrospective/{VERSION}/
├── 001-environment/
├── 002-documentation/
├── 003-backlog/
├── 004-quality/
├── 005-architecture/
├── 006-learnings/
├── 007-proposals/
├── 008-closure/
├── 009-project-closure/
└── 010-finalization/
```

**If ANY validation fails, output a clear error message and STOP.**

---

## Task Execution Flow

### Phase 1: Verification (Tasks 001-004)

**Task 001:** Environment verification
- Read: `docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/001-environment-verification.md`
- Output: `comms/outbox/versions/retrospective/{VERSION}/001-environment/`
- Start exploration → poll → verify output README.md exists

**Task 002:** Documentation completeness
- Read: `docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/002-documentation-completeness.md`
- Output: `comms/outbox/versions/retrospective/{VERSION}/002-documentation/`
- Start exploration → poll → verify output README.md exists

**Task 003:** Backlog verification
- Read: `docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/003-backlog-verification.md`
- Output: `comms/outbox/versions/retrospective/{VERSION}/003-backlog/`
- Start exploration → poll → verify output README.md exists

**Task 004:** Quality gates
- Read: `docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/004-quality-gates.md`
- Output: `comms/outbox/versions/retrospective/{VERSION}/004-quality/`
- Start exploration → poll → verify output README.md exists

### Phase 2: Analysis (Tasks 005-006)

**Task 005:** Architecture alignment
- Read: `docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/005-architecture-alignment.md`
- Output: `comms/outbox/versions/retrospective/{VERSION}/005-architecture/`
- Start exploration → poll → verify output README.md exists

**Task 006:** Learning extraction
- Read: `docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/006-learning-extraction.md`
- Output: `comms/outbox/versions/retrospective/{VERSION}/006-learnings/`
- Start exploration → poll → verify output README.md exists

**COMMIT:** After Task 006, commit verification and analysis artifacts:
```bash
git add comms/outbox/versions/retrospective/{VERSION}/
git commit -m "docs({VERSION}): retrospective verification and analysis artifacts"
git push
```

### Phase 3: Remediation (Task 007)

**Task 007:** Stage 1 proposals compilation
- Read: `docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/007-stage1-proposals.md`
- Output: `comms/outbox/versions/retrospective/{VERSION}/007-proposals/`
- Start exploration → poll → verify output README.md exists

**If proposals identify remediation actions:**
Launch a SEPARATE exploration to execute remediation:

```python
start_exploration(
    project=PROJECT,
    results_folder=f"{VERSION}-retro-remediation",
    prompt="""
Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective
Execute all remediation actions from the Stage 1 proposals document.

## Input
Read: comms/outbox/versions/retrospective/{VERSION}/007-proposals/proposals.md

## Tasks
For each proposed action:
1. Read the action description
2. Execute the action exactly as specified
3. Document the result

## Output Requirements
Save outputs to comms/outbox/exploration/{VERSION}-retro-remediation/:

### README.md (required)
First paragraph: Summary of remediation actions executed.
Then: Table of each action, its status, and any notes.

Do NOT commit — the calling prompt handles commits.
"""
)
```

Poll for completion. If remediation exploration fails, document the failure and continue.

### Phase 4: Closure (Tasks 008-009)

**Task 008:** Generic closure
- Read: `docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/008-generic-closure.md`
- Output: `comms/outbox/versions/retrospective/{VERSION}/008-closure/`
- Start exploration → poll → verify output README.md exists

**Task 009:** Project-specific closure (CONDITIONAL)

```python
# Check if docs/auto-dev/VERSION_CLOSURE.md exists for this project
if file_exists(f"docs/auto-dev/VERSION_CLOSURE.md"):
    # Run task 009
    # Read: docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/009-project-specific-closure.md
    # Output: comms/outbox/versions/retrospective/{VERSION}/009-project-closure/
    # Start exploration → poll → verify output README.md exists
else:
    # Skip task 009
    # Create 009-project-closure/README.md with: "Skipped: No VERSION_CLOSURE.md found."
```

### Phase 5: Finalization (Task 010)

**Task 010:** Finalization
- Read: `docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/010-finalization.md`
- Output: `comms/outbox/versions/retrospective/{VERSION}/010-finalization/`
- Start exploration → poll → verify output README.md exists

---

## Error Handling

Between each task:
1. Check exploration status via `get_exploration_status`
2. If "failed", document the failure in the task's output folder and STOP
3. If "complete", read result to verify output README.md exists
4. Only proceed to next task if current task succeeded

---

## Progress Tracking

- [ ] Validation: PROJECT and VERSION set
- [ ] Validation: Project exists
- [ ] Validation: Version execution complete
- [ ] Validation: Retrospective folder does not exist
- [ ] Validation: Deliverables folder structure created
- [ ] Task 001: Environment verification
- [ ] Task 002: Documentation completeness
- [ ] Task 003: Backlog verification
- [ ] Task 004: Quality gates
- [ ] Task 005: Architecture alignment
- [ ] Task 006: Learning extraction
- [ ] COMMIT: Verification and analysis artifacts
- [ ] Task 007: Stage 1 proposals + remediation explore
- [ ] Task 008: Generic closure
- [ ] Task 009: Project-specific closure (conditional)
- [ ] Task 010: Finalization

---

## Completion

When all tasks complete:
1. Verify all output folders contain README.md
2. Output success message with summary of findings and actions taken
3. Report any outstanding items requiring user attention

### auto-dev-mcp Conditional: Skills Repackaging

```python
if PROJECT == "auto-dev-mcp":
    # Task 009 may have identified skills needing repackaging
    # Read 009-project-closure/README.md for skills status
    # If any skills need repackaging, inform user:
    # "Interactive step outstanding: Skills repackaging needed for: [list]"
```

---

## Usage

1. Set PROJECT and VERSION variables at the top
2. Run this prompt via Chatbot orchestration
3. Monitor progress — orchestrator executes all tasks sequentially
4. Handle failures — investigate and fix before retrying
