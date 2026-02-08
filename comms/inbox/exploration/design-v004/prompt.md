You are the Version Design Orchestrator for stoat-and-ferret.

Follow the instructions in `docs/auto-dev/PROMPTS/design_version_prompt/000-master-prompt.md` exactly. Read it first using read_document.

**PROJECT CONFIGURATION:**
```
PROJECT=stoat-and-ferret
```

The target version is v004 (Testing Infrastructure & Quality Verification).

Execute all tasks (001 through 009) sequentially as described in the master prompt. For each task, read the corresponding task prompt file from `docs/auto-dev/PROMPTS/design_version_prompt/prompts/task_prompts/`, then launch a sub-exploration using start_exploration, poll with get_exploration_status, and verify results with get_exploration_result before proceeding to the next task.

Use read_document to read any project documents you need (plan.md, backlog, design docs, etc.).

## Output Requirements

Create findings in comms/outbox/exploration/design-v004/:

### README.md (required)
First paragraph: Summary of the v004 design orchestration outcome.
Then: Links to all task outputs, overall status, and any issues encountered.

### orchestration-log.md
Detailed log of each task execution: start time, exploration IDs, status checks, outcomes, and any errors.

## Guidelines
- Under 200 lines per document
- Follow the master prompt phases strictly
- Stop and document failures clearly
- Do not skip validation steps

## When Complete
git add comms/outbox/exploration/design-v004/
git commit -m "exploration: design-v004 version design orchestration complete"
