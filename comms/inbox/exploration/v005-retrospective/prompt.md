Read AGENTS.md first and follow all instructions there.

## Objective

Execute the Post-Version Retrospective for stoat-and-ferret version v005.

## Instructions

Read and follow the master prompt at:
`docs/auto-dev/PROMPTS/retrospective_prompt/000-master-prompt.md`

Use these configuration values:
```
PROJECT=stoat-and-ferret
VERSION=v005
```

Execute ALL phases and tasks as specified in the master prompt, sequentially:
- Phase 1: Verification (Tasks 001-004)
- Phase 2: Analysis (Tasks 005-006) + commit
- Phase 3: Remediation (Task 007) + remediation exploration if needed
- Phase 4: Closure (Tasks 008-009)
- Phase 5: Finalization (Task 010)

For each task, read the corresponding task prompt file from `docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/`, launch a sub-exploration, poll for completion, and verify the output README.md exists before proceeding.

Follow all error handling, progress tracking, and completion steps in the master prompt.

## Output Requirements

Save outputs to: `comms/outbox/exploration/v005-retrospective/`

### README.md (required)
First paragraph: Summary of the v005 retrospective execution — which tasks completed, which failed, and overall status.

Then: Detailed progress log showing each task's status, key findings, and any items requiring user attention.

Commit retrospective artifacts as specified in the master prompt.