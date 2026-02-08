# Implementation Plan — coverage-gap-fixes

## Overview

Audit coverage exclusions, test ImportError fallback paths, and remove unjustified exclusions.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Modify | `src/stoat_ferret_core/__init__.py` | Review/update coverage exclusion comments |
| Create | `tests/test_coverage/test_import_fallback.py` | ImportError fallback tests |
| Create | `tests/test_coverage/__init__.py` | Package init |
| Modify | Various source files | Remove unjustified `pragma: no cover` |

## Implementation Stages

### Stage 1: Audit
Scan all Python source files for `pragma: no cover`, `type: ignore`, and coverage exclusion patterns. Catalog each exclusion with file, line, and justification status.

### Stage 2: ImportError Fallback Tests
Write tests that mock the Rust import to exercise the ImportError fallback path. Verify fallback behavior is correct (stub classes created, warnings issued).

### Stage 3: Remove Unjustified Exclusions
Remove `pragma: no cover` from lines that can be tested. Add justification comments to lines that genuinely cannot be tested (e.g., platform-specific code).

### Stage 4: Verify Coverage
Run full test suite with coverage to confirm threshold is maintained or improved.

## Quality Gates

- ImportError fallback tests: 2–3 tests
- Coverage exclusion audit documented
- 80%+ Python coverage maintained
- `uv run ruff check src/ tests/` passes
- `uv run mypy src/` passes

## Risks

| Risk | Mitigation |
|------|------------|
| Removing exclusions drops coverage | Only remove if tests added to cover the path |
| ImportError mock affects other tests | Use dedicated test module with proper isolation |

## Commit Message

```
feat: audit and fix coverage exclusions for ImportError fallback
```
