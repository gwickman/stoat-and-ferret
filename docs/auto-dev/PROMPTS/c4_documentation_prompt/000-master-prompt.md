# C4 Architecture Documentation Orchestrator - Master Prompt

**PROJECT CONFIGURATION:**
```
PROJECT=[SET_PROJECT_NAME_HERE]
VERSION=[SET_VERSION_HERE]
MODE=auto
PUSH=true        # Set to false to commit locally without pushing
```

**MODE options:**
- `auto` — Checks for existing C4 docs; runs delta if found and current version has changes, full otherwise
- `full` — Full regeneration regardless of existing state
- `delta` — Delta only; fails if no existing C4 docs found

**CRITICAL:** Set PROJECT and VERSION variables above before proceeding.

---

## MCP Tool Authorization

Extract the autoDevToolKey from your initial prompt if present:
- Pattern: `autoDevToolKey: ([a-f0-9-]{36})`
- Include in all MCP tool calls to auto-dev-mcp

---

## Variable Substitution

Task prompts use `${VARIABLE}` placeholders. Before passing a task prompt to `start_exploration()`, the orchestrator MUST:

1. Read the task prompt file content
2. Replace all `${VARIABLE}` tokens with actual values using string replacement
3. For `${BATCH_DIRECTORIES}`, insert the actual directory list from the manifest as a markdown list
4. Pass the fully-resolved prompt string to `start_exploration(prompt=resolved_prompt)`

**Example for Task 002 batch launch:**
```python
task_template = read_document("docs/auto-dev/PROMPTS/c4_documentation_prompt/task_prompts/002-code-level-analysis.md")
prompt = task_template
    .replace("${PROJECT}", PROJECT)
    .replace("${VERSION}", VERSION)
    .replace("${BATCH_NUMBER}", str(batch_num))
    .replace("${BATCH_COUNT}", str(total_batches))
    .replace("${BATCH_DIRECTORIES}", batch_directory_list)
start_exploration(project=PROJECT, prompt=prompt, results_folder=f"c4-{VERSION}-002-batch{batch_num}")
```

NOTE: results_folder must have at most 5 hyphen-separated parts. Use compact names like "c4-v003-002-batch1".

**Variables used across tasks:**
| Variable | Source | Used In |
|----------|--------|---------|
| `${PROJECT}` | Config block | All tasks |
| `${VERSION}` | Config block | All tasks |
| `${MODE}` | Determined in Step 4 | 001, 003, 006 |
| `${PREVIOUS_VERSION}` | Extracted from existing README.md | 001 |
| `${PREVIOUS_C4_COMMIT}` | Git SHA from Step 4 | 001 |
| `${BATCH_NUMBER}` | Loop counter (1..N) | 002 |
| `${BATCH_COUNT}` | From manifest | 002 |
| `${BATCH_DIRECTORIES}` | From manifest, per-batch | 002 |

---

## Overview

This prompt orchestrates C4 architecture documentation generation using the exploration framework. It follows the C4 model (Code → Component → Container → Context) with bottom-up analysis.

**Key differences from the plugin approach:**
- Code-level analysis runs as **parallel exploration batches** for scalability
- **Delta mode** only reprocesses directories with changes since last generation
- Each phase gets its own clean context window (no context limit issues)
- All work flows through `comms/outbox/exploration/c4-*` before persisting to `docs/C4-Documentation/`

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

**STEP 3:** Check git status.

```python
result = git_read(project=PROJECT, operation="status")
# Note current branch and any uncommitted changes
```

**STEP 4:** Determine execution mode.

