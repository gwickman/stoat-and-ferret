# Stub Regeneration

## Goal
Replace manually maintained stubs with auto-generated stubs and add CI verification to prevent future drift.

## Background
Exploration found significant stub drift:
- Methods in stubs that don't exist (Position.from_timecode, Duration.__add__)
- Methods in Rust missing from stubs (from_secs, as_secs, zero)
- Wrong method names (Duration.between vs between_positions)

**This feature MUST execute FIRST in Theme 01.**

## Requirements

### FR-001: Generate Stubs from Rust
- Run pyo3-stub-gen binary to generate accurate stubs
- Output to stubs/stoat_ferret_core/

### FR-002: CI Verification Step
- Add workflow step that regenerates stubs
- Compare against committed stubs
- Fail if any differences detected

### FR-003: Update Existing Tests
- Fix test_pyo3_bindings.py to use correct method names
- Update TestModuleExports if export list changes
- **Expected: ~20 assertion updates**

### FR-004: Documentation
- Document stub regeneration command in README or CONTRIBUTING

## Acceptance Criteria
- [ ] `cargo run --bin stub_gen` generates stubs matching Rust API
- [ ] CI step: regenerate → diff → fail if different
- [ ] All existing tests pass with correct method names
- [ ] Documentation explains how to regenerate stubs

## Evidence
- Stub drift details: `comms/outbox/exploration/design-research-gaps/stub-generation.md`