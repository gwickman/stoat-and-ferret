## Context

InMemory test doubles can silently diverge from real implementations over time. Behavioral differences (e.g., search semantics, ordering, edge cases) mean tests pass against fakes but fail against real systems.

## Learning

Write explicit parity tests that run the same operations against both the InMemory test double and the real implementation, asserting identical results. These tests serve as a contract between the fake and real, catching drift automatically.

## Evidence

- v004 Theme 01: 8 InMemory vs SQLite parity tests for repository operations.
- v004 Theme 02 Feature 003 (search-unification): 7 parity tests caught that InMemory used substring matching while SQLite FTS5 used prefix matching. The parity tests drove the fix to per-token `startswith` semantics.
- Parity tests extended naturally as new features were added.

## Application

- For every InMemory/fake test double, add parity tests against the real implementation.
- Run parity tests as part of the standard test suite (not just occasionally).
- When a parity test fails, fix the fake to match the real — the real implementation is the source of truth.
- Document known behavioral differences that are intentionally not matched.