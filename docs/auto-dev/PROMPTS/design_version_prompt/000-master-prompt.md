# Version Design Orchestrator v3 - Master Prompt

**PROJECT CONFIGURATION:**
```
PROJECT=[SET_PROJECT_NAME_HERE]
```

**CRITICAL:** Set the PROJECT variable above before proceeding.

---

## Orchestrator Rules

**Your ONLY job is to launch sub-explorations and poll them to completion. Follow these rules strictly:**

1. **NEVER execute task work inline.** You are an orchestrator, not a worker. Every task (001–009) MUST be delegated to a sub-exploration via `start_exploration`. Do not write files, run health checks, or analyze backlog items yourself.

2. **Read each task prompt ONLY when you are about to launch it.** Do not read task prompts in advance or in batches. This wastes your context budget.

3. **Poll sub-explorations with 30-second minimum intervals.** After calling `get_exploration_status`, wait at least 30 seconds before polling again. Sub-explorations typically take 3–10 minutes.

4. **Use the sub-exploration launch template exactly.** See the template below. The `results_folder` must follow the pattern `design-{VERSION}-{NNN}-{short-name}`. The prompt must reference `comms/outbox/exploration/{results_folder}/` as its output path (not the design artifact store path).

5. **Task prompts write to the design artifact store.** Each task prompt already contains instructions to write output to `comms/outbox/versions/design/{VERSION}/{NNN}-{name}/`. The exploration outbox (`comms/outbox/exploration/{results_folder}/`) is for the sub-exploration's own README — the real artifacts go to the design store. Do not conflate these two paths.

---

## Sub-Exploration Launch Template

For each task, use this exact pattern:

```
start_exploration(
  project=PROJECT,
  results_folder="design-{VERSION}-{NNN}-{short-name}",
  prompt="""Read AGENTS.md first and follow all instructions there.

Follow the task instructions in docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/{NNN}-{task-file}.md exactly.

PROJECT={PROJECT}
VERSION={VERSION}

Output Requirements:
- Save task artifacts to comms/outbox/versions/design/{VERSION}/{NNN}-{name}/ as specified in the task prompt
- Save a README.md to comms/outbox/exploration/design-{VERSION}-{NNN}-{short-name}/ summarizing what was produced
- Commit all changes with descriptive messages
""",
  allowed_mcp_tools=[...tools listed in the task prompt's "Allowed MCP Tools" section...]
)
```

**Mapping for each task:**

| Task | results_folder | Task file | Allowed MCP Tools |
|------|---------------|-----------|-------------------|
| 001 | `design-{VERSION}-001-env` | `001-environment-verification.md` | health_check, get_project_info, git_read, read_document, list_product_requests, get_product_request, add_product_request, update_product_request, upvote_item |
| 002 | `design-{VERSION}-002-backlog` | `002-backlog-analysis.md` | get_backlog_item, list_backlog_items, search_learnings, read_document, list_product_requests, get_product_request, add_product_request, update_product_request, upvote_item |
| 003 | `design-{VERSION}-003-impact` | `003-impact-assessment.md` | request_clarification, read_document, list_product_requests, get_product_request, add_product_request, update_product_request, upvote_item |
| 004 | `design-{VERSION}-004-research` | `004-research-investigation.md` | request_clarification, read_document, start_exploration, get_exploration_status, get_exploration_result, get_backlog_item, list_product_requests, get_product_request, add_product_request, update_product_request, upvote_item |
| 005 | `design-{VERSION}-005-logical` | `005-logical-design.md` | read_document, list_product_requests, get_product_request, add_product_request, update_product_request, upvote_item |
| 006 | `design-{VERSION}-006-critical` | `006-critical-thinking.md` | request_clarification, read_document, list_product_requests, get_product_request, add_product_request, update_product_request, upvote_item |
| 007 | `design-{VERSION}-007-drafts` | `007-document-drafts.md` | read_document, list_product_requests, get_product_request, add_product_request, update_product_request, upvote_item |
| 008 | `design-{VERSION}-008-persist` | `008-persist-documents.md` | read_document, design_version, design_theme, validate_version_design, list_product_requests, get_product_request, add_product_request, update_product_request, upvote_item |
| 009 | `design-{VERSION}-009-validation` | `009-pre-execution-validation.md` | read_document, validate_version_design, get_backlog_item, list_product_requests, get_product_request, add_product_request, update_product_request, upvote_item |

---

## Pre-Execution Validation

**STEP 1:** Verify PROJECT variable is set.

```python
if PROJECT == "[SET_PROJECT_NAME_HERE]" or not PROJECT or PROJECT.strip() == "":
    print("ERROR: PROJECT variable not set.")
    STOP IMMEDIATELY
```

**STEP 2:** Read `docs/auto-dev/PLAN.md` and derive the next version number.

```python
# Find "Planned Versions" section
# Extract the FIRST planned version entry (format: ### vXXX - Title)
# If no planned versions exist, ERROR and STOP
# Set: VERSION = "vXXX"
```

**STEP 3:** Verify version folder does NOT exist.

