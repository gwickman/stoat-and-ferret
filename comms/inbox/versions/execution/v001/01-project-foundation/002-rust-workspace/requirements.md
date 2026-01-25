# Rust Workspace Setup

## Goal
Initialize Rust workspace with maturin and PyO3 for building Python bindings.

## Requirements

### FR-001: Rust Project Structure
- Create `rust/stoat_ferret_core/` crate directory
- Configure as library crate with `cdylib` and `rlib` targets
- Set minimum Rust edition to 2021

### FR-002: PyO3 Integration
- Add PyO3 dependency with `abi3-py310` feature
- Add pyo3-stub-gen for type stub generation
- Create basic `#[pymodule]` with health check function

### FR-003: Maturin Configuration
- Configure `pyproject.toml` for maturin build backend
- Set module-name to `stoat_ferret_core._core`
- Configure python-source for mixed layout

### FR-004: Type Stubs
- Set up pyo3-stub-gen with `define_stub_info_gatherer!`
- Create stub generator binary in `src/bin/stub_gen.rs`
- Generate initial `stoat_ferret_core.pyi`

### FR-005: Rust Quality Gates
- Configure clippy with `-D warnings`
- Add rustfmt.toml with project style
- Set up cargo test infrastructure

## Acceptance Criteria
- [ ] `maturin develop` builds and installs module
- [ ] `from stoat_ferret_core import _core` works in Python
- [ ] `cargo test` runs Rust unit tests
- [ ] `cargo clippy -- -D warnings` passes
- [ ] Type stubs generated in `stubs/` directory