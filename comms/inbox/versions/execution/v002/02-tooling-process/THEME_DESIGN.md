# Theme 02: tooling-process

## Overview
Document PyO3 binding patterns in AGENTS.md to prevent future tech debt from deferred bindings.

## Context
v001 retrospective identified that deferring PyO3 bindings created tech debt. Theme 1 fixes this; Theme 2 prevents recurrence.

## Backlog Items

| ID | Title | Priority | Notes |
|----|-------|----------|-------|
| BL-006 | Update AGENTS.md with PyO3 bindings guidance | P1 | Process improvement from v001 retrospective |

## Architecture Decisions

### AD-001: Documentation Location
Add new section to existing AGENTS.md rather than separate doc.

### AD-002: Key Guidance Points
1. Add bindings in same feature as Rust implementation
2. Always regenerate stubs after Rust changes
3. Use #[pyo3(name = \"...\")] for clean Python names

## Dependencies
- Theme 1 (establishes patterns to document)

## Evidence
- v001 retrospective insights

## Success Criteria
- AGENTS.md includes PyO3 section
- Clear, actionable guidance for Claude Code