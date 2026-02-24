# Requirements: windows-dev-guidance

## Goal

Document the Windows Git Bash /dev/null vs nul pitfall in AGENTS.md so developers and AI agents avoid creating literal `nul` files.

## Background

Backlog Item: BL-019 — Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore.

In Git Bash / MSYS2 on Windows, `/dev/null` is correctly translated to the Windows null device. However, bare `nul` — the native Windows convention — creates a literal file named `nul` because MSYS interprets it as a filename. This has already caused git noise in the project (a `nul` file was created and had to be added to `.gitignore`). The `.gitignore` entry is already in place — this item covers only the AGENTS.md documentation.

## Functional Requirements

**FR-001: Windows section in AGENTS.md**
- AGENTS.md contains a "Windows (Git Bash)" section under or after the Commands section
- Acceptance: New section is present and renders correctly in markdown

**FR-002: Correct usage documentation**
- Section documents that `/dev/null` is correct for output redirection in Git Bash on Windows
- Acceptance: `/dev/null` documented as the correct approach

**FR-003: Warning against nul**
- Section warns against using bare `nul` which creates a literal file in MSYS/Git Bash
- Acceptance: Clear warning with explanation of MSYS behavior

**FR-004: Usage examples**
- Section includes correct and incorrect usage examples
- Acceptance: At least one correct example (`command > /dev/null 2>&1`) and one incorrect example (`command > nul`)

## Non-Functional Requirements

None — documentation-only change.

## Handler Pattern

Not applicable for v011 — no new handlers introduced.

## Out of Scope

- .gitignore changes (already done — `nul` entry exists at line 219)
- Other Windows-specific guidance beyond /dev/null
- PowerShell or CMD guidance (only Git Bash/MSYS2 context)

## Test Requirements

**Manual verification:**
- AGENTS.md Windows section renders correctly in markdown preview
- Section is positioned logically within the document structure

## Reference

See `comms/outbox/versions/design/v011/004-research/` for supporting evidence:
- `codebase-patterns.md` — AGENTS.md structure and insertion point (after Commands section, line 46)
- `evidence-log.md` — nul entry in .gitignore confirmed at line 219