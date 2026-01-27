# API Naming Cleanup

## Goal
Ensure all Python-visible method names are clean (no py_ prefixes) and update tests accordingly.

## Background
54 methods use py_ prefix for PyO3 method chaining with PyRefMut. Most use #[pyo3(name = "...")] to expose clean names. Need to audit and fix any that don't.

**This feature MUST execute LAST in Theme 01.**

**Expected test updates: ~20 assertions**

## Requirements

### FR-001: Audit All py_ Methods
- Check all 54 py_ prefixed methods in timeline/, ffmpeg/, sanitize/
- Verify each has #[pyo3(name = "...")] attribute
- List any exposing py_ prefix to Python

### FR-002: Fix Missing Name Attributes
- Add #[pyo3(name = "method_name")] to any missing
- Ensure Python sees clean names

### FR-003: Update Tests (~20 assertions)
- Update test_pyo3_bindings.py to use clean method names
- Remove any py_ references in test assertions
- Batch all updates in this feature

### FR-004: Regenerate Stubs
- Verify stubs show clean names only

### FR-005: Update Module Exports Test
- Update TestModuleExports.test_all_exports_present with complete export list

## Acceptance Criteria
- [ ] No py_ prefixes visible when using module from Python
- [ ] All ~20 test assertions updated to use clean names
- [ ] Stubs show clean method names
- [ ] TestModuleExports passes with complete export list

## Evidence
- py_ inventory (54 methods): `comms/outbox/exploration/design-research-gaps/rust-types.md`