```python
# Check: comms/inbox/versions/execution/{VERSION}/ must NOT exist
# If it exists, ERROR: "Version {VERSION} already has design documents."
# STOP IMMEDIATELY
```

**STEP 4:** Create the design artifact store.

```python
# Create: comms/outbox/versions/design/{VERSION}/
# Subfolders created by individual tasks:
#   001-environment/
#   002-backlog/
#   003-impact-assessment/
#   004-research/
#   005-logical-design/
#   006-critical-thinking/
```

**If ANY validation fails, output a clear error message and STOP.**

---

## Test Target Project Awareness

Some features affect cross-project tooling (MCP tools, git operations, exploration) and should be validated against destructive test target projects during implementation.

**During Task 005 (Logical Design):** When proposing themes and features, identify any features that modify cross-project behavior. Flag these in the test strategy as requiring test-target validation. Registered test target projects (with `destructive_test_target: true` in `projects.yaml`) exist specifically for safe destructive testing.

**During Task 007 (Document Drafts):** For features flagged for test-target validation, include test-target steps in the implementation plan (e.g., "validate against a registered test target project using `test_target_reset` in `git_write`").

Features that only affect internal logic or single-project documentation do not need test-target steps.

---

## Task Execution Flow

**For each task below, the procedure is identical:**
1. Read the task prompt file (ONE file only — the one you are about to launch)
2. Launch a sub-exploration using the template above
3. Poll with `get_exploration_status` at 30-second minimum intervals
4. When complete, call `get_exploration_result` to verify documents were produced
5. If the sub-exploration failed or produced 0 documents, document the failure and STOP
6. Proceed to the next task

### Phase 1: Environment & Investigation (Tasks 001-004)

**Task 001:** Environment verification
- Task prompt: `task_prompts/001-environment-verification.md`
- Design store output: `comms/outbox/versions/design/{VERSION}/001-environment/`

**Task 002:** Backlog analysis
- Task prompt: `task_prompts/002-backlog-analysis.md`
- Design store output: `comms/outbox/versions/design/{VERSION}/002-backlog/`

**Task 003:** Impact assessment
- Task prompt: `task_prompts/003-impact-assessment.md`
- Design store output: `comms/outbox/versions/design/{VERSION}/003-impact-assessment/`

**Task 004:** Research investigation
- Task prompt: `task_prompts/004-research-investigation.md`
- Design store output: `comms/outbox/versions/design/{VERSION}/004-research/`

### Phase 2: Logical Design & Critical Thinking (Tasks 005-006)

**Task 005:** Logical design proposal
- Task prompt: `task_prompts/005-logical-design.md`
- Design store output: `comms/outbox/versions/design/{VERSION}/005-logical-design/`

**Task 006:** Critical thinking and risk investigation
- Task prompt: `task_prompts/006-critical-thinking.md`
- Design store output: `comms/outbox/versions/design/{VERSION}/006-critical-thinking/`

**COMMIT:** After Task 006, commit the design artifact store:
```bash
git add comms/outbox/versions/design/{VERSION}/
git commit -m "design: {VERSION} design artifacts (phases 1-2)"
git push
```

### Phase 3: Document Drafts & Persistence (Tasks 007-008)

**Task 007:** Document drafts
- Task prompt: `task_prompts/007-document-drafts.md`
- Exploration output: `comms/outbox/exploration/design-{VERSION}-007-drafts/`

**Task 008:** Persist documents to inbox
- Task prompt: `task_prompts/008-persist-documents.md`
- Exploration output: `comms/outbox/exploration/design-{VERSION}-008-persist/`

### Phase 4: Validation (Task 009)

**Task 009:** Pre-execution validation (READ-ONLY)
- Task prompt: `task_prompts/009-pre-execution-validation.md`
- Exploration output: `comms/outbox/exploration/design-{VERSION}-009-validation/`

---

## Error Handling

Between each task:
1. Check exploration status
2. If "failed", document the failure and STOP
3. If "complete", read result to verify output documents exist
4. Only proceed if current task succeeded

---

## Progress Tracking

- [ ] Validation: PROJECT set
- [ ] Validation: VERSION derived from PLAN.md
- [ ] Validation: Version folder does not exist
- [ ] Validation: Design artifact store created
- [ ] Task 001: Environment verification
- [ ] Task 002: Backlog analysis
- [ ] Task 003: Impact assessment
- [ ] Task 004: Research investigation
- [ ] Task 005: Logical design
- [ ] Task 006: Critical thinking
- [ ] COMMIT: Design artifacts (phases 1-2)
- [ ] Task 007: Document drafts
- [ ] Task 008: Persist documents
- [ ] Task 009: Pre-execution validation

---

## Completion

When all tasks complete:
1. Verify design documents exist in `comms/inbox/versions/execution/{VERSION}/`
2. Run `validate_version_design(project=PROJECT, version=VERSION)`
3. If validation passes, output success message
4. If validation fails, document missing items and require manual intervention

---

## Usage

1. Set PROJECT variable at the top
2. Run this prompt via exploration or directly in Claude Code
3. Monitor progress — orchestrator executes all 9 tasks sequentially
4. Handle failures — investigate and fix before retrying
