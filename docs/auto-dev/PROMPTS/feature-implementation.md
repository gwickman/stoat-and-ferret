# Feature Implementation Prompt

First, call the Read tool with file_path='AGENTS.md' to read the project guidelines.
Then follow every instruction in AGENTS.md, including the mandatory PR workflow.

## BEFORE Writing Any Code

Create and checkout a feature branch:

```bash
git checkout -b {version}/{theme}/{feature}
```

**All commits MUST go to this branch, NOT to main.**

## Context

You are implementing a feature as part of the auto-dev MCP workflow.

**Version:** {version}
**Theme:** {theme}
**Feature:** {feature}

## Input Documents

Use the Read tool to read these files before starting:

1. **Requirements:** `comms/inbox/versions/execution/{version}/{theme}/{feature}/requirements.md`
2. **Implementation Plan:** `comms/inbox/versions/execution/{version}/{theme}/{feature}/implementation-plan.md`

## Code Quality Principles

Follow: KISS + YAGNI first. Refactor to DRY/SOLID after duplication or change demonstrated.

- [ ] No speculative abstractions
- [ ] No unused extension points
- [ ] No premature optimization

## Implementation Steps

1. **Read the requirements and plan** - Use Read tool to understand acceptance criteria
2. **Implement the feature** - Follow the staged plan, use Write/Edit tools
3. **Run quality gates** - Use Bash tool to run pytest, ruff, mypy
4. **Fix any failures** - Max 3 attempts per failure type
5. **Create output documents** - Use Write tool to create files below
6. **Commit and push** - Use Bash tool for git commands per AGENTS.md PR workflow

## Quality Gates

Use Bash tool to run these before considering the feature complete:

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest -v
```

## Output Documents

Use Write tool to create these in `comms/outbox/versions/execution/{version}/{theme}/{feature}/`:

1. **completion-report.md** - MUST start with YAML frontmatter on line 1 (no title before it):
   ```markdown
   ---
   status: complete
   acceptance_passed: X
   acceptance_total: Y
   quality_gates:
     ruff: pass
     mypy: pass
     pytest: pass
   ---
   # Completion Report: {feature}

   ## Summary
   ...
   ```
   CRITICAL: The `---` must be the very first line. Do not put a heading before it.
2. **quality-gaps.md** - Document any gaps or tech debt (optional)
3. **handoff-to-next.md** - Context for next feature implementer (optional)

## Completion Criteria

The feature is complete when:

- [ ] All acceptance criteria from requirements.md met
- [ ] All quality gates pass
- [ ] completion-report.md created with valid YAML frontmatter
- [ ] Changes committed and pushed via PR workflow

## On Failure

If you cannot complete the feature:

1. Use Write tool to document blockers in quality-gaps.md
2. Set `status: failed` or `status: partial` in completion-report.md
3. Explain what was completed and what remains
