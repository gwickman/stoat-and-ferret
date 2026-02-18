Read AGENTS.md first and follow all instructions there.

Follow the instructions in docs/auto-dev/PROMPTS/design_version_prompt/000-master-prompt.md exactly. You are the Version Design Orchestrator. Your job is to launch sub-explorations for each task (001–009) and poll them to completion, following the orchestrator rules strictly.

PROJECT=stoat-and-ferret
VERSION=v006

Output Requirements:
- Execute all tasks (001–009) as sub-explorations per the master prompt template
- Save a README.md to comms/outbox/exploration/design-v006/ summarizing orchestration results
- Commit all changes with descriptive messages
