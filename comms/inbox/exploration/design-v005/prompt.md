## Version Design Orchestrator

Follow the instructions in `docs/auto-dev/PROMPTS/design_version_prompt/000-master-prompt.md` exactly.

**PROJECT CONFIGURATION:**
```
PROJECT=stoat-and-ferret
```

The target version is **v005** (the smallest planned version from plan.md).

Read the master prompt file first, then execute all tasks sequentially as described. Each task has its own prompt file under `docs/auto-dev/PROMPTS/design_version_prompt/prompts/task_prompts/`. Read each task prompt before executing it.

Use `start_exploration` to launch sub-explorations for each task, `get_exploration_status` to poll for completion, and `get_exploration_result` to verify outputs. Use `read_document` to read prompt files and verify artifacts. Use `request_clarification` when you need to query the codebase.

**Output Requirements:**
- All design artifacts as specified in the master prompt
- README.md summarizing orchestration results in `comms/outbox/exploration/design-v005/`
- Progress tracking showing which tasks completed/failed

**Commit instructions:**
- Commit design artifacts after Phase 2 as specified in the master prompt
- Commit final documents after Phase 3-4 completion
