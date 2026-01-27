---
status: complete
acceptance_passed: 4
acceptance_total: 4
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 001-agents-pyo3-guidance

## Summary

Added a comprehensive PyO3 Bindings section to AGENTS.md documenting best practices for PyO3 bindings in this hybrid Python/Rust project. The section covers incremental binding rules, stub regeneration workflow, naming conventions, and includes a complete example.

## Acceptance Criteria

- [x] AGENTS.md has PyO3 Bindings section - Added after Coding Standards section
- [x] Incremental binding rule clearly stated - Explicit "Wrong" vs "Right" examples included
- [x] Stub regeneration command documented - `cd rust/stoat_ferret_core && cargo run --bin stub_gen`
- [x] Naming convention explained with example - `py_` prefix pattern with `#[pyo3(name = "...")]` attribute

## Changes Made

- **AGENTS.md**: Added new "## PyO3 Bindings" section with:
  - Incremental Binding Rule subsection explaining tech debt rationale
  - Stub Regeneration subsection with command and CI enforcement note
  - Naming Convention subsection explaining the `py_` prefix pattern
  - Example: Complete Type with Bindings showing a full `Segment` struct

## Quality Gate Results

All quality gates passed:
- ruff check: All checks passed
- ruff format: 6 files already formatted
- mypy: Success: no issues found in 3 source files
- pytest: 77 passed, 100% coverage
