Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

Follow the task instructions in docs/auto-dev/PROMPTS/retrospective_prompt/task_prompts/010-finalization.md exactly.

PROJECT=stoat-and-ferret
VERSION=v006

Note: The task prompt references "commit_changes" but that tool doesn't exist. Use "git_write" instead for committing and pushing changes.

Output Requirements:
- Save task artifacts to comms/outbox/versions/retrospective/v006/010-finalization/ as specified in the task prompt
- Save a README.md to comms/outbox/exploration/v006-retro-010-final/ summarizing what was produced
- Commit all changes with descriptive messages