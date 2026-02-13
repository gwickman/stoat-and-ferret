# Post-Version Retrospective Orchestrator v2 - Master Prompt

**PROJECT CONFIGURATION:**
```
PROJECT=[SET_PROJECT_NAME_HERE]
VERSION=[SET_VERSION_HERE]
```

**CRITICAL:** Set both PROJECT and VERSION variables above before proceeding.

---

## Orchestrator Rules

**Your ONLY job is to launch sub-explorations and poll them to completion. Follow these rules strictly:**

1. **NEVER execute task work inline.** You are an orchestrator, not a worker. Every task (001–010) MUST be delegated to a sub-exploration via `start_exploration`. Do not write files, run quality gates, check backlog items, or extract learnings yourself.

2. **Read each task prompt ONLY when you are about to launch it.** Do not read task prompts in advance or in batches. This wastes your context budget.

3. **Poll sub-explorations with 30-second minimum intervals.** After calling `get_exploration_status`, wait at least 30 seconds before polling again. Sub-explorations typically take 3–10 minutes.

4. **Use the sub-exploration launch template exactly.** See the template below. The `results_folder` must follow the pattern `{VERSION}-retro-{NNN}-{short-name}`. The prompt must reference `comms/outbox/exploration/{results_folder}/` as its output path.

5. **Task prompts write to the retrospective deliverables store.** Each task prompt already contains instructions to write output to `comms/outbox/versions/retrospective/{VERSION}/{NNN}-{name}/`. The exploration outbox (`comms/outbox/exploration/{results_folder}/`) is for the sub-exploration's own README — the real artifacts go to the deliverables store. Do not conflate these two paths.

---

## State File Mutation Rules

**NEVER directly edit state files.** The following files are managed exclusively by MCP tools and MUST NOT be modified via Write, Edit, or any direct file operation:

- `backlog.json`
- `learnings.json`
- `product_requests.json`
- Any files under `comms/state/`

**ALL data mutations MUST use MCP tools.** Use the appropriate tool for each operation:

| Operation | Correct (MCP Tool) | FORBIDDEN (Direct Edit) |
|-----------|-------------------|------------------------|
| Complete a backlog item | `complete_backlog_item(project=..., item_id="BL-XXX")` | Editing `backlog.json` to change status |
| Add a backlog item | `add_backlog_item(project=..., title=..., ...)` | Appending an entry to `backlog.json` |
| Save a learning | `save_learning(project=..., title=..., ...)` | Editing `learnings.json` directly |
| Update a learning | `update_learning(project=..., learning_id=..., ...)` | Editing `learnings.json` directly |

**WARNING — next_id counter corruption:** Direct edits to `backlog.json` bypass the `next_id` counter increment managed by the MCP server. This causes duplicate ID collisions (e.g., two items both assigned BL-473). ALWAYS use MCP tools to ensure IDs are assigned correctly.

---

## Sub-Exploration Launch Template

For each task, use this exact pattern:

```
start_exploration(
  project=PROJECT,
  results_folder="{VERSION}-retro-{NNN}-{short-name}",
  prompt="""Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

Follow the task instructions in docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/{NNN}-{task-file}.md exactly.

PROJECT={PROJECT}
VERSION={VERSION}

Output Requirements:
- Save task artifacts to comms/outbox/versions/retrospective/{VERSION}/{NNN}-{name}/ as specified in the task prompt
- Save a README.md to comms/outbox/exploration/{VERSION}-retro-{NNN}-{short-name}/ summarizing what was produced
- Commit all changes with descriptive messages
""",
  allowed_mcp_tools=[...tools listed in the task prompt's "Allowed MCP Tools" section...]
)
```

**Mapping for each task:**

| Task | results_folder | Task file | Allowed MCP Tools |
|------|---------------|-----------|-------------------|
| 001 | `{VERSION}-retro-001-env` | `001-environment-verification.md` | health_check, get_project_info, get_version_status, git_read, read_document |
| 002 | `{VERSION}-retro-002-docs` | `002-documentation-completeness.md` | read_document, get_version_status, get_theme_status |
| 003 | `{VERSION}-retro-003-backlog` | `003-backlog-verification.md` | read_document, get_backlog_item, list_backlog_items, complete_backlog_item |
| 004 | `{VERSION}-retro-004-quality` | `004-quality-gates.md` | run_quality_gates, read_document |
| 005 | `{VERSION}-retro-005-arch` | `005-architecture-alignment.md` | list_backlog_items, get_backlog_item, update_backlog_item, add_backlog_item, read_document |
| 006 | `{VERSION}-retro-006-learn` | `006-learning-extraction.md` | read_document, save_learning, list_learnings, extract_learnings |
| 007 | `{VERSION}-retro-007-proposals` | `007-stage1-proposals.md` | read_document, add_backlog_item |
| 008 | `{VERSION}-retro-008-closure` | `008-generic-closure.md` | read_document, git_read |
| 009 | `{VERSION}-retro-009-project` | `009-project-specific-closure.md` | read_document, health_check, run_quality_gates, start_exploration, get_exploration_status, get_exploration_result, list_backlog_items, add_backlog_item, git_read |
| 010 | `{VERSION}-retro-010-final` | `010-finalization.md` | read_document, run_quality_gates, complete_version, commit_changes, git_read |
| 011 | `{VERSION}-retro-011-cross-version` | `011-cross-version-analysis.md` | read_document, get_server_logs, list_backlog_items, list_learnings, search_learnings, add_product_request |

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

