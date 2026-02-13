# Requirements: filter-composition

## Goal

Build chain, branch, and merge composition modes with automatic pad label management and validation.

## Background

Backlog Item: BL-039

No support exists for composing filter chains programmatically. The current system builds individual filters but cannot chain them sequentially, branch one stream into multiple, or merge multiple streams. M2.1 requires a composition API for building complex filter graphs. Without it, every effect combination must manually construct raw filter strings, which is error-prone and unvalidatable.

## Functional Requirements

**FR-001: Chain composition**
- Apply filters sequentially to a single stream
- Automatic pad label management between chained filters
- AC: A chain of N filters produces a correctly connected sequential graph with valid pad labels

**FR-002: Branch composition**
- Split one stream into multiple output streams
- AC: Branching produces correct output pads for each branch target

**FR-003: Merge composition**
- Combine multiple streams using overlay, amix, or concat
- AC: Merge produces a correctly connected graph combining multiple input streams

**FR-004: Automatic validation**
- Composed graphs pass FilterGraph validation automatically
- AC: Validation runs automatically on composed graphs; invalid compositions are caught before serialization

**FR-005: Automatic pad management**
- Pad labels managed automatically during composition — no manual label assignment required
- AC: Users never specify pad labels directly; the composition API generates and connects them

**FR-006: PyO3 bindings**
- Expose composition API to Python with type stubs
- Builder API uses `PyRefMut` chaining pattern (LRN-001)
- AC: Python code can chain, branch, and merge filters identically to Rust

## Non-Functional Requirements

**NFR-001: Composability**
- Compositions can be nested (e.g., a chain within a branch)
- AC: Nested composition produces valid graphs

**NFR-002: Test coverage**
- Module-level Rust coverage >90%
- AC: `cargo tarpaulin` reports >90% for the composition module

## Out of Scope

- Visual composition editing (GUI concern)
- Dynamic composition (runtime graph modification)
- Performance-optimized graph execution (FFmpeg handles execution)

## Test Requirements

- **Unit tests:** Chain (sequential application, multi-step chains), branch (stream splitting, pad label auto-management), merge (overlay/amix/concat modes, multi-input), automatic validation (invalid compositions caught), PyO3 bindings (composition from Python, method chaining)

Reference: `See comms/outbox/versions/design/v006/004-research/ for supporting evidence`