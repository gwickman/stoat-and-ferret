Read AGENTS.md first and follow all instructions there.

Follow the task instructions in docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/007-document-drafts.md exactly.

PROJECT=stoat-and-ferret
VERSION=v006

IMPORTANT NOTE about the design artifact store:
- Task 005 produced only `comms/outbox/versions/design/v006/005-logical-design/logical-design.md` (no separate risks-and-unknowns.md or test-strategy.md — content is embedded in logical-design.md)
- Task 006 produced all 4 files: README.md, risk-assessment.md, refined-logical-design.md, investigation-log.md in `comms/outbox/versions/design/v006/006-critical-thinking/`
- Use Task 006's `refined-logical-design.md` as the primary design source

Output Requirements:
- Save all drafts to comms/outbox/exploration/design-v006-007-drafts/drafts/ as specified in the task prompt
- Save a README.md and draft-checklist.md to comms/outbox/exploration/design-v006-007-drafts/
- Commit all changes with descriptive messages