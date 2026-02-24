Read AGENTS.md first and follow all instructions there.

Follow the instructions in docs/auto-dev/PROMPTS/design_version_prompt/000-master-prompt.md exactly. You are the Version Design Orchestrator. Your job is to launch sub-explorations (tasks 001-009) sequentially, polling each to completion before launching the next.

PROJECT=stoat-and-ferret
VERSION=v011

Output Requirements:
- Follow the master prompt's sub-exploration launch template for each task (001-009)
- Each sub-task writes its artifacts to comms/outbox/versions/design/v011/{NNN}-{name}/ as specified
- Save a README.md to comms/outbox/exploration/design-v011/ summarizing overall orchestration results
- Commit all changes with descriptive messages
