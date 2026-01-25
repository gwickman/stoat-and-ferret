# v001 Starter Prompt

## Instructions

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Process

1. Read `comms/inbox/versions/execution/v001/THEME_INDEX.md` for the execution order
2. For each theme in order:
   a. Read the theme's `THEME_DESIGN.md`
   b. For each feature:
      - Read `requirements.md` and `implementation-plan.md`
      - Implement the feature
      - Run quality gates
      - Create output documents (completion-report.md, quality-gaps.md, handoff-to-next.md)
      - Update STATUS.md
   c. Create theme retrospective
3. Create version retrospective
4. Update docs/CHANGELOG.md

## Status Tracking

Update `comms/outbox/versions/execution/v001/STATUS.md` after each feature:
- Mark features as complete/partial/failed
- Update current position
- Add completion notes

## Output Documents

For each feature, create in the feature's outbox folder:
- `completion-report.md` with YAML frontmatter
- `quality-gaps.md` documenting any gaps
- `handoff-to-next.md` with context for next feature

## Quality Gates

All must pass before marking feature complete:

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest -v
```
