# Theme 01: rust-python-bindings

## Overview

Fix stub drift and complete Python bindings for all v001 Rust types. This theme must execute first as subsequent themes may use these types.

## Context

Exploration (design-research-gaps) revealed:
- Manual stubs have significant drift from Rust API
- Clip and ValidationError structs exist but lack PyO3 bindings
- find_gaps, merge_ranges, total_coverage exist but aren't exposed
- 54 methods use py_ prefix intentionally for PyO3 method chaining

## Rust Type Status

| Type | Rust Status | Python Status | Feature |
|------|-------------|---------------|---------|
| Clip | ✅ Implemented | ❌ No PyO3 bindings | 002 |
| ValidationError (struct) | ✅ Has field/message/actual/expected | ❌ No PyO3 bindings | 002 |
| find_gaps | ✅ Implemented | ❌ Not exposed | 003 |
| merge_ranges | ✅ Implemented | ❌ Not exposed | 003 |
| total_coverage | ✅ Implemented | ❌ Not exposed | 003 |

## Architecture Decisions

### AD-001: Stub Generation Strategy
Replace manual stubs with auto-generated stubs from pyo3-stub-gen.
- Run `cargo run --bin stub_gen` to generate
- CI verifies generated matches committed

### AD-002: ValidationError Disambiguation
Two ValidationErrors exist:
- Python exception in lib.rs (keep as-is for error handling)
- Rust struct in clip/validation.rs (expose with clear documentation)

Expose Rust struct as `ValidationError` from clip module. Document that this is distinct from the exception type.

### AD-003: Feature Ordering (CRITICAL)
Features must execute sequentially:
1. **001-stub-regeneration FIRST** (fixes test method names before other work)
2. 002-clip-bindings (adds new types)
3. 003-range-list-ops (adds new functions)
4. **004-api-naming-cleanup LAST** (final polish, batches all ~20 test updates)

## Backlog Items

| ID | Title | Priority | Notes |
|----|-------|----------|-------|
| BL-007 | Automate type stub generation in CI | P1 (elevated from P2) | Feature 001 - MUST EXECUTE FIRST |
| BL-004 | Expose Clip and ValidationError types to Python | P1 | Feature 002 - Rust struct, not exception |
| BL-005 | Expose TimeRange and list operations to Python | P1 | Feature 003 |
| BL-008 | Clean up Python API naming inconsistencies | P2 | Feature 004 - MUST EXECUTE LAST |

## Dependencies
- v001 Rust crate (stoat_ferret_core)

## Risks

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Stub regeneration breaks tests | HIGH | HIGH | Feature 001 fixes tests before proceeding |
| BL-008 breaks ~20 test assertions | HIGH | CERTAIN | Feature 004 batches all test updates at end |

## Test Impact
- `test_pyo3_bindings.py`: ~20 assertions need updating
- `TestModuleExports`: Add Clip, ValidationError, find_gaps, merge_ranges, total_coverage

## Evidence Sources

| Claim | Source |
|-------|--------|
| Stub drift details | `comms/outbox/exploration/design-research-gaps/stub-generation.md` |
| Clip/ValidationError status | `comms/outbox/exploration/design-research-gaps/rust-types.md` |
| py_ prefix inventory (54 methods) | `comms/outbox/exploration/design-research-gaps/rust-types.md` |

## Success Criteria
- CI fails on stub drift
- Clip, ValidationError (struct) available in Python
- find_gaps, merge_ranges, total_coverage callable
- No py_ prefixes visible in Python API