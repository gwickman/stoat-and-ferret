# Requirements — search-unification

## Goal

Align InMemory search with FTS5 prefix-match semantics for consistent test/production behavior.

## Background

`AsyncInMemoryVideoRepository` uses substring match (`query_lower in v.filename.lower()` at `async_repository.py:301-308`) while `AsyncSQLiteVideoRepository` uses FTS5 prefix match (`'"{}"*'` at `async_repository.py:186-195`). Three known gaps identified in Task 006 (R3 resolved): (1) substring vs prefix, (2) multi-word phrase handling, (3) field scope. Per-token `startswith` closes gap #1; gaps #2–3 are minor for current usage patterns.

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|--------|
| FR-1 | InMemory search uses per-token `startswith` matching instead of substring | BL-016 |
| FR-2 | Parity tests verify consistent behavior between InMemory and SQLite for common queries | BL-016 |
| FR-3 | Documentation explains search behavior and known limitations | BL-016 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Existing search tests pass with unified behavior (or are updated if they relied on substring matching) |
| NFR-2 | Known FTS5 features not used by app (AND/OR/NOT/NEAR/ranking) do not need emulation |

## Out of Scope

- Full FTS5 emulation in InMemory — only prefix-match approximation
- Changing SQLite FTS5 behavior — only InMemory changes
- Adding new search features beyond what FTS5 currently supports

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| Parity | Same search queries against InMemory and SQLite produce same results | 5–8 |
| Unit | InMemory prefix-match: "test" matches "testing" but "est" does not match "testing" | 3–5 |
| Regression | Existing search tests pass with unified behavior | (existing) |