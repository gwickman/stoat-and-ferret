# Implementation Plan — search-unification

## Overview

Change InMemory search from substring to per-token `startswith` matching and add parity tests verifying consistency with SQLite FTS5.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Modify | `src/stoat_ferret/db/async_repository.py` | Change InMemory search to per-token startswith |
| Modify | `src/stoat_ferret/db/repository.py` | Change sync InMemory search to match (if applicable) |
| Create | `tests/test_contract/test_search_parity.py` | Parity tests: InMemory vs SQLite |
| Modify | existing search tests | Update tests relying on substring behavior |

## Implementation Stages

### Stage 1: Audit Existing Search Tests
Identify all tests that perform search queries. Determine which rely on substring behavior that would break with prefix matching.

### Stage 2: Implement Per-Token Startswith
Replace `query_lower in v.filename.lower()` with per-token `startswith` logic: tokenize filename by non-alphanumeric characters, check if any token starts with the query. Apply to both `AsyncInMemoryVideoRepository` and `InMemoryVideoRepository`.

### Stage 3: Parity Tests
Create parametrized tests running the same queries against both InMemory and SQLite repositories. Test cases: single word prefix, non-prefix substring (should NOT match in unified behavior), multi-word queries, case sensitivity, empty query.

### Stage 4: Document Known Differences
Add inline documentation listing 3 known behavioral differences between InMemory and FTS5: (a) multi-word phrase handling, (b) field scope, (c) tokenization rules. These are acceptable gaps for current usage patterns.

## Quality Gates

- Parity tests: 5–8 tests
- Prefix-match unit tests: 3–5 tests
- All existing search tests pass (updated as needed)
- `uv run ruff check src/ tests/` passes
- `uv run mypy src/` passes

## Risks

| Risk | Mitigation |
|------|------------|
| Existing tests rely on substring behavior | Audit first; update affected tests |
| Tokenization edge cases | Document known limitations; test common patterns |

## Commit Message

```
feat: unify InMemory search with FTS5 prefix-match semantics
```
