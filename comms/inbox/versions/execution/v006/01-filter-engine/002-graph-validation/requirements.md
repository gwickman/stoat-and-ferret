# Requirements: graph-validation

## Goal

Validate FilterGraph pad matching, detect unconnected pads and cycles using Kahn's algorithm.

## Background

Backlog Item: BL-038

The current FilterGraph (v001) builds FFmpeg filter strings but performs no validation of input/output pad matching. Invalid graphs (unconnected pads, cycles, mismatched labels) are only caught when FFmpeg rejects the command at runtime. M2.1 requires compile-time-safe graph construction. Without validation, complex filter graphs for effects composition will produce cryptic FFmpeg errors instead of actionable messages.

## Functional Requirements

### FR-001: Pad Label Validation

Pad labels validated for correct matching — each output label must feed a matching input label in another chain. Special-case `N:v`/`N:a` as stream references (not inter-chain labels).

**Acceptance criteria:** Pad labels validated for correct matching (output label feeds matching input label).

### FR-002: Unconnected Pad Detection

Unconnected pads detected and reported with the specific pad name. Build `HashMap<output_label, chain_index>` for lookup; unmatched outputs are graph final outputs, unmatched inputs are errors.

**Acceptance criteria:** Unconnected pads detected and reported with the specific pad name.

### FR-003: Cycle Detection

Graph cycles detected and rejected before serialization using Kahn's algorithm (BFS + in-degree tracking). O(V+E) time, O(V) space.

**Acceptance criteria:** Graph cycles detected and rejected before serialization.

### FR-004: Actionable Error Messages

Validation error messages include actionable guidance on how to fix the graph. Extend existing `BoundsError` enum pattern with `UnconnectedPad { label }`, `CycleDetected { labels }`, `DuplicateLabel { label }` variants.

**Acceptance criteria:** Validation error messages include actionable guidance on how to fix the graph.

### FR-005: Backward Compatibility

Opt-in `validate()` method on FilterGraph. Add `validated_to_string()` convenience. Do NOT modify existing `Display`/`to_string()` — zero breaking changes. All existing consumers create valid graphs so no migration needed.

**Acceptance criteria:** Existing FilterGraph tests updated to cover validation.

## Non-Functional Requirements

### NFR-001: Test Coverage

New validation code targets >90% coverage. CI threshold remains at 75%.

### NFR-002: No New Dependencies

Kahn's algorithm implemented inline (~30 lines). No petgraph dependency.

## Out of Scope

- Semantic validation of filter parameters (only structural graph validation)
- Automatic graph repair or suggestion of fixes
- Validation of stream format compatibility between filters

## Test Requirements

- Unit tests for each validation error type (unconnected pad, cycle, duplicate label)
- Tests for valid graphs passing validation
- Tests verifying backward compatibility (existing tests continue to pass)
- PyO3 binding tests for `validate()` and `validated_to_string()` methods

## Reference

See `comms/outbox/versions/design/v006/004-research/` for supporting evidence.