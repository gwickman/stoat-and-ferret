# Requirements — coverage-gap-fixes

## Goal

Review and fix coverage exclusions for ImportError fallback code.

## Background

v001 retrospective noted ImportError fallback code is excluded from coverage. The `src/stoat_ferret_core/__init__.py:83` has `except ImportError: # pragma: no cover` for the Rust extension fallback. Lines 86-121 have 30+ `type: ignore` comments for stub assignments. See `004-research/codebase-patterns.md` §Coverage Exclusions.

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|--------|
| FR-1 | Identify all coverage exclusions in Python code | BL-012 |
| FR-2 | Remove or justify each exclusion with documentation | BL-012 |
| FR-3 | ImportError fallback properly tested or documented as intentional exclusion | BL-012 |
| FR-4 | Coverage threshold maintained after changes | BL-012 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | 80% Python coverage minimum maintained |
| NFR-2 | Justified exclusions documented in code comments |

## Out of Scope

- Rewriting the ImportError fallback mechanism
- Achieving 100% coverage — only removing unjustified exclusions
- Rust coverage gaps — that's BL-010

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| Unit | ImportError fallback path exercised (mock import failure) | 2–3 |
| Audit | Review all `pragma: no cover` and `type: ignore` for justification | (review) |