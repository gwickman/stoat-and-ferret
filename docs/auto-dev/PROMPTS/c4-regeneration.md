# C4 Architecture Regeneration Prompt

**Version:** {{version}}

## CRITICAL: Use the Plugin

You MUST use the c4-architecture plugin. Do NOT manually analyze code files.

**Slash command:** `/c4-architecture:c4-architecture`
**Or natural language:** "Create C4 architecture documentation for this codebase"

## Pre-Check

Check if `C4-Documentation/` exists:
- Exists: Plugin updates existing docs
- Not exists: Plugin generates fresh docs

## README.md Requirement

After the plugin completes, create/update `C4-Documentation/README.md`:

```markdown
# C4 Architecture Documentation

**Last Updated:** [YYYY-MM-DD HH:MM UTC]
**Generated for Version:** {{version}}
**Generator:** wshobson/agents c4-architecture plugin

## Contents

[List all .md files with one-line descriptions]

## C4 Levels

- **Context** (c4-context.md): External actors and systems
- **Container** (c4-container.md): Deployment containers
- **Component** (c4-component-*.md): Internal architecture
- **Code** (c4-code-*.md): Function signatures and dependencies

## Regeneration

If stale, run: `/c4-architecture:c4-architecture`
```

## Completion

```bash
git add C4-Documentation/
git commit -m "docs: regenerate C4 architecture documentation for {{version}}"
git push
```

## Success Criteria

- [ ] C4 plugin executed successfully
- [ ] README.md exists with current timestamp
- [ ] Changes committed and pushed

Read AGENTS.md first and follow the mandatory PR workflow.
