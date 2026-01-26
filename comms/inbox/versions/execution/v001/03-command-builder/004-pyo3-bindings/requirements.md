# PyO3 Bindings with Type Stubs

## Goal
Expose Rust command builder to Python via PyO3 with generated type stubs for IDE support.

## Requirements

### FR-001: Core Type Exposure
- Expose Position, Duration, FrameRate to Python
- Expose TimeRange to Python
- Expose ValidationError to Python

### FR-002: Command Builder Exposure
- Expose FFmpegCommand builder
- Expose Filter, FilterChain, FilterGraph builders
- Method chaining works in Python

### FR-003: Type Stubs
- Generate .pyi files with pyo3-stub-gen
- All public functions have type hints
- CI verifies stubs match implementation

### FR-004: Error Handling
- Rust errors converted to Python exceptions
- Custom exception classes for domain errors
- Error messages preserved

### FR-005: Python Wrapper Module
- `src/stoat_ferret_core/__init__.py` exports public API
- Re-export from `_core` with clean names
- Type hints in wrapper

## Acceptance Criteria
- [ ] All Rust types importable from Python
- [ ] Method chaining works in Python
- [ ] mypy passes with generated stubs
- [ ] IDE autocomplete works