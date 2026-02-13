# Requirements: graph-validation

## Goal

Add validation to the existing FilterGraph type: pad label matching, unconnected pad detection, cycle detection, and actionable error messages.

## Background

Backlog Item: BL-038

The current FilterGraph (v001) builds FFmpeg filter strings but performs no validation of input/output pad matching. Invalid graphs (unconnected pads, cycles, mismatched labels) are only caught when FFmpeg rejects the command at runtime. M2.1 requires compile-time-safe graph construction. Complex filter graphs for effects composition (BL-039) will produce cryptic FFmpeg errors without validation.

## Functional Requirements

**FR-001: Pad label matching**
- Validate that output pad labels connect to matching input pad labels
- AC: Mismatched labels produce errors with specific pad names identifying the mismatch

**FR-002: Unconnected pad detection**
- Detect and report unconnected pads with the specific pad name
- AC: Graphs with dangling input or output pads produce errors identifying each unconnected pad

**FR-003: Cycle detection**
- Detect and reject graph cycles before serialization using topological sort
- AC: Cyclic graphs are rejected; acyclic graphs pass validation

**FR-004: Actionable error messages**
- Validation error messages include guidance on how to fix the graph
- AC: Each error type provides at least one suggestion for resolution

**FR-005: Automatic validation**
- Validation runs automatically before serialization
- AC: Calling `serialize()` or equivalent on an invalid graph returns a validation error, not invalid output

**FR-006: Existing test compatibility**
- Existing FilterGraph tests continue passing — validation extends, not replaces
- AC: All pre-existing FilterGraph tests pass without modification

## Non-Functional Requirements

**NFR-001: Error quality**
- Error messages are developer-friendly and identify the specific graph elements involved
- AC: Errors include pad names, filter names, or other identifiers sufficient to locate the issue

**NFR-002: Test coverage**
- Module-level Rust coverage >90%
- AC: `cargo tarpaulin` reports >90% for the graph validation module

## Out of Scope

- Filter-specific pad type checking (e.g., verifying audio pad connected to audio input)
- Performance optimization for very large graphs (v006 graphs are small)
- Visual graph debugging tools

## Test Requirements

- **Unit tests:** Pad matching (valid and invalid labels), unconnected pad detection (dangling inputs/outputs), cycle detection (cyclic vs acyclic graphs), error message quality
- **Existing test compatibility:** All pre-existing FilterGraph tests must continue passing

Reference: `See comms/outbox/versions/design/v006/004-research/ for supporting evidence`
