Read AGENTS.md first and follow all instructions there.

Follow the master orchestrator instructions in docs/auto-dev/PROMPTS/design_version_prompt/000-master-prompt.md exactly. You are the Version Design Orchestrator.

PROJECT=stoat-and-ferret
VERSION=v010

CRITICAL CONTEXT — RESUMING FROM INTERRUPTION:
The previous orchestrator run completed tasks 001 through 007 successfully. All sub-explorations for those tasks finished and committed their artifacts. You can verify this by checking the existing explorations:
- design-v010-001-env: complete
- design-v010-002-backlog: complete
- design-v010-003-impact: complete
- design-v010-004-research: complete
- design-v010-005-logical: complete
- design-v010-006-critical: complete
- design-v010-007-drafts: complete

DO NOT re-run tasks 001–007. They are done. Skip directly to launching task 008 (persist documents), then 009 (pre-execution validation).

The design artifact store already exists at comms/outbox/versions/design/v010/ with artifacts from tasks 001–007.

Output Requirements:
- Launch tasks 008 and 009 sequentially using the master prompt's sub-exploration launch template
- Save a README.md to comms/outbox/exploration/design-v010-resume/ summarizing orchestration results for tasks 008–009
- Commit all changes with descriptive messages