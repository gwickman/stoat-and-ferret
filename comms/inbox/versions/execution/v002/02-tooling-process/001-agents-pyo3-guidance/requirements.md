# AGENTS.md PyO3 Guidance

## Goal
Add section to AGENTS.md documenting PyO3 binding best practices.

## Requirements

### FR-001: New Section in AGENTS.md
- Add "## PyO3 Bindings" section
- Place after existing Rust-related guidance

### FR-002: Content - Incremental Binding Rule
- State: add Python bindings in same feature as Rust implementation
- State: do not defer bindings to later feature
- Explain rationale (tech debt accumulation)

### FR-003: Content - Stub Regeneration
- State: always run stub generator after modifying bindings
- Provide command: `cd rust/stoat_ferret_core && cargo run --bin stub_gen`
- Note: CI will fail if stubs drift

### FR-004: Content - Naming Convention
- State: use #[pyo3(name = "...")] for clean Python names
- Explain py_ prefix pattern and why it exists
- Show example

### FR-005: Example Code
Include example showing correct pattern with complete type.

## Acceptance Criteria
- [ ] AGENTS.md has PyO3 Bindings section
- [ ] Incremental binding rule clearly stated
- [ ] Stub regeneration command documented
- [ ] Naming convention explained with example