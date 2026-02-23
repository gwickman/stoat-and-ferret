Read AGENTS.md first and follow all instructions there.

Follow the master orchestrator instructions in docs/auto-dev/PROMPTS/design_version_prompt/000-master-prompt.md exactly. You are the Version Design Orchestrator. Your job is to launch sub-explorations for tasks 001-009 sequentially, polling each to completion before launching the next.

PROJECT=stoat-and-ferret

The target version is v010 (Async Pipeline & Job Controls) — the smallest planned version in docs/auto-dev/plan.md.

Output Requirements:
- Follow the master prompt's sub-exploration launch template for each task (001-009)
- Each sub-exploration writes its artifacts to comms/outbox/versions/design/v010/{NNN}-{name}/
- Save a README.md to comms/outbox/exploration/design-v010/ summarizing overall orchestration results
- Commit all changes with descriptive messages