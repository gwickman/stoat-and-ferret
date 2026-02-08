# Requirements — inmemory-test-doubles

## Goal

Add deepcopy isolation and seed helpers to `AsyncInMemoryProjectRepository`; create `InMemoryJobQueue` with synchronous deterministic execution.

## Background

The `AsyncInMemoryProjectRepository` exists (`src/stoat_ferret/db/project_repository.py:184`) but stores direct references without isolation. No `InMemoryJobQueue` exists — no job queue concept exists at all. The `07-quality-architecture.md` spec requires these test doubles for black box testing (M1.8). See `004-research/codebase-patterns.md` §Existing InMemory for current state.

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|---------|
| FR-1 | `AsyncInMemoryProjectRepository` returns deepcopy-isolated objects from all read operations | BL-020 |
| FR-2 | `AsyncInMemoryProjectRepository` provides `seed()` method to populate initial test data | BL-020 |
| FR-3 | `InMemoryJobQueue` implements `AsyncJobQueue` protocol (submit, get_status, get_result) | BL-020 |
| FR-4 | `InMemoryJobQueue` executes jobs synchronously for deterministic test behavior | BL-020 |
| FR-5 | `InMemoryJobQueue` supports configurable outcomes (success, failure, timeout) | BL-020 |
| FR-6 | Seed helpers available for all InMemory repositories (project, video, clip) | BL-020 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Deepcopy overhead < 1ms per operation for typical domain objects |
| NFR-2 | InMemoryJobQueue interface matches AsyncJobQueue protocol exactly |
| NFR-3 | All existing tests continue to pass after modifications |

## Out of Scope

- Full rewrite of `AsyncInMemoryProjectRepository` — scope is adding isolation and seed helpers
- External job queue implementations (Redis, arq) — asyncio.Queue is in Theme 03
- Migration of existing tests to use seed helpers — that happens incrementally in later features

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| Unit | InMemoryJobQueue: submit, status, completion, failure, configurable outcomes | 8–10 |
| Unit | AsyncInMemoryProjectRepository: deepcopy isolation (mutate returned, verify store unchanged) | 3–5 |
| Unit | Seed helpers: populate test data, verify retrieval | 3–5 |
| Contract | InMemory vs SQLite parity: same operations produce same results | 5–8 |