```python
# Check for existing C4 documentation
c4_readme = read_document(project=PROJECT, path="docs/C4-Documentation/README.md")

if MODE == "auto":
    if c4_readme exists and has "Generated for Version" field:
        previous_version = extract version string from c4_readme (e.g., "v005")
        # Find the commit SHA where C4 docs were last generated
        # Search by the standardized commit message format
        c4_commit = git_read output of:
            git log --oneline --format="%H" --grep="docs(c4):.*finalized" -1 -- docs/C4-Documentation/README.md
        if c4_commit found:
            PREVIOUS_C4_COMMIT = c4_commit
            MODE = "delta"
        else:
            # Can't find previous commit reliably — fall back to full
            MODE = "full"
    else:
        MODE = "full"
elif MODE == "delta":
    if c4_readme does not exist:
        STOP: "ERROR: Delta mode requires existing C4 documentation."
    previous_version = extract version string from c4_readme
    c4_commit = git log --oneline --format="%H" --grep="docs(c4):.*finalized" -1 -- docs/C4-Documentation/README.md
    if not c4_commit:
        STOP: "ERROR: Cannot find previous C4 generation commit. Use MODE=full."
    PREVIOUS_C4_COMMIT = c4_commit
```

**CRITICAL:** The final commit message MUST use the exact format `docs(c4): ${VERSION} C4 documentation finalized (${MODE} mode)`. Delta mode detection depends on matching the pattern `docs(c4):.*finalized` in git log. Do not modify, reword, squash, or amend these commit messages — doing so will silently break delta mode for future runs.

**STEP 5:** Log mode decision.

```
Mode: {MODE}
Previous C4 Version: {previous_version or "N/A"}
Current Version: {VERSION}
```

**If ANY validation fails, output a clear error message and STOP.**

---

## Task Execution Flow

### Phase 1: Discovery & Planning (Task 001)

**Task 001:** Discovery and directory manifest
- Read: `docs/auto-dev/PROMPTS/c4_documentation_prompt/task_prompts/001-discovery-and-planning.md`
- Substitute: `${PROJECT}`, `${VERSION}`, `${MODE}`, `${PREVIOUS_VERSION}`, `${PREVIOUS_C4_COMMIT}`
- Output: `comms/outbox/exploration/c4-${VERSION}-001-discovery/`
- Start exploration → poll → verify

**After Task 001 completes:**
- Read `comms/outbox/exploration/c4-${VERSION}-001-discovery/directory-manifest.md`
- Extract the list of directories to process
- Extract the recommended batch groupings
- If MODE is delta, extract the list of changed directories
- Set `BATCH_COUNT` = number of batches from manifest
- Set `DIRECTORIES_PER_BATCH` from manifest

**If manifest reports 0 directories to process (delta mode, no changes):**
- Skip to Phase 5 (Finalization) with "no changes" status
- Update README.md timestamp only

---

### Phase 2: Code-Level Analysis (Task 002 — PARALLEL BATCHES)

**For each batch N (1 to BATCH_COUNT), launch in PARALLEL:**

- Read: `docs/auto-dev/PROMPTS/c4_documentation_prompt/task_prompts/002-code-level-analysis.md`
- Substitute: `${PROJECT}`, `${VERSION}`, `${BATCH_NUMBER}`, `${BATCH_DIRECTORIES}` (from manifest)
- Results folder: `c4-${VERSION}-002-batch${N}`
- Start exploration (do NOT wait — launch all batches)

**After launching all batches:**
```python
exploration_ids = [id_1, id_2, ..., id_N]
# Poll all explorations until all complete
for eid in exploration_ids:
    while get_exploration_status(project=PROJECT, exploration_id=eid).status != "complete":
        wait(30 seconds)
        check status
    verify result has README.md
```

**If any batch fails:** Document the failure, note which directories were in that batch, and continue with remaining batches. Failed directories will be missing from component synthesis.

**Parallel write safety:** Each batch writes to distinct files (`c4-code-[different-dir-name].md`) so parallel explorations do not conflict. The commit occurs only after all batches complete, ensuring all files are captured atomically.

**COMMIT after all batches complete:**
```python
git_write(project=PROJECT, message="docs(c4): ${VERSION} code-level analysis complete", push=PUSH)
```

---

### Phase 3: Component Synthesis (Task 003)