**For each task below, the procedure is identical:**
1. Read the task prompt file (ONE file only — the one you are about to launch)
2. Launch a sub-exploration using the template above
3. Poll with `get_exploration_status` at 30-second minimum intervals
4. When complete, call `get_exploration_result` to verify documents were produced
5. If the sub-exploration failed or produced 0 documents, document the failure and STOP
6. Proceed to the next task

### Phase 1: Verification (Tasks 001-004)

**Task 001:** Environment verification
- Task prompt: `task_prompts/001-environment-verification.md`
- Deliverables store output: `comms/outbox/versions/retrospective/{VERSION}/001-environment/`

**Task 002:** Documentation completeness
- Task prompt: `task_prompts/002-documentation-completeness.md`
- Deliverables store output: `comms/outbox/versions/retrospective/{VERSION}/002-documentation/`

**Task 003:** Backlog verification
- Task prompt: `task_prompts/003-backlog-verification.md`
- Deliverables store output: `comms/outbox/versions/retrospective/{VERSION}/003-backlog/`

**Task 004:** Quality gates
- Task prompt: `task_prompts/004-quality-gates.md`
- Deliverables store output: `comms/outbox/versions/retrospective/{VERSION}/004-quality/`

### Phase 2: Analysis (Tasks 005-006)

**Task 005:** Architecture alignment
- Task prompt: `task_prompts/005-architecture-alignment.md`
- Deliverables store output: `comms/outbox/versions/retrospective/{VERSION}/005-architecture/`

**Task 006:** Learning extraction
- Task prompt: `task_prompts/006-learning-extraction.md`
- Deliverables store output: `comms/outbox/versions/retrospective/{VERSION}/006-learnings/`

**COMMIT:** After Task 006, commit verification and analysis artifacts:
```bash
git add comms/outbox/versions/retrospective/{VERSION}/
git commit -m "docs({VERSION}): retrospective verification and analysis artifacts"
git push
```

### Phase 3: Remediation (Task 007)

**Task 007:** Stage 1 proposals compilation
- Task prompt: `task_prompts/007-stage1-proposals.md`
- Deliverables store output: `comms/outbox/versions/retrospective/{VERSION}/007-proposals/`

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
- Task prompt: `task_prompts/008-generic-closure.md`
- Deliverables store output: `comms/outbox/versions/retrospective/{VERSION}/008-closure/`

**Task 009:** Project-specific closure
- Task prompt: `task_prompts/009-project-specific-closure.md`
- Deliverables store output: `comms/outbox/versions/retrospective/{VERSION}/009-project-closure/`
- Note: This task always runs. It evaluates project-specific closure needs based on the version's actual changes, then executes the VERSION_CLOSURE.md checklist if present.

### Phase 5: Finalization (Task 010)

**Task 010:** Finalization
- Task prompt: `task_prompts/010-finalization.md`
- Deliverables store output: `comms/outbox/versions/retrospective/{VERSION}/010-finalization/`

### Phase 6: Cross-Version Retrospective (Conditional)

**Condition:** Execute this phase ONLY if `int(VERSION[1:]) % 5 == 0` (i.e., versions v050, v055, v060, v065, etc.)

```python
if int(VERSION[1:]) % 5 == 0:
    # Launch Task 011: Cross-Version Analysis
else:
    # Skip — no output, no action
```

**If the condition is met:**

**Task 011:** Cross-version analysis
- Task prompt: `task_prompts/011-cross-version-analysis.md`
- Deliverables store output: `comms/outbox/versions/retrospective/{VERSION}/011-cross-version/`
- Create the `011-cross-version/` subfolder in the deliverables structure before launching

**If the condition is NOT met:**
- Skip this phase entirely — no output, no action, no folder creation

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
- [ ] Task 009: Project-specific closure
- [ ] Task 010: Finalization
- [ ] Task 011: Cross-version analysis (conditional: `int(VERSION[1:]) % 5 == 0`)

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
