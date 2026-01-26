# Version Retrospective Prompt

## Context

You are creating a retrospective for a completed version.

**Version:** {{version}}
**Version Path:** `comms/outbox/versions/execution/{{version}}/`

## Input Documents

Review these before writing the retrospective:

1. **Version Definition:** `comms/inbox/versions/execution/{{version}}/THEME_INDEX.md`
2. **Theme Retrospectives:** All `*/retrospective.md` files
3. **Status File:** `comms/outbox/versions/execution/{{version}}/STATUS.md`

## Process Document

Follow: `docs/auto-dev/PROCESS/generic/07-VERSION-CLOSE.md`

## C4 Documentation Status

**Status:** {{c4_status}}

If C4 regeneration failed, note this in the retrospective and consider adding to technical debt.

## Retrospective Structure

Create `comms/outbox/versions/execution/{{version}}/retrospective.md` with:

1. **Version Summary** - Goals achieved and scope
2. **Theme Results** - Table of themes with outcomes
3. **C4 Documentation** - Status of architecture documentation regeneration
4. **Cross-Theme Learnings** - Patterns across multiple themes
5. **Technical Debt Summary** - Items requiring follow-up (Chatbot will create backlog items during closure)
6. **Process Improvements** - For AGENTS.md or process docs
7. **Statistics** - Features completed, time, etc.

## CHANGELOG Update

After creating retrospective, update `docs/CHANGELOG.md`:

```markdown
## [v018] - YYYY-MM-DD

### Added
- <new features>

### Changed
- <modifications>

### Fixed
- <bug fixes>
```

## Completion Criteria

- [ ] retrospective.md created
- [ ] All theme retrospectives reviewed
- [ ] docs/CHANGELOG.md updated
- [ ] Tech debt items documented in retrospective (Chatbot handles backlog during closure)
- [ ] STATUS.md shows version complete

## Outputs

1. `comms/outbox/versions/execution/{{version}}/retrospective.md`
2. Updated `docs/CHANGELOG.md`

**Note:** Do NOT update BACKLOG.md directly. Backlog management is handled by Chatbot during the interactive closure phase via MCP tools.
