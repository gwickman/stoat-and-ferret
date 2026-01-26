# Theme 1: project-foundation

## Overview
Establish the hybrid Python/Rust project structure that will serve as the foundation for all subsequent development. This theme sets up modern tooling, quality gates, and CI pipeline.

## Context
Based on EXP-001 (rust-python-hybrid) exploration findings:
- Use maturin with PyO3 for Python/Rust integration
- Dual crate-type `["cdylib", "rlib"]` for both bindings and tests
- pyo3-stub-gen for type stub generation
- Mixed layout with `python-source` configuration

## Architecture Decisions

### AD-001: Project Layout
Use mixed Rust/Python layout:
```
stoat-and-ferret/
├── src/stoat_ferret/          # Python package (orchestration)
├── src/stoat_ferret_core/     # Python wrapper for Rust
├── rust/stoat_ferret_core/    # Rust crate
├── stubs/                     # Generated .pyi files
└── tests/                     # Python tests
```

### AD-002: Module Naming
- Rust crate: `stoat_ferret_core`
- PyO3 module: `stoat_ferret_core._core`
- Python import: `from stoat_ferret_core import function`

### AD-003: Quality Gates
- Python: ruff (lint+format), mypy (types), pytest (tests, 80% coverage)
- Rust: clippy (-D warnings), rustfmt, cargo test

### AD-004: CI Stub Verification
CI regenerates stubs and fails if they differ from committed stubs. No manual stub management.

## Dependencies
None (first theme)

## Risks
- PyO3/maturin version compatibility
- Cross-platform build differences (especially Windows path handling)

## Success Criteria
- All quality gates pass locally and in CI
- Python can import Rust module
- CI runs on all 3 platforms
- Stub verification enforced in CI