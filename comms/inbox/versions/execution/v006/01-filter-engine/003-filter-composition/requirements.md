# Requirements: filter-composition

## Goal

Programmatic chain, branch, and merge composition with automatic pad label management.

## Background

Backlog Item: BL-039

No support exists for composing filter chains programmatically. The current system builds individual filters but cannot chain them sequentially, branch one stream into multiple, or merge multiple streams (e.g., overlay, amix). M2.1 requires a composition API for building complex filter graphs. Without it, every effect combination must manually construct raw filter strings, which is error-prone and unvalidatable.

## Functional Requirements

### FR-001: Chain Composition

Chain composition applies filters sequentially to a single stream. A chain takes an input stream and produces an output stream through a sequence of filters.

**Acceptance criteria:** Chain composition applies filters sequentially to a single stream.

### FR-002: Branch Composition

Branch splits one stream into multiple output streams using the `split` or `asplit` filter with automatic label generation.

**Acceptance criteria:** Branch splits one stream into multiple output streams.

### FR-003: Merge Composition

Merge combines multiple streams using overlay, amix, or concat with automatic input label wiring.

**Acceptance criteria:** Merge combines multiple streams using overlay, amix, or concat.

### FR-004: Automatic Validation

Composed graphs pass FilterGraph validation automatically. The composition API calls `validate()` internally to ensure structural correctness.

**Acceptance criteria:** Composed graphs pass FilterGraph validation automatically.

### FR-005: PyO3 Bindings

PyO3 bindings expose composition API to Python with type stubs. Follow `PyRefMut<'_, Self>` pattern for method chaining.

**Acceptance criteria:** PyO3 bindings expose composition API to Python with type stubs.

## Non-Functional Requirements

### NFR-001: Test Coverage

New composition module targets >90% coverage. CI threshold remains at 75%.

### NFR-002: Automatic Pad Label Management

Pad labels generated automatically — users do not need to manage label strings manually.

## Out of Scope

- Dynamic composition (modifying graphs after construction)
- Parallel stream processing optimization
- Audio/video stream type checking at the composition level

## Test Requirements

- Unit tests for chain, branch, and merge operations
- Tests for automatic pad label generation and uniqueness
- Tests verifying composed graphs pass validation
- Integration tests combining multiple composition operations
- PyO3 binding tests for composition API
- Type stub regeneration and verification

## Sub-tasks

- Impact #4: Run `cargo run --bin stub_gen` after adding PyO3 bindings

## Reference

See `comms/outbox/versions/design/v006/004-research/` for supporting evidence.