**Task 003:** Synthesize code docs into components
- Read: `docs/auto-dev/PROMPTS/c4_documentation_prompt/task_prompts/003-component-synthesis.md`
- Substitute: `${PROJECT}`, `${VERSION}`, `${MODE}`
- Output: `comms/outbox/exploration/c4-${VERSION}-003-components/`
- Start exploration → poll → verify

---

### Phase 4: Container & Context Synthesis (Tasks 004-005 — SEQUENTIAL)

**Task 004:** Container-level synthesis
- Read: `docs/auto-dev/PROMPTS/c4_documentation_prompt/task_prompts/004-container-synthesis.md`
- Substitute: `${PROJECT}`, `${VERSION}`
- Output: `comms/outbox/exploration/c4-${VERSION}-004-containers/`
- Start exploration → poll → verify

**Task 005:** Context-level synthesis
- Read: `docs/auto-dev/PROMPTS/c4_documentation_prompt/task_prompts/005-context-synthesis.md`
- Substitute: `${PROJECT}`, `${VERSION}`
- Output: `comms/outbox/exploration/c4-${VERSION}-005-context/`
- Start exploration → poll → verify

**COMMIT after Phase 4:**
```python
git_write(project=PROJECT, message="docs(c4): ${VERSION} component/container/context synthesis complete", push=PUSH)
```

---

### Phase 5: Finalization (Task 006)

**Task 006:** README generation and validation
- Read: `docs/auto-dev/PROMPTS/c4_documentation_prompt/task_prompts/006-finalization.md`
- Substitute: `${PROJECT}`, `${VERSION}`, `${MODE}`
- Output: `comms/outbox/exploration/c4-${VERSION}-006-finalize/`
- Start exploration → poll → verify

**FINAL COMMIT after Task 006:**
```python
git_write(project=PROJECT, message="docs(c4): ${VERSION} C4 documentation finalized (${MODE} mode)", push=PUSH)
```

---

## Error Handling

Between each task (except parallel batches which are handled above):
1. Check exploration status via `get_exploration_status`
2. If "failed", document the failure and STOP
3. If "complete", read result to verify output README.md exists
4. Only proceed to next task if current task succeeded

For parallel batch failures:
- Document which batch failed and which directories it contained
- Continue with remaining batches
- Note gaps in component synthesis task prompt

---

## Progress Tracking

- [ ] Validation: PROJECT and VERSION set
- [ ] Validation: Project exists
- [ ] Validation: Mode determined (full/delta)
- [ ] Task 001: Discovery and planning
- [ ] Task 002: Code-level batches launched (count: ___)
- [ ] Task 002: All code-level batches complete
- [ ] COMMIT: Code-level analysis
- [ ] Task 003: Component synthesis
- [ ] Task 004: Container synthesis
- [ ] Task 005: Context synthesis
- [ ] COMMIT: Component/container/context
- [ ] Task 006: Finalization

---

## Completion

When all tasks complete:
1. Verify `docs/C4-Documentation/README.md` exists with current timestamp
2. Verify all expected C4 level files exist
3. Output summary:
   - Mode used (full/delta)
   - Directories processed
   - Components identified
   - Containers mapped
   - Any gaps or failures

---

## Output Structure

```
docs/C4-Documentation/
├── README.md                  # Index with timestamp and version
├── c4-context.md              # Level 1: System context
├── c4-container.md            # Level 2: Container architecture
├── c4-component.md            # Level 3: Master component index
├── c4-component-*.md          # Level 3: Individual components
├── c4-code-*.md               # Level 4: Code-level docs (one per directory)
└── apis/                      # OpenAPI specs (only created if network APIs exist)
    └── *.yaml
```

---

## Usage

```
# Full regeneration
PROJECT=auto-dev-test-target-1 VERSION=v005 MODE=full PUSH=true

# Delta update after a version
PROJECT=auto-dev-test-target-1 VERSION=v006 MODE=auto PUSH=true

# Force delta only
PROJECT=auto-dev-test-target-1 VERSION=v006 MODE=delta PUSH=true

# Local-only (commit without pushing to remote)
PROJECT=auto-dev-test-target-1 VERSION=v005 MODE=full PUSH=false
```
