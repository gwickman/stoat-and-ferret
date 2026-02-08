# Requirements — property-test-guidance

## Goal

Add property test section to feature design templates with invariant-first guidance.

## Background

v001 retrospective suggested writing proptest invariants before implementation as executable specifications. No property test guidance exists in current design templates. `hypothesis` is not in dev dependencies. See `004-research/external-research.md` §3 for property-based testing patterns.

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|---------|
| FR-1 | Feature design template includes property test section | BL-009 |
| FR-2 | Guidance on writing property test invariants before implementation | BL-009 |
| FR-3 | Example showing invariant-first design approach using Hypothesis | BL-009 |
| FR-4 | Documentation on expected test count tracking per feature | BL-009 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | `hypothesis` added to dev dependencies in `pyproject.toml` with version pin |
| NFR-2 | Template guidance is practical and concise — not a Hypothesis tutorial |

## Out of Scope

- Writing property tests for existing features — guidance only
- Hypothesis integration with Rust (proptest) — Python-side only
- Mandatory property tests for all features — guidance is advisory

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| Example | Property test example in template showing invariant-first approach | 1–2 |
| (none) | Primarily a documentation/template feature | — |
