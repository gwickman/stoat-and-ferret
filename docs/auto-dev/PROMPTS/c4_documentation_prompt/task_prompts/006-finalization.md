# Task 006: Finalization

Read AGENTS.md first and follow all instructions there.

## Objective

Create the C4 Documentation README index, validate all expected files exist, and prepare the final commit. This is the cleanup and verification step.

## Context

C4 architecture documentation generation for `${PROJECT}` version `${VERSION}`.
- **Mode:** `${MODE}`
- All C4 level documents should now exist in `docs/C4-Documentation/`

## Tasks

### 1. Inventory All C4 Files

List everything in `docs/C4-Documentation/`:
- `c4-context.md` — must exist
- `c4-container.md` — must exist
- `c4-component.md` — must exist (master index)
- `c4-component-*.md` — at least one must exist
- `c4-code-*.md` — at least one must exist
- `apis/*.yaml` — may or may not exist (depends on whether APIs were found)

### 2. Validate Cross-References

Spot-check that links between documents are valid:
- `c4-context.md` links to `c4-container.md` and `c4-component.md`
- `c4-container.md` references component docs that exist
- `c4-component.md` master index links to individual component files
- Component files reference code-level files that exist

**Do not exhaustively validate every link** — spot-check 3-5 cross-references per level.

### 3. Check Mermaid Diagrams

Spot-check that Mermaid diagrams in each level file:
- Use correct C4 syntax (C4Context, C4Container, C4Component)
- Have a title
- Are not empty
- Reference entities that exist in the documentation

### 4. Create/Update README.md

Create `docs/C4-Documentation/README.md`:

```markdown
# C4 Architecture Documentation

**Last Updated:** [YYYY-MM-DD HH:MM UTC]
**Generated for Version:** ${VERSION}
**Generation Mode:** ${MODE}
**Generator:** auto-dev-mcp C4 documentation prompt

## Quick Reference

| Level | Document | Description |
|-------|----------|-------------|
| Context | [c4-context.md](./c4-context.md) | System context, personas, user journeys |
| Container | [c4-container.md](./c4-container.md) | Deployment containers, APIs, infrastructure |
| Component | [c4-component.md](./c4-component.md) | Component index and relationships |
| Code | c4-code-*.md | Per-directory code analysis |

## C4 Levels Explained

- **Context** (c4-context.md): Who uses the system and what other systems does it talk to? Start here for orientation.
- **Container** (c4-container.md): What are the running processes, databases, and services? Read this for deployment understanding.
- **Component** (c4-component.md + c4-component-*.md): What are the logical modules inside each container? Read for development context.
- **Code** (c4-code-*.md): What functions and classes exist in each directory? Reference during implementation.

## API Specifications

[List any files in apis/ directory, or "No API specifications generated."]

## Contents

### Components
[List all c4-component-*.md files with one-line descriptions]

### Code-Level Documents
[List all c4-code-*.md files with one-line descriptions]

## Generation History

| Version | Mode | Date | Notes |
|---------|------|------|-------|
| ${VERSION} | ${MODE} | [date] | [any notes about gaps or issues] |

## Regeneration

To regenerate, run the C4 documentation prompt:
- **Full:** Set MODE=full to regenerate everything
- **Delta:** Set MODE=delta to update only changed directories (requires existing C4 docs from a previous full run)
- **Auto:** Set MODE=auto to let the prompt decide (uses delta if possible, falls back to full)
- **Prompt location:** docs/auto-dev/PROMPTS/c4_documentation_prompt/
```

### 5. Produce Validation Report

Summarize the validation results.

## Output Requirements

Save outputs to `comms/outbox/exploration/c4-${VERSION}-006-finalize/`:

### README.md (required)

First paragraph: Finalization summary — all files present or listing gaps.

Then:
- **Files Present:** complete inventory with ✅/❌ status
- **Cross-Reference Check:** results of spot-checks
- **Mermaid Diagram Check:** results of spot-checks
- **Gaps or Issues:** anything missing or broken
- **Generation Stats:**
  - Total c4-code files: N
  - Total c4-component files: N
  - Total containers documented: N
  - Total personas identified: N
  - Total API specs: N
  - Mode: full/delta
  - Version: ${VERSION}

### validation-report.md

Detailed validation results:
- Every expected file and its status
- Cross-reference check results
- Mermaid syntax check results
- Recommendations for fixes (if any)

### C4 README

`docs/C4-Documentation/README.md` written directly.

## Allowed MCP Tools

- `read_document` (file creation uses Claude Code's native file system capabilities)

## Guidelines

- **This is a verification task** — do not create or modify C4 level documents (only README.md and validation-report.md)
- **Be honest about gaps** — if files are missing, say so clearly
- **Validation is best-effort** — spot-checks, not exhaustive parsing
- **README should be useful** — someone new to the project should understand what's here
- Do NOT commit — the master prompt handles the final commit
