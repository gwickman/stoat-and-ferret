# Implementation Plan: graph-validation

## Overview

Add validation to the existing `FilterGraph` type in Rust: pad label matching, unconnected pad detection, and cycle detection via topological sort. Validation runs automatically before serialization and produces actionable error messages. This extends existing code rather than creating new types.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `rust/stoat_ferret_core/src/ffmpeg/filter.rs` | Modify | Add validation methods to existing FilterGraph type |
| `rust/stoat_ferret_core/src/lib.rs` | Modify | Export any new error types to PyO3 module if needed |
| `stubs/stoat_ferret_core/_core.pyi` | Modify | Update stubs if new public types exposed |
| `rust/stoat_ferret_core/tests/test_graph_validation.rs` | Create | Validation unit tests |

## Implementation Stages

### Stage 1: Validation Infrastructure

1. In `rust/stoat_ferret_core/src/ffmpeg/filter.rs`:
   - Add `ValidationError` enum with variants: `MismatchedPads`, `UnconnectedPad`, `CycleDetected`
   - Each variant includes specific pad/filter names and actionable guidance text
   - Add `fn validate(&self) -> Result<(), Vec<ValidationError>>` to FilterGraph

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_graph_validation
```

### Stage 2: Pad Matching and Unconnected Pad Detection

1. Implement pad label matching:
   - Collect all output pad labels and input pad labels from the graph
   - Verify each output label has a matching input label consumer
   - Report mismatches with specific pad names
2. Implement unconnected pad detection:
   - Identify pads with no connections
   - Report with specific pad name and parent filter name

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_graph_validation
```

### Stage 3: Cycle Detection

1. Implement topological sort on the filter graph:
   - Build adjacency list from pad connections
   - Run Kahn's algorithm or DFS-based topological sort
   - Report cycles with the involved filter names
2. Error messages include guidance: e.g., "Cycle detected involving filters [A, B, C]. Remove the connection from C back to A."

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_graph_validation
```

### Stage 4: Automatic Validation Before Serialization

1. Modify FilterGraph serialization to call `validate()` automatically:
   - Serialization returns `Result<String, Vec<ValidationError>>` instead of `String`
   - Or validate in a pre-serialization step
2. Ensure all existing FilterGraph tests still pass — validation extends, not replaces
3. Update PyO3 bindings if serialization signature changed
4. Regenerate type stubs if needed:
   ```bash
   cd rust/stoat_ferret_core && cargo run --bin stub_gen
   ```

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test
uv run pytest tests/test_pyo3_bindings.py
```

## Test Infrastructure Updates

- No new test infrastructure needed — standard Rust unit tests

## Quality Gates

```bash
cd rust/stoat_ferret_core && cargo clippy -- -D warnings
cd rust/stoat_ferret_core && cargo test
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest
```

## Risks

- Changing FilterGraph serialization signature may break existing consumers — mitigate by ensuring all existing tests pass. See `comms/outbox/versions/design/v006/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: add filter graph validation with pad matching and cycle detection

Extend FilterGraph with pad label matching, unconnected pad detection,
cycle detection via topological sort, and actionable error messages.
Validation runs automatically before serialization. Covers BL-038.
```
